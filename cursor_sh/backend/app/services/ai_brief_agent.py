"""State-driven Brief agent helpers for media-side requirement collection."""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from app.services.ai_brief_state import FIELD_LABELS
from app.services.memory_sanitizer import sanitize_reusable_memory_text
from app.utils.log_setup import get_module_logger
from app.utils.timezone import beijing_now


logger = get_module_logger("ai")


BRIEF_CATEGORY_GROUPS = [
    {
        "key": "basic_info",
        "label": "基础信息",
        "fields": ("city_location", "resource_background", "audience_scene", "viewing_path"),
        "question": "基础信息这边，我想先补一个最影响判断的点：投放点位、现场观看关系或目标受众里，您现在方便先确认哪一项？",
    },
    {
        "key": "creative_direction",
        "label": "创意方向",
        "fields": ("theme_concept", "art_direction", "content_review", "special_requirements"),
        "question": "创意方向这边，我想先把核心画面机制收清楚：主体、动作或视觉风格里，您最想先确定哪一个？",
    },
    {
        "key": "tech_delivery",
        "label": "技术与交付",
        "fields": ("media_specs", "timing_number", "tech_delivery", "online_time", "budget", "site_photos"),
        "question": "技术与交付这边，我想先确认一个会影响制作判断的条件：屏幕规格、交付时间或素材资料里，您现在手头最明确的是哪一项？",
    },
]

BRIEF_CATEGORY_BY_FIELD = {
    field: category
    for category in BRIEF_CATEGORY_GROUPS
    for field in category["fields"]
}


QUESTION_KEYWORDS_BY_FIELD = {
    "city_location": ("投放点位", "屏幕位置", "城市、屏幕位置", "哪块屏", "哪个城市", "点位", "投放在哪里"),
    "media_specs": ("屏幕规格", "已有规格", "规格", "分辨率", "物理尺寸", "屏幕尺寸", "4k", "8k", "2k"),
    "theme_concept": ("内容或主题", "内容主题", "核心表达", "主要想做什么", "创意方向"),
    "viewing_path": ("观看动线", "观看方向", "哪个方向观看", "正面", "斜侧", "仰视"),
    "audience_scene": ("哪类人群", "观看场景", "目标受众", "面向"),
    "art_direction": ("风格偏好", "视觉气质", "艺术方向"),
    "online_time": ("预计上刊", "上线时间", "交付时间", "活动时间"),
    "content_review": ("审核规范", "禁忌", "避免", "表现尺度"),
    "site_photos": ("现场实拍图", "屏幕照片", "参考素材", "素材", "上传"),
}


def _field_value(brief_state: dict[str, Any] | None, field: str) -> str:
    value = ((brief_state or {}).get("fields") or {}).get(field, {})
    if isinstance(value, dict):
        return str(value.get("value") or "").strip()
    return str(value or "").strip()


def _filled_fields(brief_state: dict[str, Any] | None) -> set[str]:
    return {
        field
        for field in ((brief_state or {}).get("fields") or {})
        if _field_value(brief_state, field)
    }


def _creative_evaluation_hint_status(agent_state: dict[str, Any] | None) -> str:
    hint = (agent_state or {}).get("creative_evaluation_hint")
    if not isinstance(hint, dict):
        return ""
    return str(hint.get("status") or "").strip()


def should_show_creative_evaluation_hint(agent_state: dict[str, Any] | None) -> bool:
    """Return true once the creative direction has enough shape for a non-blocking evaluation hint."""
    if _creative_evaluation_hint_status(agent_state):
        return False
    if (agent_state or {}).get("pending_evaluation"):
        return False
    if (agent_state or {}).get("pending_creative_direction"):
        return False

    brief_state = (agent_state or {}).get("brief_state") or {}
    if _pending_confirmation(brief_state):
        return False

    filled = _filled_fields(brief_state)
    has_creative_shape = {"theme_concept", "art_direction"}.issubset(filled)
    has_basic_grounding = bool({"city_location", "viewing_path", "audience_scene", "resource_background"} & filled)
    return has_creative_shape and has_basic_grounding


