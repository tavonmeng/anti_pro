"""Creative direction Agent for external media-side conversations."""

from __future__ import annotations

import json
import re
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

creative_direction_router = APIRouter()
logger = get_module_logger("ai")

_BOUNDARY_NOTE = (
    "**边界说明**\n"
    "这是一版创意方向草案，用来判断视觉策略和讨论大方向，还不是完整创意方案。"
    "具体创意方案还需要策划专家结合品牌目标、屏幕参数、现场观看动线、现场素材、审核规范、预算周期等信息继续深化。"
)


class CreativeDirectionRequest(BaseModel):
    session_id: str
    message: str
    history: list = Field(default_factory=list)
    business_type: str = "ai_3d_custom"
    agent_state: dict[str, Any] | None = None
    attachments: list[UploadedAttachment] = Field(default_factory=list)


async def _request_with_image_context(request: CreativeDirectionRequest) -> CreativeDirectionRequest:
    image_context = await summarize_uploaded_images(
        message=request.message,
        attachments=request.attachments,
    )
    if not image_context:
        return request
    return request.model_copy(
        update={"message": append_image_context_to_message(request.message, image_context)}
    )


def _brief_state(request: CreativeDirectionRequest) -> dict[str, Any]:
    return ((request.agent_state or {}).get("brief_state") or {})


def _brief_fields(request: CreativeDirectionRequest) -> dict[str, str]:
    fields = (_brief_state(request).get("fields") or {})
    values: dict[str, str] = {}
    for field in MEDIA_3D_BRIEF_FIELDS:
        raw = fields.get(field, {})
        value = raw.get("value") if isinstance(raw, dict) else raw
        text = str(value or "").strip()
        if text:
            values[field] = text
    return values


def _next_brief_question(request: CreativeDirectionRequest) -> str:
    values = _brief_fields(request)
    priority = [
        ("viewing_path", "为了把这个方向从概念推进到能落地的方案，想确认一下观众主要从哪个方向观看：正面、斜侧、仰视，还是有多条人流动线？"),
        ("media_specs", "这个方向需要结合屏幕结构来控制透视和出屏幅度，屏幕分辨率、物理尺寸或转角结构目前有大概参数吗？"),
        ("content_review", "后续深化前还需要确认审核边界，有没有必须避免的内容、动作或表现尺度？"),
        ("online_time", "如果这个方向继续推进，预计上刊或交付时间大概是什么时候？"),
        ("resource_background", "这个点位的媒体资源背景可以再补一点吗，比如商圈属性、人流特征或媒体定位？"),
    ]
    for field, question in priority:
        if not values.get(field):
            return question
    return "如果方便的话，也可以发一张现场实拍图、屏幕照片或参考素材，我可以基于真实环境把这个方向继续收细。"


def _build_fallback_message(request: CreativeDirectionRequest) -> str:
    values = _brief_fields(request)
    location = values.get("city_location") or "当前点位"
    audience = values.get("audience_scene") or "现场人群"
    theme = values.get("theme_concept") or "本次主题"
    direction_name = _fallback_direction_name(values, request.message)
    return (
        "**创意方向草案**\n\n"
        f"- **创意方向名称**：{direction_name}\n"
        f"- **计划概括**：以「{theme}」为核心，把{location}的空间感做成一段由远及近的视觉展开。"
        "画面先建立城市或场景识别，再让核心视觉元素从屏幕结构中靠近观众，形成适合停留和拍摄的瞬间。\n"
        f"- **适合的原因**：这个方向适合面向{audience}的户外大屏传播，因为它把地域/主题记忆点和裸眼3D的空间错觉结合起来，"
        "不会只停留在单一出屏奇观。\n"
        "- **传播价值**：重点制造前 3 秒的识别钩子和中段的拍摄高点，有利于形成现场围观、短视频传播和招商展示素材。\n\n"
        f"{_BOUNDARY_NOTE}\n\n"
        f"{_next_brief_question(request)}"
    )


def _has_clear_boundary_note(message: str) -> bool:
    text = re.sub(r"\s+", "", message or "")
    return "策划专家" in text and ("不是完整创意方案" in text or "还不是完整创意方案" in text)


