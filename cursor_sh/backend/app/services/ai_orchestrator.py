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
    has_diagnosis_action = re.search(r"评估|判断|诊断|打分|评分|成立|风险|优化|适不适合|可不可行|值不值得|帮我看|看看", text)
    return bool(has_creative_subject and has_diagnosis_action)


def _creative_direction_intent(message: str) -> bool:
    text = re.sub(r"\s+", "", message or "")
    if not text:
        return False
    if _creative_diagnosis_intent(text):
        return False
    has_creative_subject = re.search(r"创意|方案|方向|策划|设计|视觉|内容", text)
    has_generation_action = re.search(r"生成|写|出|做|给|来|设计|策划|想看|需要|要一版|来一版", text)
    return bool(has_creative_subject and has_generation_action)


def _order_flow_support_intent(message: str) -> str | None:
    text = re.sub(r"\s+", "", message or "")
    if not text:
        return None
    if re.search(r"预算|报价|费用|周期|工期|成本|投入", text):
        return "budget_diagnosis"
    return None


@dataclass(frozen=True)
class OrchestratorContext:
    session_id: str
    message: str
    history: list[dict[str, Any]]
    current_agent: str | None = None
    stage: str | None = None
    business_type: str | None = None
    brief_state: dict[str, Any] | None = None
    memory_context: str = ""


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


def _switch_signal(message: str) -> bool:
    text = re.sub(r"\s+", "", message or "")
    if not text:
        return False
    return bool(
        re.search(r"订单|进度|状态|查询|查看|我的单|下过的", text)
        or re.search(r"了解|介绍|业务|服务|案例|作品|你们做什么|什么公司", text)
        or re.search(r"预算|报价|费用|周期|怎么做|适不适合|可不可行", text)
    )


def _rule_route(context: OrchestratorContext) -> RouteDecision | None:
    text = re.sub(r"\s+", "", context.message or "")
    current_agent = normalize_agent(context.current_agent)

    if not text:
        return RouteDecision("stay", "unclear", current_agent, context.stage, context.business_type, reason="empty_message", source="rule")

    if re.search(r"订单|进度|状态|查询|查看|我的单|下过的|已下", text):
        return RouteDecision("switch", "order_query", "order_agent", "order_query", context.business_type, reason="explicit_order_query", source="rule")

    if re.search(r"了解|介绍|业务|服务|案例|作品|你们做什么|什么公司", text) and current_agent != "business_intro_agent":
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

    if context.current_agent and not _switch_signal(text):
        return RouteDecision("stay", "unclear", current_agent, context.stage, context.business_type, reason="contextual_continuation", source="rule")

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
        "product_goal": {
            "primary": "外部端对话的主目标是把用户输入收拢为本次项目 Brief。",
            "completion_flow": "Brief 信息足够后，brief_agent 输出【需求收集完成】，前端继续执行需求提取、评估、草稿保存、内嵌表单确认，最后由用户确认下单。",
            "creative_direction": "创意方向生成由 creative_direction_agent 独立完成轻量草案；生成完成后必须自然衔接回需求梳理主流程。",
            "creative_diagnosis": "创意评估由 creative_diagnosis_agent 独立完成专业判断；评估完成后必须自然衔接回需求梳理主流程。",
            "supporting_intents": "预算判断、可行性建议和业务说明不能让用户长期停留在独立咨询里，应最终衔接回需求梳理主流程。",
        },
        "available_agents": {
            "brief_agent": "整理项目需求和创意 Brief，继续追问缺失字段。",
            "business_intro_agent": "介绍公司业务、服务范围、案例规则和业务入口。",
            "creative_direction_agent": "生成轻量创意方向草案，帮助用户讨论方向。",
            "creative_diagnosis_agent": "判断创意是否适合裸眼 3D、大屏和传播场景。",
            "budget_agent": "判断预算、周期、制作难度和资源投入区间。",
            "order_agent": "查询订单列表、状态、进度和订单详情。",
            "general_agent": "处理无法归类的闲聊或通用问题。",
        },
        "routing_policy": [
            "只判断路由，不生成用户可见业务回答。",
            "如果用户只是补充当前问题的信息，action 必须为 stay。",
            "只有出现明确新意图时才 switch。",
            "如果无法判断新意图，必须 stay 在 current_agent。",
            "如果当前处于 brief_agent 且用户明确要求生成/写/出一版创意方案、设计方案、策划方向，应 switch 到 creative_direction_agent。",
            "creative_direction_agent 完成草案后必须衔接回需求梳理主流程；后续用户补充信息时应 stay 到 brief_agent，后续用户要求修改草案时可再次 switch 到 creative_direction_agent。",
            "如果当前处于 brief_agent 且用户明确要求评估创意、判断方案成立点/风险点/优化方向，应 switch 到 creative_diagnosis_agent。",
            "creative_diagnosis_agent 完成评估后必须衔接回需求梳理主流程；后续用户补充信息时应 stay 到 brief_agent。",
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
        )

    if intent == "unclear":
        return RouteDecision("stay", intent, current_agent, context.stage, business_type, reason=reason or "unclear_stays_current")

    if action == "clarify" and context.current_agent:
        return RouteDecision("stay", intent, current_agent, context.stage, business_type, reason=reason or "clarify_with_current_context")

    if action == "switch":
        return RouteDecision("switch", intent, target_agent, stage, business_type, reason=reason)

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
        )

    return RouteDecision("stay", intent, current_agent, stage, business_type, reason=reason)


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
