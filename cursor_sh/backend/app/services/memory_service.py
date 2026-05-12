"""用户画像 Memory 服务

提供 Memory 的 CRUD、对话上下文注入、爬取触发等功能。
"""

import uuid
import asyncio
import re
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_memory import UserMemory
from app.models.user import User
from app.database import async_session_maker
from app.config import settings


_crawl_tasks: set[str] = set()
_crawl_semaphore: asyncio.Semaphore | None = None
_background_semaphore: asyncio.Semaphore | None = None


def _get_crawl_semaphore() -> asyncio.Semaphore:
    global _crawl_semaphore
    limit = max(1, int(settings.AI_CRAWL_MAX_CONCURRENT or 1))
    if _crawl_semaphore is None:
        _crawl_semaphore = asyncio.Semaphore(limit)
    return _crawl_semaphore


def _get_background_semaphore() -> asyncio.Semaphore:
    global _background_semaphore
    limit = max(1, int(settings.AI_BACKGROUND_MAX_CONCURRENT or 1))
    if _background_semaphore is None:
        _background_semaphore = asyncio.Semaphore(limit)
    return _background_semaphore


def _pending_crawl_is_fresh(company_info: dict) -> bool:
    """判断 pending 爬取是否仍在有效期内，避免异常退出后永久卡住。"""
    if company_info.get("crawl_status") != "pending":
        return False

    started_at = company_info.get("crawl_started_at")
    if not started_at:
        return False

    try:
        started = datetime.fromisoformat(started_at)
    except (TypeError, ValueError):
        return False

    ttl = max(60, int(settings.AI_CRAWL_PENDING_TTL_SECONDS or 1800))
    return (datetime.now() - started).total_seconds() < ttl


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CRUD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def get_memory(user_id: str, db: AsyncSession | None = None) -> UserMemory | None:
    """获取用户 Memory"""
    if db:
        result = await db.execute(select(UserMemory).where(UserMemory.user_id == user_id))
        return result.scalar_one_or_none()
    else:
        async with async_session_maker() as session:
            result = await session.execute(select(UserMemory).where(UserMemory.user_id == user_id))
            return result.scalar_one_or_none()


async def get_or_create_memory(user_id: str, db: AsyncSession | None = None) -> UserMemory:
    """获取或创建用户 Memory"""
    async def _inner(session: AsyncSession) -> UserMemory:
        result = await session.execute(select(UserMemory).where(UserMemory.user_id == user_id))
        memory = result.scalar_one_or_none()
        if memory:
            return memory

        memory = UserMemory(
            id=str(uuid.uuid4()),
            user_id=user_id,
            company_info={},
            screen_resources=[],
            project_preferences={},
            past_projects=[],
            interaction_stats={
                "total_sessions": 0,
                "first_contact": datetime.now().isoformat(),
                "last_contact": datetime.now().isoformat(),
            },
            agent_notes="",
        )
        session.add(memory)
        await session.commit()
        await session.refresh(memory)
        return memory

    if db:
        return await _inner(db)
    else:
        async with async_session_maker() as session:
            return await _inner(session)


