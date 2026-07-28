"""LLM-selected answer affordances for the chat composer."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.services.ai_client import post_chat_completion
from app.utils.log_setup import get_module_logger

logger = get_module_logger("ai")

INTERACTION_TYPES = {"text", "single_choice", "multiple_choice", "number", "date"}
CHOICE_TYPES = {"single_choice", "multiple_choice"}


def _question_id(field: str | None, reply: str) -> str:
    digest = hashlib.sha1(f"{field or ''}:{reply}".encode("utf-8")).hexdigest()[:12]
    return f"question:{digest}"


def normalize_interaction(raw: Any, *, reply: str = "") -> dict[str, Any] | None:
    """Keep the UI contract small and discard malformed model output."""
    if not isinstance(raw, dict):
        return None

    interaction_type = str(raw.get("type") or "text").strip()
    if interaction_type in {"none", "null", ""}:
        return None
    if interaction_type not in INTERACTION_TYPES:
        return None

    field = str(raw.get("field") or "").strip() or None
    # The model identifies the semantic field; the UI affordance for a known
    # calendar field is deterministic. This prevents a valid online-time
    # question from silently falling back to the ordinary text composer.
    if field == "online_time" and interaction_type == "text":
        interaction_type = "date"
    result: dict[str, Any] = {
        "type": interaction_type,
        "question_id": str(raw.get("question_id") or _question_id(field, reply)),
    }
    if field:
        result["field"] = field

    placeholder = str(raw.get("placeholder") or "").strip()
    if placeholder:
        result["placeholder"] = placeholder[:160]
    elif interaction_type == "date" and field == "online_time":
        result["placeholder"] = "选择预计上刊日期"

    if interaction_type in CHOICE_TYPES:
        eligibility = raw.get("choice_eligibility")
        required_checks = (
            "answer_space_closed",
            "options_exhaustive",
            "selection_fully_answers",
            "options_grounded",
            "materially_better_than_text",
        )
        if not isinstance(eligibility, dict) or any(eligibility.get(check) is not True for check in required_checks):
            return None
        options: list[dict[str, str]] = []
        seen: set[str] = set()
        for index, option in enumerate(raw.get("options") or []):
            if not isinstance(option, dict):
                continue
            label = str(option.get("label") or option.get("value") or "").strip()
            value = str(option.get("value") or label).strip()
            if not label or not value or value in seen:
                continue
            seen.add(value)
            item = {"id": str(option.get("id") or f"option-{index + 1}"), "label": label[:120], "value": value[:240]}
            group = str(option.get("group") or "").strip()
            if group:
                item["group"] = group[:80]
            options.append(item)
        if not 2 <= len(options) <= 5:
            return None
        result["options"] = options
        # Product requirement: every choice interaction keeps a free-form escape hatch.
        result["allow_other"] = True

    return result


def _interaction_messages(reply: str, history: list[dict[str, Any]], brief_state: dict[str, Any] | None) -> list[dict[str, str]]:
    system = (
        "你负责决定聊天输入区的回答方式，只返回严格 JSON，不回答用户。\n"
        "默认使用 text。首先判断 assistant_reply 是否只包含一个需要用户回答的任务。不要只按问号数量判断；"
        "即使只有一个问号，同时要求用户补充两个不同维度的信息也属于多个回答任务。"
        "如果包含多个回答任务，返回 text。\n"
        "只有答案集合确实有限时，才使用 single_choice 或 multiple_choice，并且必须同时满足："
        "选项为 2 至 5 个；所有选项属于同一个回答维度；单选项之间互斥，多选时必须明确允许同时选择；"
        "用户只选择选项就能完整回答当前问题，不需要继续解释；选项只能来自当前上下文、已提供的业务枚举或已有候选信息。"
        "这里的‘答案集合有限’是指问题本身的真实答案空间已经封闭，不能因为 assistant_reply 临时写成‘A 还是 B’、"
        "列出几个示例或使用‘如/例如/比如’，就把开放问题判断成有限集合。"
        "以上条件只是选择题的必要条件，不是满足后就必须生成选择题；还要判断一键选择是否明显优于自然输入。"
        "普通确认、探索性追问或连续使用选择题会让对话像填表时，继续返回 text。"
        "生成选择题前必须在 choice_eligibility 中逐项自检：answer_space_closed 表示真实答案空间已经封闭；"
        "options_exhaustive 表示 2 至 5 个选项足以覆盖正常答案，不能依赖‘其他’来弥补不完整候选；"
        "selection_fully_answers 表示只点选即可完整回答；options_grounded 表示选项有上下文、业务枚举或已有候选依据；"
        "materially_better_than_text 表示选择控件明显比自然输入更有帮助。五项必须全部为 true，否则 type 返回 text。"
        "例如项目背景、创意风格、内容方向等问题，即使 assistant_reply 写成两个方向，通常仍存在大量正常答案，options_exhaustive 应为 false。"
        "校准示例：‘是否符合预期/是否准确’属于普通确认，通常 materially_better_than_text 为 false；"
        "‘品牌营销节点还是城市地标焕新’没有覆盖其他项目背景，options_exhaustive 为 false；"
        "‘超写实还是卡通’没有覆盖其他视觉风格，options_exhaustive 为 false。"
        "相反，当前上下文已经锁定两个明确执行路径、用户确实只需二选一即可继续时，才可以把相关自检项判断为 true。"
        "如果不能确定答案集合是否有限，返回 text。\n"
        "interaction.type 只能是 none、text、single_choice、multiple_choice、number、date。"
        "当唯一回答任务是确认预计上刊、上线、投放、活动或交付日期时，field 返回 online_time，type 返回 date；"
        "不要因为问题使用了‘大概什么时候’这种自然措辞而退回 text。"
        "none 表示当前回复不需要输入控件。选择题 options 必须是当前问题真正相关的有限候选，不要输出 HTML。\n"
        "输出格式：{\"type\":\"...\",\"field\":\"...\",\"choice_eligibility\":{\"answer_space_closed\":true,\"options_exhaustive\":true,\"selection_fully_answers\":true,\"options_grounded\":true,\"materially_better_than_text\":true},\"options\":[{\"label\":\"...\",\"value\":\"...\"}],\"placeholder\":\"...\"}。"
    )
    payload = {
        "assistant_reply": reply,
        "recent_history": [
            {"role": item.get("role"), "content": str(item.get("content") or "")[:500]}
            for item in (history or [])[-6:]
            if item.get("role") in {"user", "assistant"} and item.get("content")
        ],
        "brief_state": brief_state or {},
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]


async def decide_interaction(
    *,
    reply: str,
    history: list[dict[str, Any]],
    brief_state: dict[str, Any] | None,
    model: str,
    timeout: float,
) -> dict[str, Any] | None:
    if not reply.strip():
        return None
    try:
        data = await post_chat_completion(
            {
                "model": model,
                "messages": _interaction_messages(reply, history, brief_state),
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "enable_thinking": False,
            },
            timeout=min(timeout, 8.0),
        )
        content = data.get("choices", [{}])[0].get("message", {}).get("content") or "{}"
        interaction = normalize_interaction(json.loads(content), reply=reply)
        logger.info(
            "ai_interaction_decided type={} field={} option_count={} question_id={}",
            (interaction or {}).get("type") or "none",
            (interaction or {}).get("field") or "",
            len((interaction or {}).get("options") or []),
            (interaction or {}).get("question_id") or "",
        )
        return interaction
    except Exception as exc:
        logger.warning("ai_interaction_decision_failed: %s", exc)
        return None
