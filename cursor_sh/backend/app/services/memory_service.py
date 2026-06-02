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
from app.database import async_session_maker
from app.config import settings
from app.utils.business_log import log_business_event
from app.utils.log_setup import get_module_logger
from app.utils.timezone import beijing_now, beijing_now_iso, ensure_beijing


logger = get_module_logger("ai")
_crawl_tasks: set[str] = set()
_crawl_semaphore: asyncio.Semaphore | None = None
_background_semaphore: asyncio.Semaphore | None = None

_AGENT_NOTE_PRIORITY_KEYWORDS = (
    "注意", "禁忌", "避免", "不要", "必须", "偏好", "风格", "主题", "创意",
    "审核", "交付", "预算", "屏幕", "点位", "规格", "格式", "时间", "周期",
    "品牌", "客户", "合作", "要求",
)

_PREFERENCE_NOTE_KEYWORDS = (
    "偏好", "风格", "主题", "创意", "目标", "定位", "调性", "禁用", "避免",
    "规避", "预算", "时长", "交付", "审核", "观看", "动线", "视角", "客流",
    "城市形象", "科技创新", "节日", "节庆",
)

_PROJECT_LOCATION_HINTS = (
    "项目为", "点位", "位置", "屏幕", "大屏", "裸眼3D大屏", "万象", "主广场",
    "购物中心", "商场", "大厦", "广场",
)


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

    started = ensure_beijing(started)
    ttl = max(60, int(settings.AI_CRAWL_PENDING_TTL_SECONDS or 1800))
    return (beijing_now() - started).total_seconds() < ttl


def _compact_agent_notes(notes: str, max_lines: int = 8, max_chars: int = 700) -> str:
    """压缩管理员/资料导入备注，仅用于 prompt 注入，不修改原始 memory。"""
    if not notes:
        return ""

    seen = set()
    candidates: list[str] = []
    for raw_line in notes.replace("\r", "\n").split("\n"):
        line = raw_line.strip().strip("-•* \t")
        if not line:
            continue
        if line.startswith("【") and line.endswith("】"):
            continue
        line = " ".join(line.split())
        if line in seen:
            continue
        seen.add(line)
        candidates.append(line)

    if not candidates:
        return ""

    prioritized = [line for line in candidates if any(k in line for k in _AGENT_NOTE_PRIORITY_KEYWORDS)]
    remaining = [line for line in candidates if line not in prioritized]
    selected = (prioritized + remaining)[:max_lines]

    compact_lines = []
    total = 0
    for line in selected:
        if len(line) > 120:
            line = line[:117].rstrip() + "..."
        projected = total + len(line) + 3
        if compact_lines and projected > max_chars:
            break
        compact_lines.append(f"- {line}")
        total = projected

    return "\n".join(compact_lines)


def _compact_preference_notes(notes: str, max_items: int = 6, max_chars: int = 360) -> str:
    """压缩历史偏好备注，保留可自然带出的关键线索，避免长文本重复注入。"""
    if not notes:
        return ""

    fragments: list[str] = []
    buffer = notes.replace("\r", "\n")
    for mark in ("；", ";", "。", "\n", "，", ","):
        buffer = buffer.replace(mark, "|")

    seen = set()
    project_keys = set()
    for raw_fragment in buffer.split("|"):
        fragment = " ".join(raw_fragment.strip().split())
        if not fragment:
            continue

        has_project_location = any(k in fragment for k in _PROJECT_LOCATION_HINTS)
        if not any(k in fragment for k in _PREFERENCE_NOTE_KEYWORDS + _PROJECT_LOCATION_HINTS):
            continue
        if has_project_location:
            project_key = fragment.split("的", 1)[0]
            for suffix in ("裸眼3D", "大屏", "屏幕", "项目", "视频"):
                project_key = project_key.replace(suffix, "")
            project_key = project_key.replace("项目为", "").strip(" ：:，,；;。")
            if project_key in project_keys:
                continue
            project_keys.add(project_key)

        fragment = fragment.replace("项目为", "历史项目线索：")
        fragment = fragment.replace("项目主题为", "主题为")
        fragment = fragment.replace("主题聚焦", "主题为")
        fragment = fragment.replace("定位侧重", "媒体定位侧重")
        fragment = fragment.replace("定位偏", "媒体定位偏")
        fragment = fragment.strip(" ：:，,；;。")
        if not fragment or fragment in seen:
            continue
        seen.add(fragment)
        fragments.append(fragment)

        if len(fragments) >= max_items:
            break

    if not fragments:
        return ""

    compact = "；".join(fragments)
    if len(compact) > max_chars:
        compact = compact[: max_chars - 3].rstrip("；,， ") + "..."
    return compact