async def update_memory(user_id: str, updates: dict, db: AsyncSession | None = None):
    """更新用户 Memory 的指定字段

    Args:
        user_id: 用户 ID
        updates: 要更新的字段字典，如 {"company_info": {...}, "screen_resources": [...]}
    """
    async def _inner(session: AsyncSession):
        result = await session.execute(select(UserMemory).where(UserMemory.user_id == user_id))
        memory = result.scalar_one_or_none()
        if not memory:
            return

        for key, value in updates.items():
            if hasattr(memory, key):
                setattr(memory, key, value)

        await session.commit()

    if db:
        await _inner(db)
    else:
        async with async_session_maker() as session:
            await _inner(session)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 交互统计更新
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def update_interaction_stats(user_id: str):
    """每次 /chat 请求后调用，更新交互统计"""
    async with async_session_maker() as session:
        memory = await get_or_create_memory(user_id, db=session)
        stats = memory.interaction_stats or {}
        stats["total_sessions"] = stats.get("total_sessions", 0) + 1
        stats["last_contact"] = datetime.now().isoformat()
        if not stats.get("first_contact"):
            stats["first_contact"] = datetime.now().isoformat()

        memory.interaction_stats = stats
        await session.commit()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 历史项目同步
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def sync_past_project(user_id: str, project_info: dict):
    """订单创建或更新时，同步到 Memory.past_projects

    Args:
        project_info: {"order_number": "...", "project_name": "...", "city": "...", "status": "..."}
    """
    async with async_session_maker() as session:
        memory = await get_or_create_memory(user_id, db=session)
        past = memory.past_projects or []

        # 添加时间戳
        project_info["updated_at"] = datetime.now().isoformat()

        # 如果已有该订单，更新状态
        updated = False
        for p in past:
            if p.get("order_number") == project_info.get("order_number"):
                p.update(project_info)
                updated = True
                break

        if not updated:
            past.append(project_info)

        # 只保留最近 20 条
        memory.past_projects = past[-20:]
        await session.commit()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 管理员上传资料同步
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def sync_document_ingest(user_id: str, document_info: dict):
    """将管理员上传 PDF/PPT 的 ingest 结果同步到用户 Memory。

    document_info:
      {
        "filename": "...",
        "document_title": "...",
        "brief": "...",
        "company_info": {...},
        "media_assets": [...]
      }
    """
    if not user_id or not document_info:
        return

    async with async_session_maker() as session:
        memory = await get_or_create_memory(user_id, db=session)
        registered_company = await _get_registered_company_for_user(user_id, session)

        ci = dict(memory.company_info or {})
        doc_company = document_info.get("company_info") or {}
        extracted_company = doc_company.get("company_name") or ""
        company_display_name = extracted_company or registered_company or "未知客户"
        company_key = _normalize_company_name(company_display_name)
        doc_title = document_info.get("document_title") or ""
        brief = document_info.get("brief") or ""
        now = datetime.now().isoformat()

        if company_display_name and company_display_name != "未知客户":
            ci["name"] = company_display_name
        if brief and not ci.get("description"):
            ci["description"] = brief
        if doc_company.get("selling_points") and not ci.get("advantages"):
            ci["advantages"] = doc_company.get("selling_points", [])[:8]

        ci["active_company_key"] = company_key
        ci["active_company_name"] = company_display_name
        ci["registered_company_name"] = registered_company
        ci["extracted_company_name"] = extracted_company
        ci["document_profile"] = doc_company
        ci["document_brief"] = brief
        ci["document_title"] = doc_title
        ci["document_source_filename"] = document_info.get("filename", "")
        ci["document_ingested_at"] = now
        ci["document_ingest_status"] = "success"

        companies = ci.get("documents_by_company") or {}
        company_bucket = companies.get(company_key) or {}
        company_bucket["company_key"] = company_key
        company_bucket["company_name"] = company_display_name
        company_bucket["registered_company_name"] = registered_company
        company_bucket["extracted_company_name"] = extracted_company
        company_bucket["profile"] = doc_company
        company_bucket["brief"] = brief
        company_bucket["updated_at"] = now

        doc_history = ci.get("document_ingests") or []
        doc_record = {
            "company_key": company_key,
            "company_name": company_display_name,
            "document_id": document_info.get("document_id", ""),
            "order_id": document_info.get("order_id", ""),
            "file_index": document_info.get("file_index"),
            "filename": document_info.get("filename", ""),
            "title": doc_title,
            "brief": brief,
            "ingested_at": now,
        }
        doc_history.append(doc_record)
        ci["document_ingests"] = doc_history[-5:]

        company_docs = company_bucket.get("documents") or []
        company_docs.append(doc_record)
        company_bucket["documents"] = company_docs[-10:]
        companies[company_key] = company_bucket
        ci["documents_by_company"] = companies

        memory.company_info = ci

        existing_screens = memory.screen_resources or []
        merged_screens = _merge_document_media_assets(
            existing_screens,
            document_info.get("media_assets") or [],
            source_filename=document_info.get("filename", ""),
            company_key=company_key,
            company_name=company_display_name,
        )
        memory.screen_resources = merged_screens

        await session.commit()
        print(f"[MemoryService] 文档资料已同步到 Memory: user={user_id}, company={company_display_name}, screens={len(merged_screens)}")


async def upsert_customer_document_ingest(user_id: str, document_id: str, updates: dict):
    """更新客户维度资料 ingest 记录。"""
    if not user_id or not document_id:
        return

    async with async_session_maker() as session:
        memory = await get_or_create_memory(user_id, db=session)
        ci = dict(memory.company_info or {})
        docs = ci.get("customer_documents") or []

        found = False
        for doc in docs:
            if doc.get("document_id") == document_id:
                doc.update(updates)
                found = True
                break

        if not found:
            docs.append({"document_id": document_id, **updates})

        ci["customer_documents"] = docs[-20:]
        memory.company_info = ci
        await session.commit()