def mark_creative_evaluation_hint_shown(agent_state: dict[str, Any] | None) -> dict[str, Any]:
    next_state = deepcopy(agent_state or {})
    brief_state = next_state.get("brief_state") or {}
    now = beijing_now().isoformat()
    next_state["creative_evaluation_hint"] = {
        "status": "shown",
        "source": "brief_agent",
        "brief_version": int(brief_state.get("version") or 0),
        "updated_at": now,
    }
    next_state["updated_at"] = now
    return next_state


def _pending_confirmation(brief_state: dict[str, Any] | None) -> dict[str, Any] | None:
    pending = (brief_state or {}).get("pending_confirmation")
    if not isinstance(pending, dict):
        return None
    field = str(pending.get("field") or "").strip()
    candidate = _compact_hint(pending.get("candidate_value"))
    if not field or not candidate or _field_value(brief_state, field):
        return None
    return pending


def _display_candidate_hint(value: Any) -> str:
    text = _compact_hint(value)
    # Memory screen resources often store both city and screen name. Avoid
    # showing duplicated city text such as "杭州 杭州巨屏" to the user.
    text = re.sub(r"^([\u4e00-\u9fa5]{2,4})\s+\1", r"\1", text)
    return text


def _compact_hint(value: Any, max_chars: int = 120) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip(" ，,；;。")
    if len(text) > max_chars:
        return text[: max_chars - 3].rstrip(" ，,；;。") + "..."
    return text


def _memory_value(memory: Any, key: str) -> Any:
    if isinstance(memory, dict):
        return memory.get(key)
    return getattr(memory, key, None)


def _first_nonempty(*values: Any) -> str:
    for value in values:
        text = _compact_hint(sanitize_reusable_memory_text(value))
        if text:
            return text
    return ""


def _append_unique_candidate(candidates: list[str], value: str, max_items: int = 3) -> None:
    text = _compact_hint(value)
    if not text or text in candidates or len(candidates) >= max_items:
        return
    candidates.append(text)


def _join_candidates(candidates: list[str]) -> str:
    return "；".join(candidate for candidate in candidates if candidate)


def build_brief_memory_hints(memory: Any) -> dict[str, str]:
    """Extract non-confirmed Brief candidates from user memory."""
    if not memory:
        return {}

    hints: dict[str, str] = {}
    candidate_lists: dict[str, list[str]] = {
        "city_location": [],
        "media_specs": [],
        "viewing_path": [],
        "audience_scene": [],
    }
    screens = _memory_value(memory, "screen_resources") or []
    if isinstance(screens, list):
        for screen in screens:
            if not isinstance(screen, dict):
                continue
            city_location = _compact_hint(
                " ".join(
                    part
                    for part in [
                        screen.get("city"),
                        screen.get("district"),
                        screen.get("name") or screen.get("location") or screen.get("media_position"),
                    ]
                    if _compact_hint(part)
                )
            )
            media_specs = _first_nonempty(
                screen.get("specs"),
                screen.get("resolution"),
                screen.get("size"),
                screen.get("area"),
                screen.get("type"),
            )
            viewing_path = _first_nonempty(screen.get("viewing_path"), screen.get("notes"))
            audience_scene = _first_nonempty(screen.get("audience_profile"))
            _append_unique_candidate(candidate_lists["city_location"], city_location)
            _append_unique_candidate(
                candidate_lists["media_specs"],
                f"{city_location}：{media_specs}" if city_location and media_specs else media_specs,
            )
            _append_unique_candidate(
                candidate_lists["viewing_path"],
                f"{city_location}：{viewing_path}" if city_location and viewing_path else viewing_path,
            )
            _append_unique_candidate(
                candidate_lists["audience_scene"],
                f"{city_location}：{audience_scene}" if city_location and audience_scene else audience_scene,
            )

    preferences = _memory_value(memory, "project_preferences") or {}
    if isinstance(preferences, dict):
        common_cities = preferences.get("common_cities") or []
        if isinstance(common_cities, str):
            common_cities = [common_cities]
        common_city_text = "、".join(_compact_hint(city, 24) for city in common_cities[:3] if _compact_hint(city))
        if common_city_text and not candidate_lists["city_location"]:
            _append_unique_candidate(candidate_lists["city_location"], common_city_text)

    for field, candidates in candidate_lists.items():
        joined = _join_candidates(candidates)
        if joined:
            hints[field] = joined

    return hints


