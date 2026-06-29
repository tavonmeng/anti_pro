"""State-driven Brief agent helpers for media-side requirement collection."""

from __future__ import annotations

import re
from typing import Any

from app.services.ai_brief_state import FIELD_LABELS
from app.services.memory_sanitizer import sanitize_reusable_memory_text


NEXT_QUESTION_PRIORITY = [
    (
        "theme_concept",
        "我先把当前信息记下。为了继续收拢 Brief，想确认一下这次内容主题或核心表达希望围绕什么展开？",
    ),
    (
        "city_location",
        "这个方向我先记下。为了判断画面尺度和现场观看关系，想确认一下这条内容大概会投放在哪个城市或哪块屏幕？",
    ),
    (
        "viewing_path",
        "这些核心信息我先记下。为了判断裸眼3D的空间关系，想确认一下观众主要会从哪个方向观看，比如正面、斜侧、仰视，还是有多条人流动线？",
    ),
    (
        "audience_scene",
        "我先按这个方向记录。为了判断内容的吸引点和节奏，想确认一下现场主要面向哪类人群或观看场景？",
    ),
    (
        "art_direction",
        "项目方向我先记下。为了后续策划更准确，想确认一下整体视觉气质更偏写实、治愈、科技，还是有其他风格偏好？",
    ),
    (
        "resource_background",
        "我先继续整理。为了判断内容目标，想了解一下这个点位或项目的背景，是开业造势、节日活动、招商展示，还是常规内容焕新？",
    ),
    (
        "media_specs",
        "前面的项目背景和创意方向我先记下。为了后续判断裸眼3D透视和出屏幅度，再确认一下屏幕有没有明确分辨率或物理尺寸？如果暂时没有，先说已有参数也可以。",
    ),
    (
        "online_time",
        "这些信息已经够形成初步方向。为了判断制作节奏，预计上刊、活动或交付时间大概是什么时候？",
    ),
    (
        "content_review",
        "我先记录当前方向。为了避免后续返工，想确认一下这次有没有审核规范、禁忌元素，或必须避免的表现尺度？",
    ),
    (
        "special_requirements",
        "主要信息我先记录。除了当前这些要求外，还有没有必须保留、必须避免，或需要特别配合的事项？",
    ),
    (
        "site_photos",
        "需求方向基本清楚了。您这边是否还有现场实拍图、屏幕照片或其他参考素材可以补充？如果暂时没有，也可以直接说明没有。",
    ),
]


QUESTION_KEYWORDS_BY_FIELD = {
    "city_location": ("投放点位", "屏幕位置", "城市、屏幕位置", "哪块屏", "哪个城市", "点位"),
    "media_specs": ("屏幕规格", "已有规格", "分辨率", "物理尺寸", "屏幕尺寸", "4k", "8k", "2k"),
    "theme_concept": ("内容或主题", "内容主题", "核心表达", "主要想做什么"),
    "viewing_path": ("观看动线", "观看方向", "哪个方向观看", "正面", "斜侧", "仰视"),
    "audience_scene": ("哪类人群", "观看场景", "目标受众", "面向"),
    "art_direction": ("风格偏好", "视觉气质", "艺术方向"),
    "online_time": ("预计上刊", "交付时间", "活动时间"),
    "content_review": ("审核规范", "禁忌", "避免", "表现尺度"),
    "site_photos": ("现场实拍图", "屏幕照片", "参考素材", "上传"),
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


def build_brief_memory_hints(memory: Any) -> dict[str, str]:
    """Extract non-confirmed Brief candidates from user memory."""
    if not memory:
        return {}

    hints: dict[str, str] = {}
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
            if city_location and "city_location" not in hints:
                hints["city_location"] = city_location
            if media_specs and "media_specs" not in hints:
                hints["media_specs"] = media_specs
            if viewing_path and "viewing_path" not in hints:
                hints["viewing_path"] = viewing_path
            if audience_scene and "audience_scene" not in hints:
                hints["audience_scene"] = audience_scene
            if "city_location" in hints:
                break

    preferences = _memory_value(memory, "project_preferences") or {}
    if isinstance(preferences, dict):
        common_cities = preferences.get("common_cities") or []
        if isinstance(common_cities, str):
            common_cities = [common_cities]
        common_city_text = "、".join(_compact_hint(city, 24) for city in common_cities[:3] if _compact_hint(city))
        if common_city_text and "city_location" not in hints:
            hints["city_location"] = common_city_text

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
            f"点位方向我先记录。我们了解到这块屏幕可能有这些参数：「{hint_text}」，"
            "这次是否按这个规格适配？如果有更新参数，也可以直接告诉我。"
        )
    return (
        f"我先记下当前方向。我们了解到有一个可参考的信息是「{hint_text}」，"
        "这次是否按这个来推进？如果不是，也可以直接告诉我新的信息。"
    )