async def _get_registered_company_for_user(user_id: str, session: AsyncSession) -> str:
    result = await session.execute(
        select(User.enterprise_name, User.company).where(User.id == user_id)
    )
    row = result.first()
    if not row:
        return ""
    return row.enterprise_name or row.company or ""


def _normalize_company_name(name: str) -> str:
    """生成用于客户资料关联的稳定 company_key。"""
    value = (name or "").strip().lower()
    value = re.sub(r"[\s（）()【】\[\]·,，.。\-_/]+", "", value)
    suffixes = [
        "有限责任公司", "股份有限公司", "集团有限公司", "有限公司",
        "集团", "公司", "传媒", "广告", "文化", "科技",
    ]
    for suffix in suffixes:
        if value.endswith(suffix.lower()) and len(value) > len(suffix):
            value = value[: -len(suffix)]
    return value or "unknown"


def _merge_document_media_assets(
    existing: list,
    media_assets: list,
    source_filename: str = "",
    company_key: str = "",
    company_name: str = "",
) -> list:
    """将文档中的大屏/媒体资产合并到 screen_resources。"""
    merged = [dict(item) for item in (existing or []) if isinstance(item, dict)]

    def _key(item: dict) -> tuple[str, str]:
        return (
            str(item.get("company_key") or "").strip(),
            str(item.get("city") or "").strip(),
            str(item.get("location") or item.get("screen_location") or "").strip(),
        )

    index = {_key(item): i for i, item in enumerate(merged)}
    for asset in media_assets:
        if not isinstance(asset, dict):
            continue

        specs = asset.get("screen_specs") or {}
        daily_media_contacts = asset.get("daily_media_contacts") or _extract_daily_media_contacts(
            asset.get("audience_or_traffic") or []
        )
        item = {
            "company_key": company_key,
            "company_name": company_name,
            "city": asset.get("city", ""),
            "location": asset.get("screen_location", ""),
            "type": "、".join(asset.get("screen_features") or []),
            "size": specs.get("size", ""),
            "resolution": specs.get("resolution", ""),
            "daily_media_contacts": daily_media_contacts,
            "daily_traffic": "、".join(asset.get("audience_or_traffic") or []),
            "city_value": asset.get("city_value") or [],
            "location_features": asset.get("location_features") or [],
            "screen_features": asset.get("screen_features") or [],
            "screen_specs": specs,
            "audience_or_traffic": asset.get("audience_or_traffic") or [],
            "source": "uploaded_document",
            "source_filename": source_filename,
            "source_pages": asset.get("source_pages") or [],
        }

        key = _key(item)
        if key in index:
            existing_item = merged[index[key]]
            existing_item.update({k: v for k, v in item.items() if v})
        else:
            merged.append(item)

    return merged[-50:]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 爬取触发（后台异步）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def trigger_crawl(user_id: str, company_name: str):
    """后台异步触发公司官网爬取

    不阻塞当前请求，在后台完成搜索→爬取→提取→存储。
    """
    company_name = (company_name or "").strip()
    if not user_id or not company_name:
        return

    task_key = f"{user_id}:{company_name}"
    if task_key in _crawl_tasks:
        return

    async with async_session_maker() as session:
        memory = await get_or_create_memory(user_id, db=session)
        company_info = memory.company_info or {}
        crawl_status = company_info.get("crawl_status")
        if crawl_status == "success":
            return
        if crawl_status == "pending" and _pending_crawl_is_fresh(company_info):
            return
        memory.company_info = {
            **company_info,
            "name": company_name,
            "crawl_status": "pending",
            "crawl_started_at": datetime.now().isoformat(),
        }
        await session.commit()

    _crawl_tasks.add(task_key)
    task = asyncio.create_task(_background_crawl(user_id, company_name, task_key))
    task.add_done_callback(lambda _: _crawl_tasks.discard(task_key))


