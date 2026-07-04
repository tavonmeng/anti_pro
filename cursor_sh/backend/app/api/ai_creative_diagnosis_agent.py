"""Creative diagnosis Agent for external media-side conversations."""

from __future__ import annotations

from copy import deepcopy
import json
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.services.ai_context import agent_context_messages, latest_user_context_message
from app.services.ai_client import post_chat_completion
from app.services.ai_brief_state import FIELD_LABELS, MEDIA_3D_BRIEF_FIELDS, load_agent_state, save_agent_state
from app.services.ai_image_understanding import (
    IMAGE_CONTEXT_MARKER,
    UploadedAttachment,
    append_image_context_to_message,
    build_image_feedback_reply_instruction,
    summarize_uploaded_images,
)
from app.utils.business_log import log_business_event
from app.utils.dependencies import AnyUser, get_current_user_for_public_deployment
from app.utils.log_setup import get_module_logger
from app.utils.timezone import beijing_now

creative_diagnosis_router = APIRouter()
logger = get_module_logger("ai")


class CreativeDiagnosisRequest(BaseModel):
    session_id: str
    message: str
    history: list = Field(default_factory=list)
    business_type: str = "ai_3d_custom"
    agent_state: dict[str, Any] | None = None
    attachments: list[UploadedAttachment] = Field(default_factory=list)


async def _request_with_image_context(request: CreativeDiagnosisRequest) -> CreativeDiagnosisRequest:
    image_context = await summarize_uploaded_images(
        message=request.message,
        attachments=request.attachments,
    )
    if not image_context:
        return request
    return request.model_copy(
        update={"message": append_image_context_to_message(request.message, image_context)}
    )


def _brief_state(request: CreativeDiagnosisRequest) -> dict[str, Any]:
    return ((request.agent_state or {}).get("brief_state") or {})


def _pending_evaluation(request: CreativeDiagnosisRequest) -> dict[str, Any] | None:
    pending = (request.agent_state or {}).get("pending_evaluation")
    return pending if isinstance(pending, dict) else None


def _brief_fields(request: CreativeDiagnosisRequest) -> dict[str, str]:
    fields = (_brief_state(request).get("fields") or {})
    values: dict[str, str] = {}
    for field in MEDIA_3D_BRIEF_FIELDS:
        raw = fields.get(field, {})
        value = raw.get("value") if isinstance(raw, dict) else raw
        text = str(value or "").strip()
        if text:
            values[field] = text
    return values


def _next_brief_question(request: CreativeDiagnosisRequest) -> str:
    values = _brief_fields(request)
    priority = [
        ("viewing_path", "为了把这个创意判断落到现场，想确认一下观众主要从哪个方向观看：正面、斜侧、仰视，还是有多条人流动线？"),
        ("media_specs", "为了判断裸眼3D空间关系和制作边界，屏幕分辨率、物理尺寸或转角结构目前有大概参数吗？"),
        ("content_review", "这类创意后续还要看审核边界，现场或客户侧有没有必须避免的内容、动作或表现尺度？"),
        ("online_time", "如果这个方向继续推进，预计上刊或交付时间大概是什么时候？"),
        ("resource_background", "这个点位的媒体资源背景可以再补一点吗，比如商圈属性、人流特征或媒体定位？"),
        ("audience_scene", "这次内容主要希望打动哪类人群，游客、年轻消费者、亲子客群，还是招商客户？"),
    ]
    for field, question in priority:
        if not values.get(field):
            return question
    return "如果方便的话，也可以发一张现场实拍图、屏幕照片或参考素材，我可以结合真实环境把这个判断再校准一轮。"


def _build_fallback_message(request: CreativeDiagnosisRequest) -> str:
    values = _brief_fields(request)
    readiness = (_brief_state(request).get("readiness") or {}).get("level", "insufficient")
    score_line = "阶段性评分：72/100（信息仍不完整，分数仅用于判断方向，不作为正式提案结论）"
    if readiness == "formal":
        score_line = "总分：82/100（可进入正式方案深化，但仍需结合现场素材复核执行细节）"
    elif readiness == "insufficient":
        score_line = "暂不建议给正式总分；当前只能做阶段性判断。"

    concept = values.get("theme_concept") or request.message
    return (
        "**阶段性创意评估**\n\n"
        f"- **评估对象**：{concept}\n"
        f"- **结论**：方向有裸眼3D表达潜力，但是否值得推进，取决于观看动线、屏幕结构和审核边界。\n"
        f"- **{score_line}**\n\n"
        "**成立点**\n"
        "- 具备明确的视觉记忆点，适合用“探出、靠近、互动”建立大屏停留感。\n"
        "- 如果点位人流稳定、观看距离足够，容易形成拍摄和社交传播动机。\n\n"
        "**风险点**\n"
        "- 目前现场观看角度和屏幕参数不足，空间透视可能出现只在少数角度成立的问题。\n"
        "- 如果审核边界不清，过强的冲出、坠落或惊吓动作可能影响落地。\n\n"
        "**优化方向**\n"
        "- 把“单一出屏奇观”升级成与点位、人群或商业目标有关的动作逻辑。\n"
        "- 优先确认最佳观看点，再决定主体大小、出屏幅度和镜头节奏。\n\n"
        f"{_next_brief_question(request)}"
    )