def _ensure_boundary_note(message: str) -> str:
    cleaned = (message or "").replace("【需求收集完成】", "").strip()
    if not cleaned or _has_clear_boundary_note(cleaned):
        return cleaned

    paragraphs = re.split(r"\n\s*\n", cleaned)
    last = paragraphs[-1].strip() if paragraphs else ""
    if last and ("？" in last or "?" in last) and not last.startswith("- "):
        body = "\n\n".join(paragraphs[:-1]).strip()
        if body:
            return f"{body}\n\n{_BOUNDARY_NOTE}\n\n{last}".strip()
    return f"{cleaned}\n\n{_BOUNDARY_NOTE}".strip()


def _creative_direction_timeout() -> float:
    return max(
        float(settings.AI_HTTP_TIMEOUT or 0),
        float(settings.AI_CREATIVE_DIRECTION_TIMEOUT or 120.0),
    )


def _fallback_direction_name(values: dict[str, str], message: str) -> str:
    text = " ".join([values.get("theme_concept", ""), values.get("art_direction", ""), message or ""])
    if re.search(r"熊猫|panda", text, re.I):
        return "云绒熊猫探屏"
    if re.search(r"毛绒|动物|萌宠", text):
        return "云绒伙伴探屏"
    if "西湖" in text:
        return "湖光折境"
    if re.search(r"科技|未来|赛博", text):
        return "未来折境"
    return "三秒出屏记忆点"


def build_creative_direction_messages(request: CreativeDirectionRequest) -> list[dict[str, str]]:
    recent_history = [
        {"role": h["role"], "content": str(h.get("content") or "")[:700]}
        for h in (request.history or [])[-8:]
        if h.get("role") in {"user", "assistant"} and h.get("content")
    ]
    brief_values = {
        FIELD_LABELS.get(field, field): value
        for field, value in _brief_fields(request).items()
    }
    payload = {
        "current_user_message": request.message,
        "recent_history": recent_history,
        "confirmed_brief": brief_values,
        "next_brief_question": _next_brief_question(request),
    }
    system_prompt = (
        "你是 Unique Vision AI 的创意提案总监，专注裸眼3D户外媒体内容定制。"
        "你的任务是先生成一版轻量、专业、可讨论的创意方向草案，而不是做创意评估。\n\n"
        "草案必须基于当前已确认 Brief；信息不足时可以做阶段性方向，但必须说明还不是完整提案。"
        "不要输出完整分镜脚本、时间轴脚本、制作排期、报价或执行说明。\n\n"
        "输出结构固定为：**创意方向草案**，包含 **创意方向名称**、**计划概括**、**适合的原因**、"
        "**传播价值**，然后输出 **边界说明**。"
        "边界说明必须明确：这只是创意方向草案，不是完整创意方案；具体创意方案还需要策划专家结合品牌目标、屏幕参数、现场观看动线、现场素材、审核规范、预算周期等信息继续深化。"
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


@creative_direction_router.post("/creative-direction")
async def ai_creative_direction(request: CreativeDirectionRequest):
    """Generate a creative direction draft, then return to Brief collection."""
    request = await _request_with_image_context(request)
    if not settings.AI_API_KEY:
        return {"message": _ensure_boundary_note(_build_fallback_message(request)), "return_to_brief": True}

    try:
        data = await post_chat_completion(
            {
                "model": settings.AI_MODEL_NAME,
                "messages": build_creative_direction_messages(request),
                "temperature": 0.5,
                "enable_thinking": True,
            },
            timeout=_creative_direction_timeout(),
            attempts=settings.AI_CREATIVE_DIRECTION_RETRY_ATTEMPTS,
        )
        message = _ensure_boundary_note(data["choices"][0]["message"]["content"])
        return {"message": message, "return_to_brief": True}
    except HTTPException as exc:
        log_business_event(
            logger,
            "ai_creative_direction_provider_unavailable",
            level="warning",
            session_id=request.session_id,
            business_type=request.business_type,
            status_code=exc.status_code,
            detail=str(exc.detail),
        )
        return {"message": _ensure_boundary_note(_build_fallback_message(request)), "return_to_brief": True}
    except Exception as exc:
        log_business_event(
            logger,
            "ai_creative_direction_failed",
            level="warning",
            session_id=request.session_id,
            business_type=request.business_type,
            error=str(exc),
        )
        return {"message": _ensure_boundary_note(_build_fallback_message(request)), "return_to_brief": True}
