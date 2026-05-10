"""用户画像 Memory 服务

提供 Memory 的 CRUD、对话上下文注入、爬取触发等功能。
"""

import uuid
import asyncio
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_memory import UserMemory
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


def _now_iso() -> str:
    return datetime.now().isoformat()


def _stamp_company_info(company_info: dict, now: str) -> dict:
    if not isinstance(company_info, dict):
        return {}
    stamped = {**company_info}
    stamped["updated_at"] = now
    if stamped.get("crawl_status") == "success" and not stamped.get("crawled_at"):
        stamped["crawled_at"] = now
    return stamped


def _screen_resource_key(item: dict) -> tuple:
    return (
        str(item.get("city", "")).strip(),
        str(item.get("location", "")).strip(),
        str(item.get("type", "")).strip(),
        str(item.get("size", "")).strip(),
        str(item.get("resolution", "")).strip(),
    )


def _stamp_screen_resources(resources: list, now: str, existing_resources: list | None = None) -> list:
    if not isinstance(resources, list):
        return []

    existing_by_key = {}
    if isinstance(existing_resources, list):
        for item in existing_resources:
            if isinstance(item, dict):
                existing_by_key[_screen_resource_key(item)] = item

    stamped = []
    for item in resources:
        if not isinstance(item, dict):
            continue
        previous = existing_by_key.get(_screen_resource_key(item), {})
        stamped.append({
            **item,
            "first_seen_at": item.get("first_seen_at") or previous.get("first_seen_at") or now,
            "last_seen_at": now,
        })
    return stamped


def _stamp_project_preferences(preferences: dict, now: str) -> dict:
    if not isinstance(preferences, dict):
        return {}
    if preferences and not preferences.get("last_updated"):
        return {**preferences, "last_updated": now}
    return preferences