def _pending_confirmation_question(pending: dict[str, Any]) -> str:
    field = str(pending.get("field") or "")
    hint_text = _display_candidate_hint(pending.get("candidate_value"))
    if field == "city_location":
        return (
            f"这个方向我先记下。我们了解到您这边常用的投放城市或屏幕线索是「{hint_text}」，"
            "这次也是基于这个城市或点位来做吗？如果不是，也可以直接说新的城市或屏幕。"
        )
    if field == "media_specs":
        return (
            f"点位方向我先记录。我们了解到这块屏幕的规格线索是「{hint_text}」，"
            "这次先按这个规格来适配吗？如果参数有更新，也可以直接告诉我。"
        )
    return (
        f"我先记下当前方向。我们了解到有一个可参考的信息是「{hint_text}」，"
        "这次是否按这个来推进？如果不是，也可以直接告诉我新的信息。"
    )


def _pending_confirmation_llm_context(pending: dict[str, Any]) -> str:
    field = str(pending.get("field") or "")
    label = str(pending.get("label") or FIELD_LABELS.get(field, field))
    candidate = _compact_hint(pending.get("candidate_value"), 240)
    if not candidate:
        return ""
    return (
        f"- 待确认字段：{label}。\n"
        f"- 候选信息：{candidate}。\n"
        "- 回复中必须带出候选信息里的核心内容，不能只说“一组信息”“一组规格”“可参考信息”。\n"
        "- 你需要先理解候选信息，再用自然措辞向用户确认；不要原样罗列候选信息，"
        "如果候选里有重复表述，要自行合并为一句清楚的话。\n"
        "- 对外措辞使用“我们了解到……”或“这块屏幕大致……”这类自然表达；"
        "不要说 Memory、候选、系统记录、当前 Brief。\n"
    )


