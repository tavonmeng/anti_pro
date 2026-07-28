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
from app.services.ai_brief_state import (
    FIELD_LABELS,
    MEDIA_3D_BRIEF_FIELDS,
    load_agent_state,
    save_agent_state,
    update_agent_state_from_message,
)
from app.services.ai_image_understanding import (
    IMAGE_CONTEXT_MARKER,
    UploadedAttachment,
    build_image_feedback_reply_instruction,
)
from app.services.ai_material_understanding import enrich_message_with_uploaded_materials
from app.services.ai_orchestrator import (
    CREATIVE_DIAGNOSIS_ITERATION_LIMIT,
    advance_creative_diagnosis_iteration,
    creative_diagnosis_iteration_count,
    creative_diagnosis_iteration_preview,
)
from app.services.ai_upload_context import BRIEF_DOCUMENT_CONTEXT_MARKER
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
    user_message_id: str | None = None
    agent_state: dict[str, Any] | None = None
    attachments: list[UploadedAttachment] = Field(default_factory=list)


async def _request_with_material_context(
    request: CreativeDiagnosisRequest,
    current_user: Any,
) -> CreativeDiagnosisRequest:
    material = await enrich_message_with_uploaded_materials(
        message=request.message,
        attachments=request.attachments,
        user_id=str(getattr(current_user, "id", "") or "").strip(),
    )
    if material.message == request.message:
        return request
    return request.model_copy(update={"message": material.message})


async def _request_with_updated_agent_state(
    request: CreativeDiagnosisRequest,
    current_user: Any,
) -> CreativeDiagnosisRequest:
    user_id = str(getattr(current_user, "id", "") or "").strip()
    if not user_id:
        return request
    updated_state = await update_agent_state_from_message(
        session_id=request.session_id,
        user_id=user_id,
        business_type=request.business_type,
        message=request.message,
        history=request.history,
        source_message_id=request.user_message_id,
        memory_hints={},
        update_brief=False,
    )
    return request.model_copy(update={"agent_state": updated_state})


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
        "- 优先确认最佳观看点，再决定主体大小、出屏幅度和镜头节奏。"
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


def _confirmed_brief_payload(request: CreativeDiagnosisRequest) -> dict[str, str]:
    return {
        FIELD_LABELS.get(field, field): value
        for field, value in _brief_fields(request).items()
    }


def _current_message_for_prompt(request: CreativeDiagnosisRequest) -> str:
    current_message = latest_user_context_message(request.agent_state, request.message)
    material_markers = (IMAGE_CONTEXT_MARKER, BRIEF_DOCUMENT_CONTEXT_MARKER)
    if any(marker in (request.message or "") and marker not in current_message for marker in material_markers):
        return request.message
    return current_message


def build_creative_diagnosis_messages(request: CreativeDiagnosisRequest) -> list[dict[str, str]]:
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
        "iteration_control": creative_diagnosis_iteration_preview(request.agent_state),
        "next_brief_question": _next_brief_question(request),
    }
    system_prompt = (
        "你是 Unique Vision AI 的创意提案总监，专注裸眼3D户外媒体内容定制。"
        "你的任务是在同一次思考中理解对话、判断是否已有评估对象，并给出用户可见回复。"
        "不要设置前置 Gate，也不要把判断和正式评估拆成两次调用。\n\n"
        "把 current_user_message、recent_history 和 confirmed_brief 视为一段连续对话。"
        "用户说“这个方案”“上面的创意”“刚才那版”时，应根据最近对话理解所指内容；"
        "上一条回复包含多个备选方向时，整份草案或这些方向的对比本身就是可评估对象，不要求用户先选出唯一一个。\n\n"
        "如果整段对话里确实没有任何可评估的创意对象，status 返回 awaiting_target，message 只自然追问一个最关键的信息。"
        "只要上下文里存在具体创意方向，就返回 evaluated 并直接评估。"
        "评估必须基于当前已确认 Brief；信息不足时可以做阶段性判断，但必须说明不确定性。"
        "允许输出总分或阶段性评分，但不要用分数压过建设性意见。\n\n"
        "评估维度参考：战略匹配度、信息单点清晰度、前三秒钩子、裸眼3D必要性、媒介适配度、"
        "品牌/媒体关联度、情绪驱动力、社交传播力、故事节奏、执行可行性、商业转化价值。\n\n"
        "evaluated 状态的 message 结构固定为：**阶段性创意评估**、**成立点**、**风险点**、**优化方向**。"
        "不要为了推进需求梳理而固定追加问题。只有某项缺失信息会实质改变当前评估结论、风险判断或推荐方向时，"
        "才可以在评估后自然追问一个最关键的问题；否则直接结束评估。next_brief_question 只是一条可选参考，不是必问项。"
        "如果 iteration_control.exit_recommended=true，说明这次输出达到或超过第 5 轮，正文不要再提出开放式追问，"
        "也不要自行编写退出提示，系统会在末尾追加统一的软退出提醒。"
        "不要使用英文 Brief 的返回标题、附件式表达或已记录式固定话术。"
        "不要输出【需求收集完成】；表单触发只由主 Brief 流程负责。\n\n"
        "严格返回 JSON object，不要在 JSON 外输出其他内容："
        "{\"status\":\"evaluated | awaiting_target\",\"message\":\"面向用户的完整回复\"}"
    )
    image_feedback_instruction = build_image_feedback_reply_instruction(request.message)
    if image_feedback_instruction:
        system_prompt += image_feedback_instruction
    if BRIEF_DOCUMENT_CONTEXT_MARKER in (request.message or ""):
        system_prompt += (
            "\n\n【基于上传文档做创意评估的约束】\n"
            "- 必须读取 current_user_message 中的文档解析内容，并用其中明确出现的项目目标、点位参数、"
            "受众、主题、技术或审核条件判断创意的适配性与执行风险。\n"
            "- 不要声称无法读取 PDF/DOC/DOCX，不要把文档内容当作用户已经确认的正式 Brief，也不要补写文档里没有的信息。\n"
        )
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
    result: dict[str, Any],
) -> dict[str, Any]:
    state = _agent_state_for_response(request, current_user)
    now = beijing_now().isoformat()
    previous_pending = state.get("pending_evaluation")
    previous_pending = previous_pending if isinstance(previous_pending, dict) else {}
    iteration_count = creative_diagnosis_iteration_count(state)
    state["pending_evaluation"] = {
        "status": "awaiting_target",
        "source": "creative_diagnosis_agent",
        "reason": str(result.get("reason") or "model_requested_target").strip(),
        "prompt_message": (request.message or "")[:240],
        "iteration_count": iteration_count,
        "iteration_limit": CREATIVE_DIAGNOSIS_ITERATION_LIMIT,
        "exit_recommended": iteration_count >= CREATIVE_DIAGNOSIS_ITERATION_LIMIT,
        "updated_at": now,
    }
    if previous_pending.get("exit_recommended_at"):
        state["pending_evaluation"]["exit_recommended_at"] = previous_pending["exit_recommended_at"]
    state["current_agent"] = "creative_diagnosis_agent"
    state["stage"] = "creative_diagnosis"
    state["business_type"] = request.business_type
    state["updated_at"] = now
    _save_response_agent_state(request, current_user, state)
    return state