def _stable_memory_values(values: list, *, exclude_project_specific: bool = False) -> list[str]:
    """过滤空值、占位值，以及容易被误用为本次项目的单次项目文本。"""
    if not values:
        return []
    if isinstance(values, str):
        values = [values]

    skipped_values = {"未提供", "未知", "暂无", "无", "不清楚"}
    stable: list[str] = []
    seen = set()
    for value in values:
        text = str(value).strip()
        if not text or text in skipped_values:
            continue
        if exclude_project_specific and any(k in text for k in _PROJECT_LOCATION_HINTS):
            continue
        if text in seen:
            continue
        seen.add(text)
        stable.append(text)
    return stable


def _stable_memory_scalar(value) -> str:
    text = str(value or "").strip()
    if text in {"未提供", "未知", "暂无", "无", "不清楚"}:
        return ""
    return text


def _migrate_legacy_preference_notes(memory: UserMemory) -> bool:
    """将旧版 project_preferences.notes 中的屏幕线索迁到 screen_resources。"""
    pp = dict(memory.project_preferences or {})
    notes = str(pp.get("notes") or "").strip()
    if not notes:
        return False

    fragments = [
        part.strip()
        for part in re.split(r"[；;。\n]", notes)
        if part.strip()
    ]
    if not fragments:
        return False

    migrated_screens: list[dict] = []
    remaining_notes: list[str] = []
    for fragment in fragments:
        screen = _screen_from_legacy_note_fragment(fragment)
        if screen:
            migrated_screens.append(screen)
        else:
            remaining_notes.append(fragment)

    if not migrated_screens:
        return False

    memory.screen_resources = _merge_screen_resources(
        memory.screen_resources or [],
        migrated_screens,
    )[-50:]

    compact_remaining = _compact_preference_notes("；".join(remaining_notes))
    if compact_remaining:
        pp["notes"] = compact_remaining
    else:
        pp.pop("notes", None)
    memory.project_preferences = pp
    return True


def _screen_from_legacy_note_fragment(fragment: str) -> dict | None:
    """从旧 notes 的单个片段中保守抽取屏幕资源。"""
    text = str(fragment or "").strip()
    if not _note_looks_screen_specific(text):
        return None

    name_patterns = [
        r"(?:投放点位?为|项目点位为|点位为|项目为)([^，；。]+?(?:大屏|屏幕|点位))",
        r"([\u4e00-\u9fa5A-Za-z0-9·（）()×xX:：/+-]+?(?:大屏|屏幕))",
    ]
    name = ""
    for pattern in name_patterns:
        match = re.search(pattern, text)
        if match:
            name = match.group(1).strip(" ，。；")
            break
    if not name:
        return None

    city = _extract_city_from_text(text) or _extract_city_from_text(name)
    specs = "；".join(
        part for part in [
            _first_match(text, r"\d+(?:\.\d+)?\s*(?:m|米)?\s*[×xX]\s*\d+(?:\.\d+)?\s*(?:m|米)?"),
            _first_match(text, r"\d+\s*[:：]\s*\d+\s*比例?"),
            _first_match(text, r"\d{3,5}\s*[xX×]\s*\d{3,5}"),
        ]
        if part
    )
    screen = {
        "city": city,
        "name": name,
        "notes": text,
        "source": {
            "type": "conversation",
            "migrated_from": "project_preferences.notes",
            "updated_at": beijing_now_iso(),
        },
    }
    if specs:
        screen["specs"] = specs
    return screen


def _extract_city_from_text(text: str) -> str:
    cities = (
        "北京", "上海", "深圳", "广州", "成都", "杭州", "重庆", "南京", "武汉",
        "西安", "苏州", "天津", "长沙", "郑州", "青岛", "厦门", "宁波",
    )
    for city in cities:
        if city in text:
            return city
    match = re.search(r"([\u4e00-\u9fa5]{2,6})市", text)
    return match.group(1) if match else ""


