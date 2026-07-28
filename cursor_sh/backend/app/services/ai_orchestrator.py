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
from app.utils.timezone import beijing_now

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
VALID_CONTROL_ACTIONS = {"none", "finish_brief_now", "handoff_requested"}
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
AGENT_DEFAULT_STAGES = {
    "brief_agent": "brief_building",
    "business_intro_agent": "business_intro",
    "creative_direction_agent": "creative_direction",
    "creative_diagnosis_agent": "creative_diagnosis",
    "budget_agent": "budget_diagnosis",
    "order_agent": "order_query",
    "general_agent": "idle",
}
ORDER_FLOW_AGENTS = {"brief_agent", "creative_direction_agent", "creative_diagnosis_agent", "budget_agent"}
ORDER_FLOW_SUPPORT_AGENTS = {"budget_agent"}
CREATIVE_DIRECTION_ITERATION_LIMIT = 5
CREATIVE_DIRECTION_ACTIVE_STATUSES = frozenset(
    {"awaiting_image", "awaiting_image_context", "awaiting_feedback", "exit_recommended"}
)
CREATIVE_DIAGNOSIS_ITERATION_LIMIT = 5
CREATIVE_DIAGNOSIS_ACTIVE_STATUSES = frozenset(
    {"awaiting_target", "awaiting_feedback", "exit_recommended"}
)


def creative_direction_iteration_count(agent_state: dict[str, Any] | None) -> int:
    pending = (agent_state or {}).get("pending_creative_direction")
    if not isinstance(pending, dict):
        return 0
    try:
        return max(0, int(pending.get("iteration_count") or 0))
    except (TypeError, ValueError):
        return 0


def creative_direction_iteration_preview(agent_state: dict[str, Any] | None) -> dict[str, Any]:
    next_iteration = creative_direction_iteration_count(agent_state) + 1
    return {
        "current_iteration": next_iteration - 1,
        "next_iteration": next_iteration,
        "iteration_limit": CREATIVE_DIRECTION_ITERATION_LIMIT,
        "exit_recommended": next_iteration >= CREATIVE_DIRECTION_ITERATION_LIMIT,
    }


def creative_direction_stage(status: str) -> str:
    if status == "exit_recommended":
        return "creative_direction_exit_recommended"
    if status == "awaiting_feedback":
        return "creative_direction_review"
    return "creative_direction"


def advance_creative_direction_iteration(
    agent_state: dict[str, Any] | None,
    *,
    prompt_message: str,
    reason: str,
) -> dict[str, Any]:
    """Advance the orchestrator-owned creative review counter after one completed output."""
    next_state = dict(agent_state or {})
    previous_pending = next_state.get("pending_creative_direction")
    previous_pending = previous_pending if isinstance(previous_pending, dict) else {}
    preview = creative_direction_iteration_preview(next_state)
    now = beijing_now().isoformat()
    exit_recommended = bool(preview["exit_recommended"])
    status = "exit_recommended" if exit_recommended else "awaiting_feedback"
    pending = {
        "status": status,
        "source": "creative_direction_agent",
        "reason": reason,
        "prompt_message": (prompt_message or "")[:240],
        "iteration_count": preview["next_iteration"],
        "iteration_limit": preview["iteration_limit"],
        "exit_recommended": exit_recommended,
        "updated_at": now,
    }
    if exit_recommended:
        pending["exit_recommended_at"] = previous_pending.get("exit_recommended_at") or now
    next_state["pending_creative_direction"] = pending
    next_state["pending_evaluation"] = None
    next_state["current_agent"] = "creative_direction_agent"
    next_state["stage"] = creative_direction_stage(status)
    next_state["updated_at"] = now
    return next_state


def creative_diagnosis_iteration_count(agent_state: dict[str, Any] | None) -> int:
    pending = (agent_state or {}).get("pending_evaluation")
    if not isinstance(pending, dict):
        return 0
    try:
        return max(0, int(pending.get("iteration_count") or 0))
    except (TypeError, ValueError):
        return 0


def creative_diagnosis_iteration_preview(agent_state: dict[str, Any] | None) -> dict[str, Any]:
    next_iteration = creative_diagnosis_iteration_count(agent_state) + 1
    return {
        "current_iteration": next_iteration - 1,
        "next_iteration": next_iteration,
        "iteration_limit": CREATIVE_DIAGNOSIS_ITERATION_LIMIT,
        "exit_recommended": next_iteration >= CREATIVE_DIAGNOSIS_ITERATION_LIMIT,
    }