def _mark_evaluation_ready_for_feedback(request: CreativeDiagnosisRequest, current_user: Any) -> dict[str, Any]:
    state = _agent_state_for_response(request, current_user)
    state = advance_creative_diagnosis_iteration(
        state,
        prompt_message=request.message,
        reason="creative_diagnosis_evaluated",
    )
    state["business_type"] = request.business_type
    _save_response_agent_state(request, current_user, state)
    return state


def _evaluation_exit_reminder() -> str:
    return (
        "这轮评估经过几次推演，关键判断和取舍已经比较清楚了。先说明一下，这仍然是阶段性创意评估，"
        "不是完整创意方案；具体方案还需要策划专家结合品牌目标、屏幕参数、现场观看动线、现场素材、"
        "审核规范、预算和制作周期继续深化。\n\n"
        "我们可以先回到需求梳理，把这些落地条件补完整；如果评估结论里还有一个必须继续验证的关键点，也可以继续告诉我。"
    )


def _finalize_evaluation_message(request: CreativeDiagnosisRequest, message: str) -> str:
    finalized = (message or "").strip()
    if not creative_diagnosis_iteration_preview(request.agent_state)["exit_recommended"]:
        return finalized
    reminder = _evaluation_exit_reminder()
    if reminder in finalized:
        return finalized
    return f"{finalized}\n\n{reminder}".strip()


@creative_diagnosis_router.post("/creative-diagnosis")
async def ai_creative_diagnosis(
    request: CreativeDiagnosisRequest,
    current_user: AnyUser = Depends(get_current_user_for_public_deployment),
):
    """Evaluate a creative direction and keep context for the next routed turn."""
    request = await _request_with_material_context(request, current_user)
    request = await _request_with_updated_agent_state(request, current_user)
    if not settings.AI_API_KEY:
        message = _finalize_evaluation_message(request, _build_fallback_message(request))
        next_state = _mark_evaluation_ready_for_feedback(request, current_user)
        return {"message": message, "return_to_brief": False, "agent_state": next_state}

    try:
        data = await post_chat_completion(
            {
                "model": settings.AI_MODEL_NAME,
                "messages": build_creative_diagnosis_messages(request),
                "temperature": 0.3,
                "response_format": {"type": "json_object"},
            },
            timeout=settings.AI_HTTP_TIMEOUT,
        )
        result = _extract_json_object(data["choices"][0]["message"]["content"])
        status = str(result.get("status") or "").strip()
        message = str(result.get("message") or "").replace("【需求收集完成】", "").strip()
        if status not in {"evaluated", "awaiting_target"} or not message:
            raise ValueError("invalid creative diagnosis response")
        if status == "awaiting_target":
            next_state = _mark_pending_evaluation(request, current_user, result)
            return {"message": message, "return_to_brief": False, "agent_state": next_state}
        message = _finalize_evaluation_message(request, message)
        next_state = _mark_evaluation_ready_for_feedback(request, current_user)
        return {"message": message, "return_to_brief": False, "agent_state": next_state}
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
        message = _finalize_evaluation_message(request, _build_fallback_message(request))
        next_state = _mark_evaluation_ready_for_feedback(request, current_user)
        return {"message": message, "return_to_brief": False, "agent_state": next_state}
