"""Creative diagnosis Agent for external media-side conversations."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.services.ai_client import post_chat_completion
from app.services.ai_brief_state import FIELD_LABELS, MEDIA_3D_BRIEF_FIELDS
from app.services.ai_image_understanding import (
    UploadedAttachment,
    append_image_context_to_message,
    build_image_feedback_reply_instruction,
    summarize_uploaded_images,
)
from app.utils.business_log import log_business_event
from app.utils.log_setup import get_module_logger

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


def build_creative_diagnosis_messages(request: CreativeDiagnosisRequest) -> list[dict[str, str]]:
    recent_history = [
        {"role": h["role"], "content": str(h.get("content") or "")[:700]}
        for h in (request.history or [])[-8:]
        if h.get("role") in {"user", "assistant"} and h.get("content")
    ]
    brief_values = {
        FIELD_LABELS.get(field, field): value
        for field, value in _brief_fields(request).items()
    }
    readiness = _brief_state(request).get("readiness") or {}
    payload = {
        "current_user_message": request.message,
        "recent_history": recent_history,
        "confirmed_brief": brief_values,
        "creative_readiness": readiness,
        "next_brief_question": _next_brief_question(request),
    }
    system_prompt = (
        "你是 Unique Vision AI 的创意提案总监，专注裸眼3D户外媒体内容定制。"
        "你的任务是先完成专业创意评估，而不是为了补齐 Brief 才评价创意。\n\n"
        "评估必须基于当前已确认 Brief；信息不足时可以做阶段性判断，但必须说明不确定性。"
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


@creative_diagnosis_router.post("/creative-diagnosis")
async def ai_creative_diagnosis(request: CreativeDiagnosisRequest):
    """Evaluate a creative direction, then return the conversation to Brief collection."""
    request = await _request_with_image_context(request)
    if not settings.AI_API_KEY:
        return {"message": _build_fallback_message(request), "return_to_brief": True}

    try:
        data = await post_chat_completion(
            {
                "model": settings.AI_MODEL_NAME,
                "messages": build_creative_diagnosis_messages(request),
                "temperature": 0.3,
            },
            timeout=settings.AI_HTTP_TIMEOUT,
        )
        message = data["choices"][0]["message"]["content"].replace("【需求收集完成】", "").strip()
        return {"message": message, "return_to_brief": True}
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