def _extract_json_object(raw: str) -> dict[str, Any]:
    raw = (raw or "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.S)
        if not match:
            raise
        return json.loads(match.group(0))


def _looks_like_evaluation_entry_request(message: str) -> bool:
    text = re.sub(r"\s+", "", message or "")
    if not text:
        return False
    has_evaluation_intent = re.search(r"评估|可行性|优化空间|帮我看|看看|判断|诊断", text)
    has_placeholder_object = re.search(r"创意方向|创意|方案|想法|概念", text)
    has_concrete_visual = re.search(r"大熊猫|熊猫|猫|动物|汽车|鲸鱼|人物|产品|探出|冲出|破屏|互动|屏幕|大屏|L型|转角", text, re.I)
    return bool(has_evaluation_intent and has_placeholder_object and not has_concrete_visual)


def _normalize_gate_status(parsed: dict[str, Any], request: CreativeDiagnosisRequest) -> str:
    raw = str(parsed.get("status") or "").strip()
    if raw in {"evaluable", "awaiting_evaluation_target", "not_evaluable_concept"}:
        return raw
    if bool(parsed.get("is_evaluable")):
        return "evaluable"
    if _looks_like_evaluation_entry_request(request.message):
        return "awaiting_evaluation_target"
    return "not_evaluable_concept"


def _confirmed_brief_payload(request: CreativeDiagnosisRequest) -> dict[str, str]:
    return {
        FIELD_LABELS.get(field, field): value
        for field, value in _brief_fields(request).items()
    }


def _current_message_for_prompt(request: CreativeDiagnosisRequest) -> str:
    current_message = latest_user_context_message(request.agent_state, request.message)
    if IMAGE_CONTEXT_MARKER in (request.message or "") and IMAGE_CONTEXT_MARKER not in current_message:
        return request.message
    return current_message


def build_creative_diagnosis_gate_messages(request: CreativeDiagnosisRequest) -> list[dict[str, str]]:
    recent_history = agent_context_messages(
        request.agent_state,
        fallback_history=request.history,
    )
    current_message = _current_message_for_prompt(request)
    if recent_history and recent_history[-1]["role"] == "user" and recent_history[-1]["content"] == current_message:
        recent_history = recent_history[:-1]
    payload = {
        "current_user_message": current_message,
        "recent_history": recent_history,
        "confirmed_brief": _confirmed_brief_payload(request),
        "pending_evaluation": _pending_evaluation(request),
        "decision_goal": "判断当前是否已经存在一个可以被专业评估的创意方向，而不是直接做评估。",
    }
    system_prompt = (
        "你是 Unique Vision AI 创意评估子 agent 的前置判断器。"
        "你只判断当前输入是否构成一个可评估的创意方向，不输出用户可见评估。\n\n"
        "你必须把结果归入三类之一："
        "evaluable 表示当前已经有可评估创意方向；"
        "awaiting_evaluation_target 表示用户只是在进入评估任务、询问能否评估或要求帮忙评估，但还没有给出具体创意对象；"
        "not_evaluable_concept 表示用户给了一些创意碎片，但仍不足以专业评估。\n"
        "可评估创意方向的最低标准：能识别出明确评估对象，并且至少包含核心主体/主题、关键画面或动作机制、"
        "媒介或场景关系中的两个要素。"
        "如果用户说“这个方案/上面的创意/刚才那版”这类指代，必须结合 recent_history 和 confirmed_brief 判断指代对象是否足够具体。"
        "如果只是要求“评估一下”但没有具体对象，必须返回 awaiting_evaluation_target。"
        "如果只有一个词、一个材质、一个情绪、一个品类，必须返回 not_evaluable_concept。\n\n"
        "严格返回 JSON object，不要 Markdown，不要解释。"
        "字段："
        "{"
        "\"is_evaluable\": boolean,"
        "\"status\": \"evaluable | awaiting_evaluation_target | not_evaluable_concept\","
        "\"evaluation_target\": \"可评估对象的简短归纳，无法判断时为空字符串\","
        "\"reason\": \"简短原因\","
        "\"missing_aspects\": [\"缺失的信息点，最多3项\"],"
        "\"followup_question\": \"面向用户的一句话追问\""
        "}"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]


def _build_insufficient_idea_message(gate: dict[str, Any], request: CreativeDiagnosisRequest) -> str:
    missing = gate.get("missing_aspects") if isinstance(gate.get("missing_aspects"), list) else []
    missing_text = "、".join(str(item).strip() for item in missing if str(item).strip()) or "创意主体、关键动作或画面机制"
    followup = str(gate.get("followup_question") or "").strip()
    if not followup:
        followup = "可以补充一下这个创意里想呈现的主体、动作，以及它和屏幕或现场的关系吗？"
    return (
        "我先不急着给分，暂时还不能做创意评估。现在的信息还不足以构成一个可以专业评估的创意方向，"
        f"主要还缺少：{missing_text}。\n\n"
        "只要补一句核心设定就可以，比如主体是谁、它在画面里做什么、和屏幕或现场有什么关系。"
        f"{followup}"
    )


def _build_awaiting_target_message(gate: dict[str, Any], request: CreativeDiagnosisRequest) -> str:
    return (
        "可以，我会从可行性、裸眼3D适配、传播价值和优化空间几个角度帮您看。\n\n"
        "您先把创意方向简单说一下就行，比如主体是谁、它有什么动作或情节、准备放在哪类屏幕或场景。"
    )


def _build_sparse_concept_message(gate: dict[str, Any], request: CreativeDiagnosisRequest) -> str:
    missing = gate.get("missing_aspects") if isinstance(gate.get("missing_aspects"), list) else []
    missing_text = "、".join(str(item).strip() for item in missing if str(item).strip()) or "关键画面、动作机制或屏幕/现场关系"
    followup = str(gate.get("followup_question") or "").strip()
    if not followup:
        followup = "可以再补一句：主体会做什么，以及它和屏幕或现场有什么关系吗？"
    return (
        "这个方向我可以先接住。为了评估得更准，还需要再补一个关键设定："
        f"{missing_text}。\n\n"
        f"{followup}"
    )


async def _judge_creative_diagnosis_target(request: CreativeDiagnosisRequest) -> dict[str, Any]:
    data = await post_chat_completion(
        {
            "model": settings.AI_MODEL_NAME,
            "messages": build_creative_diagnosis_gate_messages(request),
            "max_tokens": 260,
            "temperature": 0,
            "response_format": {"type": "json_object"},
        },
        timeout=min(float(settings.AI_HTTP_TIMEOUT or 30.0), 12.0),
    )
    raw = data["choices"][0]["message"]["content"]
    parsed = _extract_json_object(raw)
    status = _normalize_gate_status(parsed, request)
    return {
        "is_evaluable": status == "evaluable",
        "status": status,
        "evaluation_target": str(parsed.get("evaluation_target") or "").strip(),
        "reason": str(parsed.get("reason") or "").strip(),
        "missing_aspects": parsed.get("missing_aspects") if isinstance(parsed.get("missing_aspects"), list) else [],
        "followup_question": str(parsed.get("followup_question") or "").strip(),
    }


def build_creative_diagnosis_messages(
    request: CreativeDiagnosisRequest,
    gate: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    recent_history = agent_context_messages(
        request.agent_state,
        fallback_history=request.history,
    )
    current_message = _current_message_for_prompt(request)
    if recent_history and recent_history[-1]["role"] == "user" and recent_history[-1]["content"] == current_message:
        recent_history = recent_history[:-1]
    brief_values = _confirmed_brief_payload(request)
    readiness = _brief_state(request).get("readiness") or {}
    payload = {
        "current_user_message": current_message,
        "recent_history": recent_history,
        "confirmed_brief": brief_values,
        "creative_readiness": readiness,
        "pending_evaluation": _pending_evaluation(request),
        "evaluation_target": (gate or {}).get("evaluation_target") or "",
        "next_brief_question": _next_brief_question(request),
    }
    system_prompt = (
        "你是 Unique Vision AI 的创意提案总监，专注裸眼3D户外媒体内容定制。"
        "你的任务是先完成专业创意评估，而不是为了补齐 Brief 才评价创意。\n\n"
        "评估必须基于当前已确认 Brief；信息不足时可以做阶段性判断，但必须说明不确定性。"
        "如果 payload 中有 evaluation_target，必须围绕该对象评估，不要重新猜测评估对象。"
        "允许输出总分或阶段性评分，但不要用分数压过建设性意见。\n\n"
        "评估维度参考：战略匹配度、信息单点清晰度、前三秒钩子、裸眼3D必要性、媒介适配度、"
        "品牌/媒体关联度、情绪驱动力、社交传播力、故事节奏、执行可行性、商业转化价值。\n\n"
        "输出结构固定为：**阶段性创意评估**、**成立点**、**风险点**、**优化方向**。"
        "最后用一段自然口语承接到 next_brief_question，只问一个问题，不要使用英文 Brief 的返回标题、附件式表达或已记录式固定话术。"
        "不要输出【需求收集完成】；表单触发只由主 Brief 流程负责。"
    )
    image_feedback_instruction = build_image_feedback_reply_instruction(request.message)
    if image_feedback_instruction:
        system_prompt += image_feedback_instruction
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]


def _current_user_id(current_user: Any) -> str:
    user_id = getattr(current_user, "id", "") or ""
    return str(user_id).strip()


def _agent_state_for_response(request: CreativeDiagnosisRequest, current_user: Any = None) -> dict[str, Any]:
    if isinstance(request.agent_state, dict):
        state = deepcopy(request.agent_state)
    else:
        user_id = _current_user_id(current_user)
        state = load_agent_state(request.session_id, user_id, request.business_type) if user_id else {}
    state.setdefault("business_type", request.business_type)
    return state


def _save_response_agent_state(request: CreativeDiagnosisRequest, current_user: Any, state: dict[str, Any]) -> None:
    user_id = _current_user_id(current_user)
    if not user_id:
        return
    save_agent_state(request.session_id, user_id, state)


def _mark_pending_evaluation(
    request: CreativeDiagnosisRequest,
    current_user: Any,
    gate: dict[str, Any],
) -> dict[str, Any]:
    state = _agent_state_for_response(request, current_user)
    now = beijing_now().isoformat()
    state["pending_evaluation"] = {
        "status": "awaiting_target",
        "source": "creative_diagnosis_agent",
        "reason": str(gate.get("reason") or "").strip(),
        "missing_aspects": gate.get("missing_aspects") if isinstance(gate.get("missing_aspects"), list) else [],
        "prompt_message": (request.message or "")[:240],
        "updated_at": now,
    }
    state["current_agent"] = "creative_diagnosis_agent"
    state["stage"] = "creative_diagnosis"
    state["business_type"] = request.business_type
    state["updated_at"] = now
    _save_response_agent_state(request, current_user, state)
    return state


def _clear_pending_evaluation(request: CreativeDiagnosisRequest, current_user: Any) -> dict[str, Any]:
    state = _agent_state_for_response(request, current_user)
    state["pending_evaluation"] = None
    state["current_agent"] = "brief_agent"
    state["stage"] = "brief_building"
    state["business_type"] = request.business_type
    state["updated_at"] = beijing_now().isoformat()
    _save_response_agent_state(request, current_user, state)
    return state


@creative_diagnosis_router.post("/creative-diagnosis")
async def ai_creative_diagnosis(
    request: CreativeDiagnosisRequest,
    current_user: AnyUser = Depends(get_current_user_for_public_deployment),
):
    """Evaluate a creative direction, then return the conversation to Brief collection."""
    request = await _request_with_image_context(request)
    if not settings.AI_API_KEY:
        return {"message": _build_fallback_message(request), "return_to_brief": True}

    try:
        gate = await _judge_creative_diagnosis_target(request)
    except HTTPException:
        raise
    except Exception as exc:
        log_business_event(
            logger,
            "ai_creative_diagnosis_gate_failed",
            level="warning",
            session_id=request.session_id,
            business_type=request.business_type,
            error=str(exc),
        )
        gate = {
            "is_evaluable": False,
            "status": "awaiting_evaluation_target",
            "reason": "gate_failed",
            "missing_aspects": ["创意主体", "关键动作或互动机制"],
            "followup_question": "可以先补充一句这个创意大概想呈现什么画面吗？",
        }

    if not gate.get("is_evaluable"):
        next_state = _mark_pending_evaluation(request, current_user, gate)
        status = str(gate.get("status") or "").strip()
        if status == "awaiting_evaluation_target":
            return {
                "message": _build_awaiting_target_message(gate, request),
                "return_to_brief": False,
                "agent_state": next_state,
            }
        return {
            "message": _build_sparse_concept_message(gate, request),
            "return_to_brief": False,
            "agent_state": next_state,
        }

    try:
        data = await post_chat_completion(
            {
                "model": settings.AI_MODEL_NAME,
                "messages": build_creative_diagnosis_messages(request, gate=gate),
                "temperature": 0.3,
            },
            timeout=settings.AI_HTTP_TIMEOUT,
        )
        message = data["choices"][0]["message"]["content"].replace("【需求收集完成】", "").strip()
        next_state = _clear_pending_evaluation(request, current_user)
        return {"message": message, "return_to_brief": True, "agent_state": next_state}
    except HTTPException:
        raise
    except Exception as exc:
        log_business_event(
            logger,
            "ai_creative_diagnosis_failed",
            level="warning",
            session_id=request.session_id,
            business_type=request.business_type,
            error=str(exc),
        )
        return {"message": _build_fallback_message(request), "return_to_brief": True}