def creative_diagnosis_stage(status: str) -> str:
    if status == "exit_recommended":
        return "creative_diagnosis_exit_recommended"
    if status == "awaiting_feedback":
        return "creative_diagnosis_review"
    return "creative_diagnosis"


def advance_creative_diagnosis_iteration(
    agent_state: dict[str, Any] | None,
    *,
    prompt_message: str,
    reason: str,
) -> dict[str, Any]:
    """Advance the evaluation discussion counter after one completed assessment."""
    next_state = dict(agent_state or {})
    previous_pending = next_state.get("pending_evaluation")
    previous_pending = previous_pending if isinstance(previous_pending, dict) else {}
    preview = creative_diagnosis_iteration_preview(next_state)
    now = beijing_now().isoformat()
    exit_recommended = bool(preview["exit_recommended"])
    status = "exit_recommended" if exit_recommended else "awaiting_feedback"
    pending = {
        "status": status,
        "source": "creative_diagnosis_agent",
        "reason": reason,
        "prompt_message": (prompt_message or "")[:240],
        "iteration_count": preview["next_iteration"],
        "iteration_limit": preview["iteration_limit"],
        "exit_recommended": exit_recommended,
        "updated_at": now,
    }
    if exit_recommended:
        pending["exit_recommended_at"] = previous_pending.get("exit_recommended_at") or now
    next_state["pending_evaluation"] = pending
    next_state["pending_creative_direction"] = None
    next_state["current_agent"] = "creative_diagnosis_agent"
    next_state["stage"] = creative_diagnosis_stage(status)
    next_state["updated_at"] = now
    return next_state


def _is_order_flow_agent(agent: str | None) -> bool:
    return normalize_agent(agent) in ORDER_FLOW_AGENTS


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


def _selected_agent(agent: str | None) -> str | None:
    return agent if agent in VALID_AGENTS else None


def _default_stage(agent: str) -> str:
    return AGENT_DEFAULT_STAGES.get(agent, "brief_building")


def _recent_history(history: list[dict[str, Any]], limit: int = 8) -> list[dict[str, str]]:
    valid_history: list[dict[str, str]] = []
    for item in history or []:
        role = item.get("role")
        content = str(item.get("content") or "").strip()
        if role not in {"user", "assistant"} or not content:
            continue
        valid_history.append({"role": role, "content": content})

    selected = valid_history[-(limit + 1):]
    for index in range(len(selected) - 1, -1, -1):
        if selected[index]["role"] == "assistant":
            del selected[index]
            break
    return selected[-limit:]


def _last_assistant_context(history: list[dict[str, Any]]) -> str:
    for item in reversed(history or []):
        if item.get("role") != "assistant":
            continue
        content = str(item.get("content") or "").strip()
        if not content:
            continue
        return content
    return ""


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

    return None