async def _background_crawl(user_id: str, company_name: str, task_key: str = ""):
    """后台爬取任务"""
    try:
        from app.services.crawl_service import crawl_and_extract

        async with _get_crawl_semaphore():
            print(f"[MemoryService] 开始后台爬取: user={user_id}, company={company_name}")
            result = await crawl_and_extract(company_name)

        await update_memory(user_id, {
            "company_info": result.get("company_info", {}),
            "screen_resources": result.get("screen_resources", []),
        })

        status = result.get("company_info", {}).get("crawl_status", "unknown")
        screens = len(result.get("screen_resources", []))
        print(f"[MemoryService] 爬取完成: status={status}, screens={screens}")

    except Exception as e:
        print(f"[MemoryService] 后台爬取失败: {e}")
        # 记录失败状态
        try:
            await update_memory(user_id, {
                "company_info": {
                    "name": company_name,
                    "crawl_status": "failed",
                    "error": str(e),
                    "crawled_at": datetime.now().isoformat(),
                },
            })
        except Exception:
            pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Prompt 注入 — 将 Memory 添加到 System Prompt
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def build_memory_context(memory: UserMemory | None) -> str:
    """将 Memory 构建为可注入 System Prompt 的上下文文本

    Args:
        memory: UserMemory 对象

    Returns:
        可追加到 system prompt 末尾的上下文文本
    """
    if not memory:
        return ""

    sections = []

    # 公司信息
    ci = memory.company_info or {}
    if ci.get("description"):
        sections.append(
            f"\n【客户背景信息 — 来自公司官网】\n"
            f"公司：{ci.get('name', '未知')}\n"
            f"简介：{ci.get('description', '')}\n"
        )
        if ci.get("advantages"):
            sections.append(f"核心优势：{'、'.join(ci['advantages'])}\n")

    doc_profile = ci.get("document_profile") or {}
    active_company_key = ci.get("active_company_key", "")
    companies = ci.get("documents_by_company") or {}
    active_company = companies.get(active_company_key) or {}
    if active_company.get("profile"):
        doc_profile = active_company.get("profile") or doc_profile
    if doc_profile or ci.get("document_brief"):
        lines = []
        if active_company.get("company_name"):
            lines.append(f"资料归属客户：{active_company['company_name']}")
        if doc_profile.get("company_name"):
            lines.append(f"公司名称：{doc_profile['company_name']}")
        if doc_profile.get("brand_name"):
            lines.append(f"品牌/项目：{doc_profile['brand_name']}")
        if doc_profile.get("industry"):
            lines.append(f"行业：{doc_profile['industry']}")
        if doc_profile.get("company_positioning"):
            lines.append(f"公司定位：{doc_profile['company_positioning']}")
        for label, key in [
            ("主营业务", "business_scope"),
            ("目标客群", "target_audience"),
            ("核心产品/服务", "products_or_services"),
            ("品牌卖点/优势", "selling_points"),
            ("品牌调性/视觉风格", "tone_and_style"),
            ("已有资产/案例", "existing_assets"),
            ("官网/渠道", "website_or_channels"),
        ]:
            values = doc_profile.get(key)
            if values:
                lines.append(f"{label}：{'、'.join(values[:8])}")
        doc_brief = active_company.get("brief") or ci.get("document_brief")
        if doc_brief:
            lines.append(f"资料摘要：{doc_brief}")
        sections.append(
            "\n【客户资料画像 — 来自管理员上传 PDF/PPT】\n"
            + "\n".join(lines)
            + "\n提示：这些信息来自客户资料，可用于主动理解客户行业、品牌调性和项目背景。\n"
        )

    # 屏幕资源
    screens = memory.screen_resources or []
    if active_company_key and any(s.get("company_key") for s in screens):
        screens = [
            s for s in screens
            if not s.get("company_key") or s.get("company_key") == active_company_key
        ]
    if screens:
        lines = []
        for s in screens:
            parts = []
            if s.get("company_name"):
                parts.append(f"客户：{s['company_name']}")
            parts.extend([s.get("city", ""), s.get("location", "")])
            if s.get("type"):
                parts.append(s["type"])
            if s.get("size"):
                parts.append(s["size"])
            if s.get("resolution"):
                parts.append(s["resolution"])
            if s.get("daily_traffic"):
                parts.append(f"日均客流{s['daily_traffic']}")
            if s.get("daily_media_contacts"):
                parts.append(f"日媒体接触人次{s['daily_media_contacts']}")
            if s.get("city_value"):
                parts.append(f"城市价值：{'、'.join(s['city_value'][:4])}")
            if s.get("location_features"):
                parts.append(f"位置特点：{'、'.join(s['location_features'][:4])}")
            if s.get("screen_features"):
                parts.append(f"大屏特点：{'、'.join(s['screen_features'][:4])}")
            specs = s.get("screen_specs") or {}
            spec_parts = [
                specs.get("aspect_ratio", ""),
                specs.get("orientation", ""),
                specs.get("duration", ""),
            ]
            if any(spec_parts):
                parts.append(f"规格补充：{'、'.join(p for p in spec_parts if p)}")
            lines.append(f"  • {' | '.join(p for p in parts if p)}")

        sections.append(
            f"\n【客户已知屏幕资源 — 共 {len(screens)} 块】\n"
            + "\n".join(lines) + "\n"
            "提示：你可以在对话开始时主动提及这些屏幕，询问本次项目是针对哪块屏幕。\n"
        )

    # 项目偏好
    pp = memory.project_preferences or {}
    if pp.get("preferred_styles") or pp.get("budget_range") or pp.get("common_cities"):
        pref_lines = []
        if pp.get("common_cities"):
            pref_lines.append(f"常用城市：{', '.join(pp['common_cities'])}")
        if pp.get("preferred_styles"):
            pref_lines.append(f"偏好风格：{', '.join(pp['preferred_styles'])}")
        if pp.get("budget_range"):
            pref_lines.append(f"预算范围：{pp['budget_range']}")
        if pp.get("typical_duration"):
            pref_lines.append(f"常用时长：{pp['typical_duration']}")
        if pp.get("notes"):
            pref_lines.append(f"备注：{pp['notes']}")
        # 显示数据新鲜度
        freshness = ""
        if pp.get("last_updated"):
            freshness = f"（更新于 {pp['last_updated'][:10]}）"
        sections.append(
            f"\n【客户历史偏好{freshness}】\n" + "\n".join(pref_lines) + "\n"
        )

    # 历史项目
    past = memory.past_projects or []
    if past:
        recent = past[-5:]  # 最近 5 个
        lines = []
        for p in recent:
            name = p.get("project_name") or p.get("order_number", "未命名")
            city = p.get("city", "")
            status_map = {
                "completed": "已完成", "in_production": "制作中",
                "pending_assign": "待确认", "cancelled": "已取消",
            }
            status = status_map.get(p.get("status", ""), p.get("status", ""))
            lines.append(f"  • {name} ({city}) — {status}")
        sections.append(
            f"\n【近期项目（{len(past)} 个）】\n" + "\n".join(lines) + "\n"
            "如涉及相似项目，可以引用历史经验提升专业度。\n"
        )

    # Agent 备忘
    if memory.agent_notes:
        sections.append(f"\n【Agent 备忘录】\n{memory.agent_notes}\n")

    return "\n".join(sections)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 对话学习 — 从对话中提取偏好写回 Memory
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def learn_from_conversation(user_id: str, conversation: list[dict]):
    """从对话历史中提取用户偏好，合并到 Memory

    在 /chat 返回后作为后台任务运行。
    只在对话超过 4 轮时执行（太短没有有价值的信息）。

    Args:
        user_id: 用户 ID
        conversation: 对话历史 [{"role": "user", "content": "..."}, ...]
    """
    # 只对有足够深度的对话进行学习
    user_msgs = [m for m in conversation if m.get("role") == "user"]
    if len(user_msgs) < 3:
        return

    semaphore = _get_background_semaphore()
    try:
        await asyncio.wait_for(semaphore.acquire(), timeout=0.1)
    except asyncio.TimeoutError:
        print(f"[MemoryService] 对话学习队列繁忙，跳过: user={user_id}")
        return

    try:
        extracted = await _extract_preferences(conversation)
        if not extracted:
            return

        # 合并到现有偏好
        async with async_session_maker() as session:
            memory = await get_or_create_memory(user_id, db=session)
            existing = memory.project_preferences or {}
            merged = _merge_preferences(existing, extracted)

            if merged != existing:
                memory.project_preferences = merged
                await session.commit()
                print(f"[MemoryService] 对话学习完成: user={user_id}, 更新了偏好")
            else:
                print(f"[MemoryService] 对话学习完成: 无新偏好")

    except Exception as e:
        print(f"[MemoryService] 对话学习失败: {e}")
    finally:
        semaphore.release()


