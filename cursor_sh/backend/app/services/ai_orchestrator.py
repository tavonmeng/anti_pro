"""Lightweight orchestrator for external AI chat routing.

The orchestrator is a control-plane layer: it decides whether to keep the
current agent or switch to another one, but it never produces the user-facing
business answer itself.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any

from app.config import settings
from app.services.ai_client import post_chat_completion
from app.services.ai_upload_context import is_upload_only_material_message, strip_generated_upload_context
from app.services.platform_service_catalog import VALID_BUSINESS_TYPES
from app.utils.business_log import log_business_event
from app.utils.log_setup import get_module_logger

logger = get_module_logger("ai")


VALID_AGENTS = {
    "brief_agent",
    "business_intro_agent",
    "creative_direction_agent",
    "creative_diagnosis_agent",
    "budget_agent",
    "order_agent",
    "general_agent",
}
VALID_ACTIONS = {"stay", "switch", "clarify"}
VALID_CONTROL_ACTIONS = {"none", "finish_brief_now", "handoff_requested", "ready_to_extract"}
VALID_INTENTS = {
    "brief_building",
    "creative_direction",
    "creative_diagnosis",
    "budget_diagnosis",
    "business_intro",
    "order_query",
    "case_consultation",
    "general",
    "unclear",
}
DEFAULT_AGENT = "brief_agent"
ORDER_FLOW_AGENTS = {"brief_agent", "creative_direction_agent", "creative_diagnosis_agent", "budget_agent"}
ORDER_FLOW_SUPPORT_AGENTS = {"budget_agent"}


def _is_order_flow_agent(agent: str | None) -> bool:
    return normalize_agent(agent) in ORDER_FLOW_AGENTS


def _creative_diagnosis_intent(message: str) -> bool:
    text = re.sub(r"\s+", "", message or "")
    if not text:
        return False
    has_creative_subject = re.search(r"创意|方案|方向|想法|概念|裸眼3d|裸眼3D", text)
    has_diagnosis_action = re.search(r"评估|判断|诊断|打分|评分|成立|风险|适不适合|可不可行|值不值得|帮我看|看看", text)
    return bool(has_creative_subject and has_diagnosis_action)


def _creative_direction_intent(message: str) -> bool:
    text = re.sub(r"\s+", "", message or "")
    if not text:
        return False
    if _creative_diagnosis_intent(text):
        return False
    explicit_creative_object = r"创意方案|创意方向|方向草案|设计方案|策划方案|策划方向|视觉方案"
    return bool(
        re.search(rf"(生成|出|写|来|设计|策划).*?({explicit_creative_object})", text)
        or re.search(rf"(做一版|做一个|做个).*?({explicit_creative_object})", text)
        or re.search(rf"({explicit_creative_object}).*?(生成|出|写|来一版|做一版|设计|策划)", text)
        or re.search(rf"(给我|帮我|能不能|可以).*?(一版|一个|个)({explicit_creative_object})", text)
    )


def _order_flow_support_intent(message: str) -> str | None:
    text = re.sub(r"\s+", "", message or "")
    if not text:
        return None
    if re.search(r"预算|报价|费用|周期|工期|成本|投入", text):
        return "budget_diagnosis"
    return None


def _explicit_order_query_intent(message: str) -> bool:
    text = re.sub(r"\s+", "", message or "")
    if not text:
        return False
    direct_order_terms = r"订单|我的单|下过的|已下|已下单|下单后|需求单"
    query_terms = r"进度|状态|查询|查看|历史|详情|怎么样了|什么情况|到哪了"
    return bool(
        re.search(rf"({direct_order_terms}).*?({query_terms})", text)
        or re.search(rf"({query_terms}).*?({direct_order_terms})", text)
        or re.search(r"我的订单|订单进度|订单状态|订单详情|历史订单|查单", text)
    )


def _pending_creative_diagnosis_status(pending_evaluation: dict[str, Any] | None) -> str:
    if not isinstance(pending_evaluation, dict):
        return ""
    status = str(pending_evaluation.get("status") or "").strip()
    if status in {"awaiting_target", "awaiting_evaluation_target"}:
        return "awaiting_target"
    return status


def _explicit_business_intro_intent(message: str) -> bool:
    text = re.sub(r"\s+", "", message or "")
    return bool(text and re.search(r"了解|介绍|业务|服务|案例|作品|你们做什么|什么公司", text))


@dataclass(frozen=True)
class OrchestratorContext:
    session_id: str
    message: str
    history: list[dict[str, Any]]
    current_agent: str | None = None
    stage: str | None = None
    business_type: str | None = None
    brief_state: dict[str, Any] | None = None
    pending_evaluation: dict[str, Any] | None = None
    pending_creative_direction: dict[str, Any] | None = None
    memory_context: str = ""
    has_attachments: bool = False


@dataclass(frozen=True)
class RouteDecision:
    action: str
    intent: str
    target_agent: str
    stage: str | None = None
    business_type: str | None = None
    needs_clarification: bool = False
    clarification_question: str = ""
    reason: str = ""
    source: str = "llm_router"
    control_action: str = "none"

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "intent": self.intent,
            "target_agent": self.target_agent,
            "stage": self.stage,
            "business_type": self.business_type,
            "needs_clarification": self.needs_clarification,
            "clarification_question": self.clarification_question,
            "reason": self.reason,
            "source": self.source,
            "control_action": self.control_action,
        }


def normalize_agent(agent: str | None) -> str:
    if agent in VALID_AGENTS:
        return agent
    return DEFAULT_AGENT


def _recent_history(history: list[dict[str, Any]], limit: int = 8) -> list[dict[str, str]]:
    recent: list[dict[str, str]] = []
    for item in (history or [])[-limit:]:
        role = item.get("role")
        content = str(item.get("content") or "").strip()
        if role not in {"user", "assistant"} or not content:
            continue
        recent.append({"role": role, "content": content[:700]})
    return recent


def _brief_snapshot(history: list[dict[str, Any]], latest_message: str) -> dict[str, Any]:
    text = "\n".join(
        [str(h.get("content") or "") for h in (history or []) if h.get("role") in {"user", "assistant"}]
        + [latest_message or ""]
    )
    fields = {
        "brand_or_project": r"品牌|项目|客户|公司",
        "objective": r"宣传|招商|发布|传播|活动|引流|曝光",
        "screen_context": r"屏幕|大屏|裸眼|3d|3D|天幕|户外|商场|广场|点位|城市",
        "creative_direction": r"创意|风格|主题|元素|视觉|写实|科技|国潮|赛博|水墨",
        "budget": r"预算|报价|费用|\d+\s*万",
        "deadline": r"月底|月初|上线|交付|周期|\d{1,2}月|\d{4}年",
        "materials": r"素材|图片|照片|视频|文件|参考|上传",
    }
    confirmed = [name for name, pattern in fields.items() if re.search(pattern, text, re.I)]
    return {
        "confirmed_fields": confirmed,
        "missing_fields": [name for name in fields if name not in confirmed],
    }


def _rule_route(context: OrchestratorContext) -> RouteDecision | None:
    user_text = strip_generated_upload_context(context.message)
    text = re.sub(r"\s+", "", user_text)
    current_agent = normalize_agent(context.current_agent)

    if not text and not is_upload_only_material_message(context.message, has_attachments=context.has_attachments):
        return RouteDecision("stay", "unclear", current_agent, context.stage, context.business_type, reason="empty_message", source="rule")

    if _explicit_order_query_intent(text):
        return RouteDecision("switch", "order_query", "order_agent", "order_query", context.business_type, reason="explicit_order_query", source="rule")

    if _is_order_flow_agent(current_agent) and _pending_creative_diagnosis_status(context.pending_evaluation) == "awaiting_target":
        return RouteDecision(
            "switch",
            "creative_diagnosis",
            "creative_diagnosis_agent",
            "creative_diagnosis",
            context.business_type,
            reason="pending_creative_diagnosis_target",
            source="rule",
        )

    if _explicit_business_intro_intent(text) and current_agent != "business_intro_agent":
        return RouteDecision("switch", "business_intro", "business_intro_agent", "business_intro", context.business_type, reason="explicit_business_intro", source="rule")

    if _is_order_flow_agent(current_agent) and _creative_direction_intent(text):
        return RouteDecision(
            "switch",
            "creative_direction",
            "creative_direction_agent",
            "creative_direction",
            context.business_type,
            reason="explicit_creative_direction",
            source="rule",
        )

    if _is_order_flow_agent(current_agent) and _creative_diagnosis_intent(text):
        return RouteDecision(
            "switch",
            "creative_diagnosis",
            "creative_diagnosis_agent",
            "creative_diagnosis",
            context.business_type,
            reason="explicit_creative_diagnosis",
            source="rule",
        )

    support_intent = _order_flow_support_intent(text)
    if _is_order_flow_agent(current_agent) and support_intent:
        return RouteDecision(
            "stay",
            support_intent,
            "brief_agent",
            "brief_building",
            context.business_type,
            reason="order_flow_support_stays_in_brief",
            source="rule",
        )

    return None


def build_router_messages(context: OrchestratorContext) -> list[dict[str, str]]:
    current_agent = normalize_agent(context.current_agent)
    payload = {
        "current_user_message": context.message,
        "state": {
            "current_agent": current_agent,
            "stage": context.stage,
            "business_type": context.business_type if context.business_type in VALID_BUSINESS_TYPES else None,
        },
        "recent_history": _recent_history(context.history),
        "brief_snapshot": _brief_snapshot(context.history, context.message),
        "brief_state": context.brief_state or {},
        "pending_evaluation": context.pending_evaluation or None,
        "pending_creative_direction": context.pending_creative_direction or None,
        "input_flags": {
            "has_attachments": context.has_attachments,
            "upload_only_material": is_upload_only_material_message(
                context.message,
                has_attachments=context.has_attachments,
            ),
            "user_authored_text": strip_generated_upload_context(context.message),
        },
        "product_goal": {
            "primary": "外部端对话的主目标是把用户输入收拢为本次项目 Brief。",
            "completion_flow": "Brief 信息足够后，由后端 control_action=ready_to_extract 触发需求提取、评估、草稿保存、内嵌表单确认，最后由用户确认下单。",
            "creative_direction": "创意方向生成由 creative_direction_agent 独立完成轻量草案；生成完成后必须自然衔接回需求梳理主流程。",
            "creative_diagnosis": "创意评估由 creative_diagnosis_agent 独立完成专业判断；评估完成后必须自然衔接回需求梳理主流程。",
            "supporting_intents": "预算判断、可行性建议和业务说明不能让用户长期停留在独立咨询里，应最终衔接回需求梳理主流程。",
        },
        "available_agents": {
            "brief_agent": "整理项目需求和创意 Brief，继续追问缺失字段。",
            "business_intro_agent": "介绍公司业务、服务范围、案例规则和业务入口。",
            "creative_direction_agent": "生成轻量创意方向草案，或基于已有评估/反馈优化、改写、升级现有创意方向。",
            "creative_diagnosis_agent": "判断创意是否适合裸眼 3D、大屏和传播场景。",
            "budget_agent": "判断预算、周期、制作难度和资源投入区间。",
            "order_agent": "查询订单列表、状态、进度和订单详情。",
            "general_agent": "处理无法归类的闲聊或通用问题。",
        },
        "routing_policy": [
            "只判断路由，不生成用户可见业务回答。",
            "判断意图时必须优先看 input_flags.user_authored_text；[图片理解摘要]、文件名和系统追加的视觉线索只能作为上下文证据，不能单独构成业务介绍、创意生成或评估意图。",
            "如果用户只是补充当前问题的信息，action 必须为 stay。",
            "如果用户明确表示不想继续追问、先这样、直接整理、可以了或够了，应 stay 到 brief_agent，并设置 control_action=finish_brief_now。",
            "如果用户明确要求人工/真人/客服/销售/顾问介入，应 stay 到 current_agent，并设置 control_action=handoff_requested；不要切到不存在的人工 agent。",
            "如果只是 Brief 状态已经足够整理，但用户没有新的业务意图，应 stay 到 brief_agent，并设置 control_action=ready_to_extract。",
            "如果 pending_creative_direction.status 为 awaiting_image 或 awaiting_image_context，说明创意方向子 agent 正在等待图片或图片描述；用户下一轮上传图片、参考图或补充图片描述时，应优先 switch 到 creative_direction_agent，这是补全上一轮创意方向任务。",
            "如果用户这一轮只是上传现场实拍图、屏幕照片或参考素材，没有写明要生成/评估创意，且没有 pending_creative_direction，必须 stay 到 brief_agent；上传素材是 Brief 收集的一部分，不是 creative_direction 意图。",
            "只有出现明确新意图时才 switch。",
            "如果无法判断新意图，必须 stay 在 current_agent。",
            "如果当前处于 brief_agent 且用户明确要求生成/写/出一版创意方案、设计方案、策划方向，应 switch 到 creative_direction_agent。",
            "用户只是说想做一个 3D 视频、先梳理需求、聊大概方向、还没有具体 Brief 时，必须 stay 到 brief_agent。",
            "如果当前处于 order_agent，只有用户继续明确查询订单时才 stay/switch 到 order_agent；如果用户开始描述项目需求、上传参考图、要求创意方向、创意评估或预算判断，应根据新意图 switch 到 brief_agent、creative_direction_agent、creative_diagnosis_agent 或 budget_agent。",
            "business_intro_agent 只在 input_flags.user_authored_text 明确询问公司、业务、服务范围、案例或作品时使用；不要因为图片摘要中出现“业务/服务/平台能力”等词而切到 business_intro_agent。",
            "creative_direction_agent 完成草案后必须衔接回需求梳理主流程；后续用户补充信息时应 stay 到 brief_agent，后续用户要求修改草案时可再次 switch 到 creative_direction_agent。",
            "如果用户要求优化、修改、改写、调整、升级刚才/上面/这个创意方案，尤其是在 creative_diagnosis_agent 完成评估后，应 switch 到 creative_direction_agent；这是基于评估结果继续产出优化稿，不是再次评估。",
            "如果当前处于 brief_agent 且用户明确要求评估创意、判断方案成立点/风险点/优化方向，应 switch 到 creative_diagnosis_agent。",
            "creative_diagnosis_agent 完成评估后必须衔接回需求梳理主流程；后续用户补充信息时应 stay 到 brief_agent。",
            "不要把单独的“优化一下/帮我改一下/能不能再调整”当作 creative_diagnosis；必须结合 recent_history 判断它是否是在要求优化上一版创意。",
            "如果 pending_evaluation.status 为 awaiting_target，说明创意评估子 agent 正在等待用户补充评估对象；用户下一条补充应优先 switch 到 creative_diagnosis_agent。",
            "预算和一般可行性问题默认视为 Brief 主流程内的支持动作，必须 stay 到 brief_agent。",
            "不得主动建议或路由到人工；用户明确要求人工已由 hard guard 处理。",
            "target_agent 只能使用 available_agents 中的 key，或 stay 时使用 current_agent。",
        ],
        "output_schema": {
            "action": "stay | switch | clarify",
            "intent": "brief_building | creative_direction | creative_diagnosis | budget_diagnosis | business_intro | order_query | case_consultation | general | unclear",
            "target_agent": "brief_agent | business_intro_agent | creative_direction_agent | creative_diagnosis_agent | budget_agent | order_agent | general_agent",
            "stage": "string or null",
            "business_type": "ai_3d_custom | video_purchase | digital_art | motion_content | media_post_production | campaign_analytics | null",
            "control_action": "none | finish_brief_now | handoff_requested | ready_to_extract",
            "needs_clarification": "boolean",
            "clarification_question": "string",
            "reason": "short Chinese reason",
        },
    }
    system_prompt = (
        "你是 Unique Vision AI 外部用户端的 LLM Router。"
        "你只负责选择后端 Agent，不负责回答用户。"
        "严格返回一个 JSON object，不要 Markdown，不要解释。"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]


def _extract_json_object(raw: str) -> dict[str, Any]:
    raw = (raw or "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.S)
        if not match:
            raise
        return json.loads(match.group(0))


def _fallback_route(context: OrchestratorContext, reason: str) -> RouteDecision:
    current_agent = normalize_agent(context.current_agent)
    return RouteDecision(
        action="stay",
        intent="unclear",
        target_agent=current_agent,
        stage=context.stage,
        business_type=context.business_type if context.business_type in VALID_BUSINESS_TYPES else None,
        reason=f"fallback:{reason}",
        source="fallback",
    )


def _apply_policy(parsed: dict[str, Any], context: OrchestratorContext) -> RouteDecision:
    current_agent = normalize_agent(context.current_agent)
    action = parsed.get("action") if parsed.get("action") in VALID_ACTIONS else "stay"
    intent = parsed.get("intent") if parsed.get("intent") in VALID_INTENTS else "unclear"
    target_agent = parsed.get("target_agent") if parsed.get("target_agent") in VALID_AGENTS else current_agent
    business_type = parsed.get("business_type") if parsed.get("business_type") in VALID_BUSINESS_TYPES else context.business_type
    stage = parsed.get("stage") or context.stage
    control_action = parsed.get("control_action") if parsed.get("control_action") in VALID_CONTROL_ACTIONS else "none"
    reason = str(parsed.get("reason") or "").strip()

    if target_agent in {"human_agent", "handoff_agent"}:
        return _fallback_route(context, "router_attempted_handoff")

    if _is_order_flow_agent(current_agent) and target_agent in ORDER_FLOW_SUPPORT_AGENTS:
        return RouteDecision(
            "stay",
            intent,
            "brief_agent",
            "brief_building",
            business_type,
            reason=reason or "order_flow_support_stays_in_brief",
            control_action=control_action,
        )

    if intent == "unclear":
        return RouteDecision("stay", intent, current_agent, context.stage, business_type, reason=reason or "unclear_stays_current", control_action=control_action)

    if action == "clarify" and context.current_agent:
        return RouteDecision("stay", intent, current_agent, context.stage, business_type, reason=reason or "clarify_with_current_context", control_action=control_action)

    if action == "switch":
        return RouteDecision("switch", intent, target_agent, stage, business_type, reason=reason, control_action=control_action)

    if action == "clarify":
        return RouteDecision(
            "clarify",
            intent,
            current_agent,
            stage,
            business_type,
            needs_clarification=True,
            clarification_question=str(parsed.get("clarification_question") or "").strip(),
            reason=reason,
            control_action=control_action,
        )

    return RouteDecision("stay", intent, current_agent, stage, business_type, reason=reason, control_action=control_action)


async def decide_route(context: OrchestratorContext) -> RouteDecision:
    rule_decision = _rule_route(context)
    if rule_decision:
        return rule_decision

    if not settings.AI_API_KEY:
        return _fallback_route(context, "ai_key_missing")

    try:
        data = await post_chat_completion(
            {
                "model": settings.AI_MODEL_NAME,
                "messages": build_router_messages(context),
                "max_tokens": 220,
                "temperature": 0,
                "response_format": {"type": "json_object"},
            },
            timeout=8.0,
        )
        raw = data["choices"][0]["message"]["content"]
        return _apply_policy(_extract_json_object(raw), context)
    except Exception as exc:
        log_business_event(
            logger,
            "ai_orchestrator_failed",
            level="warning",
            session_id=context.session_id,
            current_agent=context.current_agent,
            stage=context.stage,
            business_type=context.business_type,
            error=str(exc),
        )
        return _fallback_route(context, "router_error")