def _first_match(text: str, pattern: str) -> str:
    match = re.search(pattern, text)
    return match.group(0).strip() if match else ""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CRUD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def get_memory(user_id: str, db: AsyncSession | None = None) -> UserMemory | None:
    """获取用户 Memory"""
    if db:
        result = await db.execute(select(UserMemory).where(UserMemory.user_id == user_id))
        memory = result.scalar_one_or_none()
        if memory and _migrate_legacy_preference_notes(memory):
            await db.commit()
            await db.refresh(memory)
        return memory
    else:
        async with async_session_maker() as session:
            result = await session.execute(select(UserMemory).where(UserMemory.user_id == user_id))
            memory = result.scalar_one_or_none()
            if memory and _migrate_legacy_preference_notes(memory):
                await session.commit()
                await session.refresh(memory)
            return memory


async def get_or_create_memory(user_id: str, db: AsyncSession | None = None) -> UserMemory:
    """获取或创建用户 Memory"""
    async def _inner(session: AsyncSession) -> UserMemory:
        result = await session.execute(select(UserMemory).where(UserMemory.user_id == user_id))
        memory = result.scalar_one_or_none()
        if memory:
            if _migrate_legacy_preference_notes(memory):
                await session.commit()
                await session.refresh(memory)
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
                "first_contact": beijing_now_iso(),
                "last_contact": beijing_now_iso(),
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
        stats["last_contact"] = beijing_now_iso()
        if not stats.get("first_contact"):
            stats["first_contact"] = beijing_now_iso()

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
        project_info["updated_at"] = beijing_now_iso()

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
        memory.company_info = {
            **company_info,
            "name": company_name,
            "crawl_status": "pending",
            "crawl_started_at": beijing_now_iso(),
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
            log_business_event(
                logger,
                "memory_crawl_started",
                user_id=user_id,
                company_name=company_name,
                task_key=task_key,
            )
            result = await crawl_and_extract(company_name)

        await update_memory(user_id, {
            "company_info": result.get("company_info", {}),
            "screen_resources": result.get("screen_resources", []),
        })

        status = result.get("company_info", {}).get("crawl_status", "unknown")
        screens = len(result.get("screen_resources", []))
        log_business_event(
            logger,
            "memory_crawl_completed",
            user_id=user_id,
            company_name=company_name,
            task_key=task_key,
            crawl_status=status,
            screen_count=screens,
        )

    except Exception as e:
        log_business_event(
            logger,
            "memory_crawl_failed",
            level="error",
            user_id=user_id,
            company_name=company_name,
            task_key=task_key,
            error=str(e),
        )
        # 记录失败状态
        try:
            await update_memory(user_id, {
                "company_info": {
                    "name": company_name,
                    "crawl_status": "failed",
                    "error": "抓取失败，请稍后重试",
                    "crawled_at": beijing_now_iso(),
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
    company_context_lines = []
    if ci.get("description"):
        company_context_lines.append(f"简介：{ci.get('description', '')}")
    if ci.get("city_intro"):
        company_context_lines.append(f"城市介绍：{ci.get('city_intro', '')}")
    if ci.get("city_positioning"):
        company_context_lines.append(f"城市定位：{ci.get('city_positioning', '')}")
    if ci.get("business_context"):
        company_context_lines.append(f"商圈/商业背景：{ci.get('business_context', '')}")
    if ci.get("audience_profile"):
        company_context_lines.append(f"受众画像：{ci.get('audience_profile', '')}")
    if ci.get("media_value"):
        company_context_lines.append(f"媒体价值：{ci.get('media_value', '')}")
    if company_context_lines:
        sections.append(
            f"\n【客户背景信息 — 来自客户资料】\n"
            f"公司：{ci.get('name', '未知')}\n"
            + "\n".join(company_context_lines) + "\n"
        )
        if ci.get("advantages"):
            sections.append(f"核心优势：{'、'.join(ci['advantages'])}\n")

    # 屏幕资源
    screens = memory.screen_resources or []
    if screens:
        lines = []
        for s in screens:
            location = s.get("media_position") or s.get("location", "")
            parts = [s.get("city", ""), s.get("district", ""), s.get("name", "") or location]
            if s.get("specs"):
                parts.append(s["specs"])
            if s.get("type"):
                parts.append(s["type"])
            if s.get("size"):
                parts.append(s["size"])
            if s.get("area"):
                parts.append(s["area"])
            if s.get("resolution"):
                parts.append(s["resolution"])
            if s.get("play_frequency"):
                parts.append(f"播放频次{s['play_frequency']}")
            if s.get("play_time"):
                parts.append(f"播放时间{s['play_time']}")
            if s.get("list_price"):
                parts.append(f"刊例价{s['list_price']}")
            if s.get("location_intro"):
                parts.append(f"位置介绍{s['location_intro']}")
            if s.get("business_district"):
                parts.append(f"商圈{s['business_district']}")
            if s.get("surrounding_landmarks"):
                parts.append(f"周边{s['surrounding_landmarks']}")
            if s.get("audience_profile"):
                parts.append(f"受众{s['audience_profile']}")
            media_advantages = s.get("media_advantages") or []
            if isinstance(media_advantages, list) and media_advantages:
                parts.append(f"媒体优势{'、'.join(str(x) for x in media_advantages if str(x).strip())}")
            if s.get("notes"):
                parts.append(s["notes"])
            if s.get("daily_traffic"):
                parts.append(f"日媒体接触人次{s['daily_traffic']}")
            if s.get("holiday_traffic"):
                parts.append(f"节假日接触人次{s['holiday_traffic']}")
            if s.get("viewing_path"):
                parts.append(f"观看动线{s['viewing_path']}")
            lines.append(f"  • {' | '.join(p for p in parts if p)}")

        sections.append(
            f"\n【客户已知屏幕资源 — 共 {len(screens)} 块】\n"
            + "\n".join(lines) + "\n"
            "提示：第一轮开场不要主动提及这些屏幕。等客户描述完本次大方向后，"
            "可以用“我们了解到您这边有……”这类自然措辞提出候选屏幕，让客户确认本次项目是否针对其中某块屏。"
            "不要说“留存过”“记忆里”“Memory”等会让客户有压力的表达。"
            "不要对客户复述本段标题或“提示”这类内部说明。"
            "客户确认后，再把对应点位、尺寸、分辨率、客流等信息带入需求整理。\n"
        )

    # 项目偏好
    pp = memory.project_preferences or {}
    screen_names = {
        str(s.get("name") or s.get("location") or "").strip()
        for s in screens
        if isinstance(s, dict) and str(s.get("name") or s.get("location") or "").strip()
    }
    if (
        pp.get("preferred_styles") or pp.get("creative_goals") or
        pp.get("theme_concepts") or pp.get("content_taboos") or
        pp.get("budget_range") or pp.get("common_cities")
    ):
        pref_lines = []
        if pp.get("common_cities"):
            pref_lines.append(f"常用城市：{', '.join(pp['common_cities'])}")
        if pp.get("preferred_styles"):
            pref_lines.append(f"偏好风格：{', '.join(pp['preferred_styles'])}")
        if pp.get("creative_goals"):
            pref_lines.append(f"常见创意目标：{', '.join(pp['creative_goals'])}")
        if pp.get("theme_concepts"):
            pref_lines.append(f"历史内容主题：{', '.join(pp['theme_concepts'])}")
        if pp.get("content_taboos"):
            pref_lines.append(f"内容禁忌/规避项：{', '.join(pp['content_taboos'])}")
        reference_cases = [
            item for item in _stable_memory_values(pp.get("reference_cases", []))
            if item not in screen_names
        ]
        if reference_cases:
            pref_lines.append(f"历史参考案例/点位：{', '.join(reference_cases)}")
        budget_range = _stable_memory_scalar(pp.get("budget_range"))
        if budget_range:
            pref_lines.append(f"预算范围：{budget_range}")
        typical_duration = _stable_memory_scalar(pp.get("typical_duration"))
        if typical_duration:
            pref_lines.append(f"常用时长：{typical_duration}")
        if pp.get("notes"):
            compact_pref_notes = _compact_preference_notes(str(pp["notes"]))
            if compact_pref_notes:
                pref_lines.append(f"历史偏好摘要：{compact_pref_notes}")
        # 显示数据新鲜度
        freshness = ""
        if pp.get("last_updated"):
            freshness = f"（更新于 {pp['last_updated'][:10]}）"
        sections.append(
            f"\n【客户历史偏好{freshness}】\n" + "\n".join(pref_lines) + "\n"
            "这些线索要自然用于减少客户输入成本。可以用“我们了解到您这边有……”带出具体屏幕、点位或偏好，"
            "但它们不代表本次项目已确定。不要暗示双方已经有过该项目合作，除非客户在当前对话明确这样表述。"
            "使用前需要自然确认，客户确认前不要写入本次需求。"
            "不要对客户复述本段标题或内部说明。\n"
        )

    # 历史项目
    past = memory.past_projects or []
    if past:
        recent = past[-5:]  # 最近 5 个
        lines = []
        for p in recent:
            name = p.get("project_name") or p.get("order_number", "未命名")
            city = p.get("city", "")
            creative = "；".join(
                part for part in [p.get("art_direction", ""), p.get("theme_concept", "")]
                if part
            )
            status_map = {
                "completed": "已完成", "in_production": "制作中",
                "pending_assign": "待确认", "cancelled": "已取消",
            }
            status = status_map.get(p.get("status", ""), p.get("status", ""))
            extra = f"｜{creative}" if creative else ""
            lines.append(f"  • {name} ({city}) — {status}{extra}")
        sections.append(
            f"\n【近期项目（{len(past)} 个）】\n" + "\n".join(lines) + "\n"
            "这些只是历史参考，不能预设为客户本次项目。第一轮开场不要主动提及具体近期项目、点位或历史主题；"
            "只有当客户先描述了相似方向，或你需要降低客户输入成本时，才可以用自然语气提出候选并请客户确认。"
            "客户确认前，不要把近期项目内容写入本次需求。不要对客户复述本段标题或内部说明。\n"
        )

    # 管理员导入资料中抽取的过往案例
    doc_cases = ci.get("past_cases") or []
    if doc_cases:
        recent_cases = doc_cases[-8:]
        lines = []
        for c in recent_cases:
            parts = [
                c.get("brand", ""),
                c.get("title", ""),
                c.get("city", ""),
                c.get("content_type", ""),
            ]
            line = " | ".join(p for p in parts if p)
            if line:
                lines.append(f"  • {line}")
        if lines:
            sections.append(
                f"\n【客户资料中的过往案例 — 共 {len(doc_cases)} 个】\n"
                + "\n".join(lines) + "\n"
                "可作为理解客户业务和创意偏好的参考；如果要用于本次需求，仍需自然询问客户确认。不要对客户复述本段标题或内部说明。\n"
            )

    # Agent 备忘
    if memory.agent_notes:
        compact_notes = _compact_agent_notes(memory.agent_notes)
        if compact_notes:
            sections.append(
                "\n【Agent 备忘录摘要】\n"
                + compact_notes + "\n"
                "以上为压缩摘要，仅作内部参考；不要对客户复述本段标题或内部说明。\n"
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
        log_business_event(
            logger,
            "memory_learning_skipped",
            level="warning",
            user_id=user_id,
            reason="queue_busy",
        )
        return

    try:
        extracted = await _extract_preferences(conversation)
        if not extracted:
            return

        # 合并到现有偏好
        async with async_session_maker() as session:
            memory = await get_or_create_memory(user_id, db=session)
            new_screens = _normalize_conversation_screens(extracted.pop("screen_resources", []))
            if new_screens:
                memory.screen_resources = _merge_screen_resources(
                    memory.screen_resources or [],
                    new_screens,
                )[-50:]

            existing = memory.project_preferences or {}
            merged = _merge_preferences(existing, extracted)

            if merged != existing:
                memory.project_preferences = merged
                await session.commit()
                log_business_event(
                    logger,
                    "memory_learning_completed",
                    user_id=user_id,
                    updated_preferences=True,
                    updated_screens=bool(new_screens),
                )
            elif new_screens:
                await session.commit()
                log_business_event(
                    logger,
                    "memory_learning_completed",
                    user_id=user_id,
                    updated_preferences=False,
                    updated_screens=True,
                )
            else:
                log_business_event(
                    logger,
                    "memory_learning_completed",
                    user_id=user_id,
                    updated_preferences=False,
                    updated_screens=False,
                )

    except Exception as e:
        log_business_event(
            logger,
            "memory_learning_failed",
            level="error",
            user_id=user_id,
            error=str(e),
        )
    finally:
        semaphore.release()


async def _extract_preferences(conversation: list[dict]) -> dict:
    """用 LLM 从对话中提取用户偏好

    Returns:
        {
            "common_cities": ["成都"],
            "preferred_styles": ["科技感"],
            "creative_goals": ["招商展示"],
            "theme_concepts": ["城市文化"],
            "budget_range": "20-30万",
            "typical_duration": "30秒",
            "screen_preferences": ["L型大屏"],
            "screen_resources": [{"city": "深圳", "name": "万象天地主广场大屏", "specs": "30m×20m，3:2比例", "notes": "中轴步行道正向视角，需规避左右立柱遮挡"}],
            "content_taboos": ["过度商业广告化"],
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
        "- creative_goals (list[string]): 创意目标，如'招商展示'、'提升地标影响力'、'城市形象展示'\n"
        "- theme_concepts (list[string]): 内容主题或核心表达，如'城市文化'、'春节氛围'、'品牌招商'\n"
        "- content_taboos (list[string]): 明确不希望出现或需要规避的内容/调性\n"
        "- reference_cases (list[string]): 客户明确喜欢或提到的参考案例/参考方向\n"
        "- budget_range (string): 预算范围，如'20-30万'\n"
        "- typical_duration (string): 视频时长偏好，如'30秒'\n"
        "- screen_preferences (list[string]): 偏好的屏幕类型，如'L型大屏'、'曲面屏'\n"
        "- screen_resources (list[object]): 客户明确提到的具体屏幕资源，尽量简短；只使用 city, name, specs, notes 四个字段。city 是城市；name 是点位/屏幕名称，如'万象天地主广场大屏'；specs 是屏幕参数摘要，如'L型屏，3840x2160，约20m x 8m'；notes 是这块屏幕的观看动线、客流、遮挡、亮点、审核/上刊节点等屏幕相关补充。只有出现具体点位/屏幕名称/屏幕参数时才提取，不要只因为提到城市就生成屏幕资源\n"
        "- notes (string): 其他值得后续对话自然复用的非屏幕类线索，一句话概括；不要记录具体点位、屏幕参数、观看动线、遮挡、上刊节点等屏幕相关内容，这些应写入 screen_resources[].notes\n\n"
        "重要：只提取客户（user）明确提到的信息，不要推测。\n"
        "如果信息只属于某一次具体屏幕/点位，应优先放进 screen_resources；不要写成长段项目复述。\n"
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
        log_business_event(
            logger,
            "memory_preference_extract_failed",
            level="warning",
            message_count=len(conversation or []),
            error=str(e),
        )
        return {}


def _normalize_conversation_screens(value) -> list[dict]:
    """规范化从对话中抽取的屏幕资源，避免把泛泛城市写成屏幕。"""
    if not isinstance(value, list):
        return []

    allowed_fields = {"city", "name", "specs", "notes"}
    normalized: list[dict] = []
    now = beijing_now_iso()

    for raw in value:
        if not isinstance(raw, dict):
            continue
        item = {}
        for key in allowed_fields:
            text = str(raw.get(key) or "").strip()
            if text and text not in {"未知", "未提供", "暂无", "无", "不清楚"}:
                item[key] = text

        legacy_name = " ".join(
            str(raw.get(k) or "").strip()
            for k in ("location", "name")
            if str(raw.get(k) or "").strip()
        )
        if legacy_name and not item.get("name"):
            item["name"] = legacy_name

        legacy_specs = "，".join(
            str(raw.get(k) or "").strip()
            for k in ("type", "size", "resolution")
            if str(raw.get(k) or "").strip()
        )
        if legacy_specs and not item.get("specs"):
            item["specs"] = legacy_specs

        legacy_notes = "；".join(
            str(raw.get(k) or "").strip()
            for k in ("daily_traffic", "viewing_path", "highlights")
            if str(raw.get(k) or "").strip()
        )
        if legacy_notes and not item.get("notes"):
            item["notes"] = legacy_notes

        # 至少要有具体点位/屏幕名/参数之一，单独城市不算屏幕资源。
        if not any(item.get(k) for k in ("name", "specs")):
            continue

        item["source"] = {
            "type": "conversation",
            "updated_at": now,
        }
        normalized.append(item)

    return normalized


def _merge_screen_resources(existing: list, incoming: list) -> list[dict]:
    """按点位/名称合并屏幕资源；新对话补充的参数会更新旧记录。"""
    merged = [dict(item) for item in existing or [] if isinstance(item, dict)]
    index = {_screen_resource_key(item): i for i, item in enumerate(merged) if _screen_resource_key(item)}

    for item in incoming:
        key = _screen_resource_key(item)
        match_index = index.get(key) if key else None
        if match_index is None:
            match_index = _find_similar_screen_resource_index(merged, item)

        if match_index is not None:
            current = dict(merged[match_index])
            for field, value in item.items():
                if field == "source":
                    current["source"] = {
                        **(current.get("source") if isinstance(current.get("source"), dict) else {}),
                        **value,
                    }
                elif field == "name" and current.get("name"):
                    current[field] = _prefer_richer_text(current.get("name"), value)
                elif field in {"specs", "notes"} and current.get(field):
                    current[field] = _merge_text_fragments(str(current.get(field) or ""), str(value or ""))
                elif value:
                    current[field] = value
            merged[match_index] = current
            if key:
                index[key] = match_index
            continue

        merged.append(item)
        if key:
            index[key] = len(merged) - 1

    return merged


def _screen_resource_key(item: dict) -> str:
    city = str(item.get("city") or "").strip().lower()
    location = str(item.get("location") or "").strip().lower()
    name = _normalize_screen_name(str(item.get("name") or ""))
    screen_type = str(item.get("type") or "").strip().lower()
    specs = str(item.get("specs") or "").strip().lower()
    primary = "|".join(part for part in [city, name or location] if part)
    return primary or "|".join(part for part in [city, specs or screen_type] if part)


def _normalize_screen_name(name: str) -> str:
    """轻量规范化屏幕名称，帮助同一屏幕的多次描述合并。"""
    text = str(name or "").strip().lower()
    for token in ("深圳", "裸眼3d", "裸眼3D", "led", "LED", "屏幕", "大屏", "户外"):
        text = text.replace(token.lower(), "")
    text = text.replace("主广场", "广场")
    text = "".join(ch for ch in text if ch.isalnum() or "\u4e00" <= ch <= "\u9fff")
    return text


def _find_similar_screen_resource_index(existing: list[dict], incoming: dict) -> int | None:
    incoming_city = str(incoming.get("city") or "").strip().lower()
    incoming_name = _normalize_screen_name(str(incoming.get("name") or incoming.get("location") or ""))
    if not incoming_name or len(incoming_name) < 4:
        return None

    for idx, item in enumerate(existing):
        city = str(item.get("city") or "").strip().lower()
        if incoming_city and city and incoming_city != city:
            continue
        existing_name = _normalize_screen_name(str(item.get("name") or item.get("location") or ""))
        if len(existing_name) < 4:
            continue
        if incoming_name in existing_name or existing_name in incoming_name:
            return idx
    return None


def _prefer_richer_text(current, incoming) -> str:
    current_text = str(current or "").strip()
    incoming_text = str(incoming or "").strip()
    if not current_text:
        return incoming_text
    if not incoming_text:
        return current_text
    return current_text if len(current_text) >= len(incoming_text) else incoming_text


def _merge_text_fragments(current: str, incoming: str, max_items: int = 8) -> str:
    fragments: list[str] = []
    for text in (current, incoming):
        for part in str(text or "").replace("；", "|").replace("，", "|").replace(",", "|").split("|"):
            fragment = part.strip()
            if fragment and fragment not in fragments:
                fragments.append(fragment)
    return "；".join(fragments[:max_items])


def _note_looks_screen_specific(note: str) -> bool:
    note = str(note or "")
    screen_markers = (
        "点位", "屏幕", "大屏", "分辨率", "尺寸", "比例", "观看动线", "观看方向",
        "视角", "客流", "遮挡", "立柱", "上刊", "终审", "报审", "万象天地",
    )
    return any(marker in note for marker in screen_markers)


def _merge_preferences(existing: dict, new: dict) -> dict:
    """智能合并偏好：累加列表项，更新标量值，记录时间戳

    规则：
    - 列表类型（cities, styles 等）：去重合并
    - 字符串类型（budget, duration）：新值覆盖旧值
    - notes：追加，不覆盖
    - 自动记录 last_updated 和各字段的更新时间
    """
    merged = {**existing}
    now = beijing_now_iso()
    changed_fields = []

    list_fields = [
        "common_cities", "preferred_styles", "screen_preferences",
        "creative_goals", "theme_concepts", "content_taboos", "reference_cases",
    ]
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
    if new.get("notes") and not _note_looks_screen_specific(new["notes"]):
        new_notes = _compact_preference_notes(str(new["notes"]))
        if new_notes:
            old_notes = merged.get("notes", "")
            if old_notes:
                compact_notes = _compact_preference_notes(f"{old_notes}；{new_notes}")
                if compact_notes != old_notes:
                    merged["notes"] = compact_notes
                    changed_fields.append("notes")
            else:
                merged["notes"] = new_notes
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