async def _extract_preferences(conversation: list[dict]) -> dict:
    """用 LLM 从对话中提取用户偏好

    Returns:
        {
            "common_cities": ["成都"],
            "preferred_styles": ["科技感"],
            "budget_range": "20-30万",
            "typical_duration": "30秒",
            "screen_preferences": ["L型大屏"],
            "notes": "客户对交付时间比较敏感"
        }
    """
    import re
    import json
    from app.config import settings
    from app.services.ai_client import post_chat_completion

    if not settings.AI_API_KEY:
        return {}

    system_prompt = (
        "你是一个用户画像分析师。请分析以下客户与顾问的对话，"
        "提取客户透露的项目偏好和关键信息。\n\n"
        "只返回严格的 JSON，不要任何其他文字。\n"
        "如果对话中没有提到某个字段，就不要包含该字段。\n\n"
        "可提取的字段：\n"
        "- common_cities (list[string]): 提到的投放城市\n"
        "- preferred_styles (list[string]): 偏好的视觉风格，如'科技感'、'国潮'、'未来感'\n"
        "- budget_range (string): 预算范围，如'20-30万'\n"
        "- typical_duration (string): 视频时长偏好，如'30秒'\n"
        "- screen_preferences (list[string]): 偏好的屏幕类型，如'L型大屏'、'曲面屏'\n"
        "- notes (string): 其他值得记录的关键信息，一句话概括\n\n"
        "重要：只提取客户（user）明确提到的信息，不要推测。\n"
        "如果整段对话没有任何可提取的偏好信息，返回空对象 {}"
    )

    # 构建精简的对话文本（限制长度）
    dialog_text = ""
    for msg in conversation[-20:]:  # 最多取最近 20 条
        role = "客户" if msg.get("role") == "user" else "顾问"
        content = msg.get("content", "")[:200]  # 每条限 200 字
        dialog_text += f"{role}: {content}\n"

    if len(dialog_text) < 50:
        return {}

    try:
        data = await post_chat_completion(
            {
                "model": settings.AI_MODEL_NAME,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": dialog_text},
                ],
            },
            timeout=15.0,
        )
        content = data["choices"][0]["message"]["content"].strip()

        # 提取 JSON
        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            return json.loads(json_match.group(0))
        return {}
    except Exception as e:
        print(f"[MemoryService] LLM 提取偏好失败: {e}")
        return {}