def select_next_brief_question(
    brief_state: dict[str, Any] | None,
    filled_overrides: set[str] | None = None,
    memory_hints: dict[str, str] | None = None,
) -> dict[str, str] | None:
    """Choose the next Brief question strictly from missing state fields."""
    pending = _pending_confirmation(brief_state)
    if pending:
        field = str(pending.get("field") or "")
        return {
            "field": field,
            "label": str(pending.get("label") or FIELD_LABELS.get(field, field)),
            "question": _pending_confirmation_question(pending),
        }

    filled = _filled_fields(brief_state) | set(filled_overrides or set())
    for field, question in NEXT_QUESTION_PRIORITY:
        if field not in filled:
            return {
                "field": field,
                "label": FIELD_LABELS.get(field, field),
                "question": question,
            }
    return None


def build_brief_agent_instruction(
    agent_state: dict[str, Any] | None,
    memory_hints: dict[str, str] | None = None,
) -> str:
    brief_state = (agent_state or {}).get("brief_state") or {}
    next_question = select_next_brief_question(brief_state)
    filled = sorted(_filled_fields(brief_state))
    filled_labels = [FIELD_LABELS.get(field, field) for field in filled]
    pending = _pending_confirmation(brief_state)
    pending_block = ""
    if pending:
        pending_block = (
            "- 当前存在一个待用户确认的 Brief 候选。只能围绕该候选确认，不要把它当成已确认事实，也不要重复问开放式城市/规格问题。\n"
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
        + pending_block
        + f"- 当前只允许围绕「{next_question['label']}」追问一个自然问题。\n"
        + f"- 建议下一问：{next_question['question']}\n"
        + "- 禁止追问已填字段；如果点位、屏幕位置或规格已在状态中存在，不要再问投放点位或屏幕规格。\n"
    )


def _asked_filled_fields(reply: str, brief_state: dict[str, Any]) -> set[str]:
    tail = (reply or "")[-260:].lower()
    if "？" not in tail and "?" not in tail:
        return set()
    filled = _filled_fields(brief_state)
    asked: set[str] = set()
    for field, keywords in QUESTION_KEYWORDS_BY_FIELD.items():
        if field not in filled:
            continue
        if any(keyword.lower() in tail for keyword in keywords):
            asked.add(field)
    return asked


def _asked_pending_fields(reply: str, brief_state: dict[str, Any]) -> set[str]:
    tail = (reply or "")[-260:].lower()
    if "？" not in tail and "?" not in tail:
        return set()
    pending = _pending_confirmation(brief_state)
    if not pending:
        return set()
    field = str(pending.get("field") or "")
    keywords = QUESTION_KEYWORDS_BY_FIELD.get(field, ())
    if any(keyword.lower() in tail for keyword in keywords):
        return {field}
    return set()


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
    """Replace redundant questions about filled fields with the state-driven next question."""
    brief_state = (agent_state or {}).get("brief_state") or {}
    if not brief_state or not reply:
        return reply

    asked_fields = _asked_filled_fields(reply, brief_state) | _asked_pending_fields(reply, brief_state)
    if not asked_fields:
        return reply

    cleaned = _remove_redundant_trailing_question(reply, asked_fields)
    next_question = select_next_brief_question(brief_state)
    if not next_question:
        return cleaned
    if next_question["question"] in cleaned:
        return cleaned
    return (cleaned.rstrip() + "\n\n" + next_question["question"]).strip()