def _short_date(value: str | None) -> str:
    if not value:
        return ""
    return str(value)[:10]


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

        now = _now_iso()
        memory = UserMemory(
            id=str(uuid.uuid4()),
            user_id=user_id,
            company_info={},
            screen_resources=[],
            project_preferences={},
            past_projects=[],
            interaction_stats={
                "total_sessions": 0,
                "first_contact": now,
                "last_contact": now,
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

        now = _now_iso()
        for key, value in updates.items():
            if hasattr(memory, key):
                if key == "company_info":
                    value = _stamp_company_info(value, now)
                elif key == "screen_resources":
                    value = _stamp_screen_resources(value, now, memory.screen_resources or [])
                elif key == "project_preferences":
                    value = _stamp_project_preferences(value, now)
                setattr(memory, key, value)

        if "agent_notes" in updates:
            stats = {**(memory.interaction_stats or {})}
            if not stats.get("agent_notes_created_at"):
                stats["agent_notes_created_at"] = now
            stats["agent_notes_updated_at"] = now
            memory.interaction_stats = stats

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
        stats = {**(memory.interaction_stats or {})}
        stats["total_sessions"] = stats.get("total_sessions", 0) + 1
        now = _now_iso()
        stats["last_contact"] = now
        if not stats.get("first_contact"):
            stats["first_contact"] = now

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
        project_info["updated_at"] = _now_iso()

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
        now = _now_iso()
        memory.company_info = {
            **company_info,
            "name": company_name,
            "crawl_status": "pending",
            "crawl_started_at": now,
            "updated_at": now,
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
                    "crawled_at": _now_iso(),
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

    sections = [
        (
            "\n【客户记忆使用规则】\n"
            "- 本轮用户明确提供的信息优先级最高；当前结构化需求状态优先于历史记忆。\n"
            "- 客户记忆只能作为参考、候选项和追问线索，不能替客户确认本次需求。\n"
            "- 如果记忆与本轮对话冲突，以本轮对话为准，并可自然确认差异。\n"
            "- 引用记忆时要像顾问自然承接，不要说“根据系统记忆”等系统化表述。\n"
        )
    ]

    # 公司信息
    ci = memory.company_info or {}
    if ci.get("description"):
        advantages = ci.get("advantages") or []
        advantage_text = f"\n- 可参考优势：{'、'.join(advantages[:4])}" if advantages else ""
        source_date = _short_date(ci.get("crawled_at") or ci.get("updated_at"))
        source_text = f"\n- 信息时间：{source_date}" if source_date else ""
        sections.append(
            f"\n【顾问线索：客户背景】\n"
            f"- 公司：{ci.get('name', '未知')}\n"
            f"- 简介：{ci.get('description', '')[:300]}"
            f"{advantage_text}"
            f"{source_text}\n"
            "- 使用方式：可用于理解客户行业与资源背景，不要替客户确认本次项目目标。\n"
        )

    # 屏幕资源
    screens = memory.screen_resources or []
    if screens:
        lines = []
        for s in screens[:5]:
            parts = [s.get("city", ""), s.get("location", "")]
            if s.get("type"):
                parts.append(s["type"])
            if s.get("size"):
                parts.append(s["size"])
            if s.get("resolution"):
                parts.append(s["resolution"])
            if s.get("daily_traffic"):
                parts.append(f"日均客流{s['daily_traffic']}")
            if s.get("last_seen_at"):
                parts.append(f"更新时间{_short_date(s['last_seen_at'])}")
            lines.append(f"  • {' | '.join(p for p in parts if p)}")

        more = f"\n  • 另有 {len(screens) - 5} 块资源未展开" if len(screens) > 5 else ""
        sections.append(
            f"\n【顾问线索：已知屏幕资源 — 共 {len(screens)} 块】\n"
            + "\n".join(lines) + more + "\n"
            "- 使用方式：如果本轮尚未说明投放点位，可询问是否针对其中某块屏幕；不要默认选用。\n"
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
            f"\n【顾问线索：历史偏好{freshness}】\n"
            + "\n".join(f"- {line}" for line in pref_lines) + "\n"
            "- 使用方式：可作为候选项帮助客户更快表达，但本轮用户新说法优先。\n"
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
            f"\n【顾问线索：近期项目（{len(past)} 个）】\n" + "\n".join(lines) + "\n"
            "- 使用方式：如本轮项目相似，可以自然引用历史经验；不要把历史项目字段当作本次需求。\n"
        )

    # Agent 备忘
    if memory.agent_notes:
        stats = memory.interaction_stats or {}
        note_date = _short_date(stats.get("agent_notes_updated_at"))
        note_title = f"（更新于 {note_date}）" if note_date else ""
        sections.append(
            f"\n【顾问线索：人工备忘{note_title}】\n"
            f"{memory.agent_notes[:500]}\n"
            "- 使用方式：人工备忘优先作为沟通偏好和注意事项，仍需以本轮用户表述为准。\n"
        )

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
        "提取客户透露的、未来对话可复用的稳定偏好和沟通线索。\n\n"
        "只返回严格的 JSON，不要任何其他文字。\n"
        "如果对话中没有提到某个字段，就不要包含该字段。\n\n"
        "可提取的字段：\n"
        "- common_cities (list[string]): 客户反复使用、明确表示常用或长期关注的投放城市\n"
        "- preferred_styles (list[string]): 客户明确表达的长期视觉偏好，如'科技感'、'国潮'、'未来感'\n"
        "- budget_range (string): 客户常见或可复用的预算区间，如'20-30万'\n"
        "- typical_duration (string): 客户常用的视频时长偏好，如'30秒'\n"
        "- screen_preferences (list[string]): 客户常用或明确偏好的屏幕类型，如'L型大屏'、'曲面屏'\n"
        "- notes (string): 其他值得记录的关键信息，一句话概括\n\n"
        "重要规则：\n"
        "- 只提取客户（user）明确提到的信息，不要推测。\n"
        "- 不要把单次项目事实直接当作长期偏好；例如'这次投上海'不是 common_cities，"
        "除非客户说'我们通常投上海'或历史对话里反复出现。\n"
        "- 不要记录已经被客户纠正或否定的旧信息，以最新表达为准。\n"
        "- notes 只记录未来沟通有价值的稳定线索，不记录一次性执行细节。\n"
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