def select_next_brief_question(
    brief_state: dict[str, Any] | None,
    filled_overrides: set[str] | None = None,
    memory_hints: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    """Choose the next Brief focus from the three fixed Brief categories."""
    pending = _pending_confirmation(brief_state)
    if pending:
        field = str(pending.get("field") or "")
        category = BRIEF_CATEGORY_BY_FIELD.get(field) or {}
        return {
            "field": field,
            "category": str(category.get("key") or ""),
            "missing_fields": [field],
            "label": str(pending.get("label") or FIELD_LABELS.get(field, field)),
            "question": _pending_confirmation_question(pending),
        }

    filled = _filled_fields(brief_state) | set(filled_overrides or set())
    for category in BRIEF_CATEGORY_GROUPS:
        missing = [field for field in category["fields"] if field not in filled]
        if missing:
            return {
                "field": missing[0],
                "category": category["key"],
                "label": category["label"],
                "missing_fields": missing,
                "missing_labels": [FIELD_LABELS.get(field, field) for field in missing],
                "question": category["question"],
            }
    return None


def _brief_category_gap_lines(brief_state: dict[str, Any], filled: set[str]) -> str:
    lines = []
    for category in BRIEF_CATEGORY_GROUPS:
        missing_labels = [
            FIELD_LABELS.get(field, field)
            for field in category["fields"]
            if field not in filled
        ]
        if missing_labels:
            lines.append(f"- {category['label']}：{', '.join(missing_labels)}")
        else:
            lines.append(f"- {category['label']}：暂无明显缺口")
    return "\n".join(lines)


def build_brief_agent_instruction(
    agent_state: dict[str, Any] | None,
    memory_hints: dict[str, str] | None = None,
) -> str:
    brief_state = (agent_state or {}).get("brief_state") or {}
    next_question = select_next_brief_question(brief_state)
    filled = sorted(_filled_fields(brief_state))
    filled_set = set(filled)
    filled_labels = [FIELD_LABELS.get(field, field) for field in filled]
    pending = _pending_confirmation(brief_state)
    pending_block = ""
    if pending:
        pending_block = (
            "- 当前存在一个待用户确认的 Brief 候选。只能围绕该候选确认，不要把它当成已确认事实，也不要重复问开放式城市/规格问题。\n"
        )
    creative_evaluation_hint_block = ""
    if should_show_creative_evaluation_hint(agent_state):
        creative_evaluation_hint_block = (
            "- 本轮需要插入一次非阻塞创意评估提醒：如果用户已有自己的创意概念，可以随时发来做创意评估；"
            "如果没有，后续也会基于当前 Brief 生成一版 AI 创意方向。\n"
            "- 这个提醒不能变成一个选择题，不要要求用户回答“有/没有”，不要创建等待状态；提醒后必须继续当前 Brief 的自然下一问。\n"
            "- 下一问必须由当前 Brief 缺口决定，不要把下一问锁定为屏幕规格、交付时间或任何固定字段。\n"
        )

    if not next_question:
        return (
            "\n\n【Brief 子 Agent 下一问约束】\n"
            "- 当前 Brief 核心字段已基本齐全。不要重复追问已填字段；如需收尾，优先确认是否进入需求单整理。\n"
        )

    return (
        "\n\n【Brief 子 Agent 下一问约束】\n"
        "- 追问必须基于当前动态 Brief 状态，而不是固定模板。\n"
        f"- 已填字段：{', '.join(filled_labels) if filled_labels else '暂无'}。\n"
        "- Brief 固定分为三大类：基础信息、创意方向、技术与交付。总体按这个顺序推进，但不是字段硬顺序；你可以在当前大类里自行判断下一步问哪个缺口最自然、最有判断价值。\n"
        + "当前三大类缺口：\n"
        + _brief_category_gap_lines(brief_state, filled_set)
        + "\n"
        + pending_block
        + creative_evaluation_hint_block
        + "- 可以按信息复杂度给出专业判断承接用户刚补充的信息，说明它对创意成立、裸眼3D空间、制作或上刊判断的影响；这不是每轮必须，用户只是短答、确认或信息很少时可以直接自然追问，避免啰嗦，也不要只做机械确认。\n"
        + "- 如果本轮涉及关键 Brief 信息，例如点位、规格、观看关系、创意动作机制、预算周期、审核边界或交付要求，可以适度展开专业影响；但不要为了显得专业而写成小报告。\n"
        + "- 承接必须优先回应用户最新输入，不要复述上一轮 assistant 的专业判断；如果用户刚回答的是参数、时间、受众这类短信息，先确认这条新信息的作用，再追问下一个缺口。\n"
        + "- 避免连续使用同一种过渡句式，尤其不要每轮都用“既然……已经明确”“接下来我们需要……”。可以直接用更轻的承接，例如“这个信息够用了”“我先按这个记录”“下一步主要看……”。\n"
        + "- 提问时保留真实答案空间。不要为了让用户少输入，就把开放需求临时写成“A 还是 B”；列出两个方向或几个示例也不代表答案集合已经封闭。只有业务枚举、用户已有候选或客观有限的答案集合，才适合直接列候选。\n"
        + "- 如果信息密度较高、包含多个判断点，或需要同时承接信息与追问，可以使用简洁 Markdown 提升可读性；Markdown 不是固定模板，可以只是自然分段、少量加粗关键事实或关键判断，或少量列表。\n"
        + "- 当回复同时包含专业判断和下一问时，必须分成至少两个短段落，最后一个问题单独成段。\n"
        + "- 凡是会进入 Brief 的内容信息都属于重点信息，包括用户刚确认或补充的信息、状态里已确认并用于承接的信息、需要用户确认的候选信息，以及影响下一步判断的关键字段。\n"
        + "- 加粗只用于帮助客户快速抓住关键事实或关键结论；可以克制地少量加粗具体 Brief 内容，例如点位、屏幕规格、观看视角、主题、角色、风格、动作机制、受众、预算、上刊时间、审核边界、交付规格、参考素材状态或短判断。\n"
        + "- 只加粗具体 Brief 内容或关键判断，不加粗模板词、流程词或固定标题，比如“已记录”“下一步”“重点判断”。只有纯确认或一句话短追问可以不加粗；如果回复同时承担解释、判断和引导，需要自然使用 2-4 个阅读锚点。阅读锚点由语义选择，可以是核心概念、关键判断、关键范围或用户最需要记住的信息。\n"
        + "- 不要每轮都使用固定标题，如 **重点判断**、**下一步**。\n"
        + f"- 下一轮优先关注大类：「{next_question['label']}」。只提出一个需要用户回答的任务。按用户需要完成的回答动作判断："
        "如果用户必须分别提供两类信息或作出两个决定，就属于两个任务，不能因为写在同一句或只有一个问号而合并追问。"
        "回复前自检用户是否只需决定、确认或说明一件事；否则只保留当前最相关的一问，其余留到后续轮次。\n"
        + (
            _pending_confirmation_llm_context(pending)
            if pending
            else (
                f"- 下一问可覆盖的缺口字段：{', '.join(next_question.get('missing_labels') or [next_question['label']])}。\n"
                "- 不要输出字段清单，不要问用户想先确认哪一项；必须自行选择一个最有判断价值的具体缺口，直接问一个具体问题。\n"
                "- 如果用户上一轮只是选择了某个信息维度、但没有给出具体内容，要围绕该维度追问具体内容；"
                "如果该维度在当前 Brief 中已存在，则自然转向同大类里未填的具体缺口。\n"
            )
        )
        + "- 禁止追问已填字段；如果点位、屏幕位置或规格已在状态中存在，不要再问投放点位或屏幕规格。\n"
    )


def _asked_filled_fields(reply: str, brief_state: dict[str, Any]) -> set[str]:
    question = _last_question_text(reply).lower()
    if not question:
        return set()
    filled = _filled_fields(brief_state)
    asked: set[str] = set()
    for field, keywords in QUESTION_KEYWORDS_BY_FIELD.items():
        if field not in filled:
            continue
        if any(keyword.lower() in question for keyword in keywords):
            asked.add(field)
    return asked


def _last_question_text(reply: str) -> str:
    text = str(reply or "")[-400:]
    question_marks = [text.rfind("？"), text.rfind("?")]
    end = max(question_marks)
    if end < 0:
        return ""
    before = text[:end]
    start = max(before.rfind("\n"), before.rfind("。"), before.rfind("！"), before.rfind("!"), before.rfind("？"), before.rfind("?"))
    return text[start + 1 : end + 1].strip()


def _remove_redundant_trailing_question(reply: str, asked_fields: set[str]) -> str:
    if not asked_fields:
        return reply

    exact_patterns = [
        (
            r"\n*\s*我还需要再补充一个关键信息："
            r"这次项目对应的投放点位或屏幕规格目前方便确认吗？"
            r"如果暂时没有完整参数，先说城市、屏幕位置或已有规格也可以。?\s*$"
        )
    ]
    cleaned = reply
    for pattern in exact_patterns:
        cleaned = re.sub(pattern, "", cleaned).strip()
    if cleaned != reply.strip():
        return cleaned

    paragraphs = re.split(r"\n\s*\n", reply.strip())
    if not paragraphs:
        return reply.strip()
    last = paragraphs[-1]
    keywords = tuple(
        keyword
        for field in asked_fields
        for keyword in QUESTION_KEYWORDS_BY_FIELD.get(field, ())
    )
    if ("？" in last or "?" in last) and any(keyword in last for keyword in keywords):
        return "\n\n".join(paragraphs[:-1]).strip()
    return reply.strip()


def sanitize_brief_agent_reply(
    reply: str,
    agent_state: dict[str, Any] | None,
    memory_hints: dict[str, str] | None = None,
) -> str:
    """Observe redundant questions about confirmed fields without rewriting user-facing copy."""
    brief_state = (agent_state or {}).get("brief_state") or {}
    if not brief_state or not reply:
        return reply

    asked_fields = _asked_filled_fields(reply, brief_state)
    if asked_fields:
        question = _last_question_text(reply)
        logger.info(
            "brief_agent_sanitizer_observed_redundant_question "
            f"fields={','.join(sorted(asked_fields))} "
            f"reply_chars={len(str(reply))} "
            f"question_chars={len(question)}"
        )
    return reply