def _merge_preferences(existing: dict, new: dict) -> dict:
    """智能合并偏好：累加列表项，更新标量值，记录时间戳

    规则：
    - 列表类型（cities, styles 等）：去重合并
    - 字符串类型（budget, duration）：新值覆盖旧值
    - notes：追加，不覆盖
    - 自动记录 last_updated 和各字段的更新时间
    """
    merged = {**existing}
    now = datetime.now().isoformat()
    changed_fields = []

    list_fields = ["common_cities", "preferred_styles", "screen_preferences"]
    for field in list_fields:
        if field in new and new[field]:
            old_list = merged.get(field, [])
            combined = list(dict.fromkeys(old_list + new[field]))
            if combined != old_list:
                merged[field] = combined
                changed_fields.append(field)

    scalar_fields = ["budget_range", "typical_duration"]
    for field in scalar_fields:
        if field in new and new[field]:
            if merged.get(field) != new[field]:
                merged[field] = new[field]
                changed_fields.append(field)

    # notes 追加
    if new.get("notes"):
        old_notes = merged.get("notes", "")
        if old_notes:
            if new["notes"] not in old_notes:
                merged["notes"] = f"{old_notes}；{new['notes']}"
                changed_fields.append("notes")
        else:
            merged["notes"] = new["notes"]
            changed_fields.append("notes")

    # 记录时间戳
    if changed_fields:
        merged["last_updated"] = now
        # 记录每个字段的最后更新时间
        field_timestamps = merged.get("_field_updated", {})
        for f in changed_fields:
            field_timestamps[f] = now
        merged["_field_updated"] = field_timestamps

    return merged


def _extract_daily_media_contacts(values: list) -> str:
    """兼容旧结构：从客流/曝光字段里提取日媒体接触人次。"""
    for value in values or []:
        text = str(value or "").strip()
        if not text:
            continue
        if "日媒体接触" in text or "日均媒体接触" in text:
            return text
        match = re.search(r"(日[^，、；;]*?(?:媒体接触|触达|接触人次)[^，、；;]*)", text)
        if match:
            return match.group(1)
    return ""