def build_router_messages(context: OrchestratorContext) -> list[dict[str, str]]:
    current_agent = _selected_agent(context.current_agent)
    recent_history = _recent_history(context.history)
    last_assistant_message = _last_assistant_context(context.history)
    payload = {
        "current_user_message": context.message,
        "immediate_context": {
            "last_assistant_message": last_assistant_message,
        },
        "state": {
            "current_agent": current_agent,
            "stage": context.stage,
            "business_type": context.business_type if context.business_type in VALID_BUSINESS_TYPES else None,
        },
        "recent_history": recent_history,
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
            "completion_flow": "Router 只识别用户是否明确要求结束追问并整理 Brief；普通 readiness 仅表示信息可用于当前专业判断，不代表可以提取表单或保存订单草稿。",
            "creative_direction": "创意方向生成后进入 awaiting_feedback 讨论阶段；Orchestrator 记录 iteration_count，第 5 轮起状态变为 exit_recommended 并软提醒退出。用户明确确认方向或要求返回 Brief 后才真正退出。",
            "creative_diagnosis": "创意评估生成后进入 awaiting_feedback 讨论阶段；系统记录 iteration_count，第 5 轮起状态变为 exit_recommended 并软提醒退出。用户仍可继续追问，是否离开由下一轮 Router 根据用户意图决定。",
            "supporting_intents": "预算判断、可行性建议和业务说明应服从用户当前任务；是否返回需求梳理由下一轮 Router 根据用户的新意图决定。",
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
            "如果 state.current_agent 为 null，表示这是首次路由、尚未进入任何子 Agent；必须从 available_agents 中选择最符合当前用户意图的具体 Agent，并返回 action=switch，不能因为主目标是整理 Brief 而默认选择 brief_agent。",
            "判断意图时必须优先看 input_flags.user_authored_text；[图片理解摘要]、文件名和系统追加的视觉线索只能作为上下文证据，不能单独构成业务介绍、创意生成或评估意图。",
            "如果用户只是补充当前问题的信息，action 必须为 stay。",
            "先结合 immediate_context.last_assistant_message 理解当前这一轮。current_user_message 是短回答或省略句时，优先视为对该消息中最后一个可回答任务的回应；recent_history 只用于补充更早上下文，不能覆盖这一邻接关系。",
            "如果用户明确要求先这样、直接整理、结束追问或提交需求，应路由到 brief_agent；当前不是 brief_agent 时使用 action=switch，并设置 control_action=finish_brief_now。",
            "判断 Brief 是否结束时必须结合 immediate_context.last_assistant_message 里的实际提问。只有上一条明确处于最终素材收尾、并说明没有更多素材即可整理时，用户回答“没有了/暂无/不上传”才等价于确认整理，并设置 control_action=finish_brief_now；回答其他字段时的相同短句不能触发整理。",
            "如果用户明确要求人工/真人/客服/销售/顾问介入，应 stay 到 current_agent，并设置 control_action=handoff_requested；不要切到不存在的人工 agent。",
            "不得仅因为 brief_state.readiness 为 provisional/formal 或 can_score=true 就触发 Brief 整理；这些字段只表示创意生成或评估的信息就绪度。",
            "如果 pending_creative_direction.status 为 awaiting_image 或 awaiting_image_context，说明创意方向子 agent 正在等待图片或图片描述；用户下一轮上传图片、参考图或补充图片描述时，应继续由 creative_direction_agent 补全上一轮创意方向任务。",
            "如果 pending_creative_direction.status 为 awaiting_feedback，说明上一条创意方向仍在讨论中。用户评价方向、指出不满意、增加/删除/替换元素或提出其他修改时，stay 在 creative_direction_agent，并保持 intent=creative_direction；但用户明确要求评估、判断可行性、分析风险或比较优劣时，应 switch 到 creative_diagnosis_agent，不能把“评估”当作普通创意反馈。",
            "如果 pending_creative_direction.status 为 exit_recommended，说明创意方向已完成至少 5 轮，系统已经建议用户退出；这是软提醒，不是强制退出。用户明确继续修改时仍 stay 在 creative_direction_agent；用户确认当前方向、同意返回或要求继续 Brief 时 switch 到 brief_agent。",
            "只有当用户明确认可当前创意方向、明确要求结束创意讨论并继续 Brief，或切换到其他明确业务意图时，才离开 awaiting_feedback/exit_recommended；仅确认方向并继续 Brief 时 action=switch、target_agent=brief_agent、stage=brief_building、control_action=none。",
            "如果用户这一轮只是上传现场实拍图、屏幕照片或参考素材，没有写明要生成/评估创意，且没有 pending_creative_direction，必须 stay 到 brief_agent；上传素材是 Brief 收集的一部分，不是 creative_direction 意图。",
            "只有出现明确新意图时才 switch。",
            "如果 current_agent 非空且无法判断新意图，必须 stay 在 current_agent。",
            "如果用户要求产出、发散、列举、探索或延展创意内容/创意方向，包括询问“基于图片可以从哪些方向展开”，应路由到 creative_direction_agent；即使图片尚未上传，也先进入该 Agent 由其记录等待图片状态。",
            "如果用户只是描述想做一个 3D 视频、要求先梳理项目需求或回答 Brief 问题，并没有要求产出创意内容，应路由或停留在 brief_agent。",
            "如果当前处于 order_agent，只有用户继续明确查询订单时才 stay/switch 到 order_agent；如果用户开始描述项目需求、上传参考图、要求创意方向、创意评估或预算判断，应根据新意图 switch 到 brief_agent、creative_direction_agent、creative_diagnosis_agent 或 budget_agent。",
            "business_intro_agent 只在 input_flags.user_authored_text 明确询问公司、业务、服务范围、案例或作品时使用；不要因为图片摘要中出现“业务/服务/平台能力”等词而切到 business_intro_agent。",
            "creative_direction_agent 生成草案不代表讨论完成；草案生成后保留在 creative_direction_agent 等待用户反馈，不能自动返回 Brief。",
            "如果用户要求优化、修改、改写、调整、升级刚才/上面/这个创意方案，尤其是在 creative_diagnosis_agent 完成评估后，应 switch 到 creative_direction_agent；这是基于评估结果继续产出优化稿，不是再次评估。",
            "如果当前处于 brief_agent 且用户明确要求评估创意、判断方案成立点/风险点/优化方向，应 switch 到 creative_diagnosis_agent。",
            "如果 pending_evaluation.status 为 awaiting_feedback，说明上一轮评估仍可继续讨论。用户继续追问评估依据、比较方向、改变条件、要求重新判断，或直接回答上一条 creative_diagnosis_agent 为完善评估而提出的问题时，应 stay 在 creative_diagnosis_agent；用户确认结论、明确继续需求梳理或仅补充普通项目需求时 switch 到 brief_agent。",
            "如果 pending_evaluation.status 为 exit_recommended，说明评估讨论已完成至少 5 轮，系统已经建议退出；这是软提醒，不是强制退出。用户明确继续评估时仍 stay 在 creative_diagnosis_agent；用户接受结论、同意返回或继续 Brief 时 switch 到 brief_agent。",
            "只有 current_user_message 明确要求修改、改写、优化、生成或产出评估后的方案时，才 switch 到 creative_direction_agent；仅回答 creative_diagnosis_agent 上一条追问、补充偏好或条件，不等于要求产出方案，应继续 stay 在 creative_diagnosis_agent。",
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
            "control_action": "none | finish_brief_now | handoff_requested",
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
    selected_agent = _selected_agent(context.current_agent)
    current_agent = selected_agent or DEFAULT_AGENT
    return RouteDecision(
        action="stay" if selected_agent else "switch",
        intent="unclear",
        target_agent=current_agent,
        stage=context.stage if selected_agent else _default_stage(current_agent),
        business_type=context.business_type if context.business_type in VALID_BUSINESS_TYPES else None,
        reason=f"fallback:{reason}",
        source="fallback",
    )


def _apply_policy(parsed: dict[str, Any], context: OrchestratorContext) -> RouteDecision:
    selected_agent = _selected_agent(context.current_agent)
    current_agent = selected_agent or DEFAULT_AGENT
    initial_routing = selected_agent is None
    action = parsed.get("action") if parsed.get("action") in VALID_ACTIONS else "stay"
    intent = parsed.get("intent") if parsed.get("intent") in VALID_INTENTS else "unclear"
    parsed_target = parsed.get("target_agent") if parsed.get("target_agent") in VALID_AGENTS else None
    target_agent = parsed_target or current_agent
    business_type = parsed.get("business_type") if parsed.get("business_type") in VALID_BUSINESS_TYPES else context.business_type
    stage = parsed.get("stage") or (_default_stage(target_agent) if initial_routing else context.stage)
    control_action = parsed.get("control_action") if parsed.get("control_action") in VALID_CONTROL_ACTIONS else "none"
    reason = str(parsed.get("reason") or "").strip()

    if target_agent in {"human_agent", "handoff_agent"}:
        return _fallback_route(context, "router_attempted_handoff")

    if not initial_routing and _is_order_flow_agent(current_agent) and target_agent in ORDER_FLOW_SUPPORT_AGENTS:
        return RouteDecision(
            "stay",
            intent,
            "brief_agent",
            "brief_building",
            business_type,
            reason=reason or "order_flow_support_stays_in_brief",
            control_action=control_action,
        )

    if initial_routing:
        if intent == "unclear" or parsed_target is None:
            return _fallback_route(context, "initial_route_unclear")
        return RouteDecision(
            "switch",
            intent,
            target_agent,
            stage,
            business_type,
            reason=reason or "initial_agent_selected",
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
