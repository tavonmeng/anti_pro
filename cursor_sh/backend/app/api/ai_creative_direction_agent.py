"""Creative direction Agent for external media-side conversations."""

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
    image_attachments,
    summarize_uploaded_images,
)
from app.utils.business_log import log_business_event
from app.utils.dependencies import AnyUser, get_current_user_for_public_deployment
from app.utils.log_setup import get_module_logger
from app.utils.timezone import beijing_now

creative_direction_router = APIRouter()
logger = get_module_logger("ai")

_BOUNDARY_NOTE = (
    "**边界说明**\n"
    "这是一版创意方向草案，用来判断视觉策略和讨论大方向，还不是完整创意方案。"
    "具体创意方案还需要策划专家结合品牌目标、屏幕参数、现场观看动线、现场素材、审核规范、预算周期等信息继续深化。"
)

_MINIMUM_CREATIVE_DIRECTION_FIELDS = {"theme_concept", "city_location", "audience_scene"}


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


def _has_minimum_brief_for_creative_direction(request: CreativeDirectionRequest) -> bool:
    brief_state = _brief_state(request)
    readiness = brief_state.get("readiness") or {}
    if readiness.get("level") in {"provisional", "formal"} or readiness.get("can_score") is True:
        return True
    values = _brief_fields(request)
    return _MINIMUM_CREATIVE_DIRECTION_FIELDS.issubset(values.keys())


def _build_low_confidence_fallback_message(request: CreativeDirectionRequest) -> str:
    return (
        "**创意方向草案（低置信度）**\n\n"
        "- **创意方向名称**：三秒出屏记忆点探索\n"
        "- **计划概括**：目前只知道您想做 3D 视频，我不会直接预设具体角色、点位或剧情。"
        "这一版先把方向控制在「一个容易被记住的核心视觉物、一次清晰的空间纵深变化、一个适合路人拍摄的互动瞬间」这个框架里，"
        "后续再根据屏幕结构、观看动线和主题内容收细。\n"
        "- **适合的原因**：在信息还少的阶段，先确定视觉钩子和空间动作，比直接堆完整故事更稳；"
        "它能帮助我们快速判断这条内容是偏破屏冲击、情绪治愈、品牌展示，还是城市打卡传播。\n"
        "- **传播价值**：这个方向优先服务前 3 秒识别和现场拍摄动机，适合作为后续 Brief 讨论的起点，而不是最终执行方案。\n\n"
        "**信息不足说明**\n"
        "这版判断是低置信度的阶段性方向，缺少投放点位、屏幕结构、观看关系、主题/IP/品牌目标等信息，"
        "所以不会把它包装成完整创意方案。\n\n"
        f"{_BOUNDARY_NOTE}\n\n"
        f"{_next_brief_question(request)}"
    )


def _has_image_context_available(request: CreativeDirectionRequest) -> bool:
    if IMAGE_CONTEXT_MARKER in (request.message or ""):
        return True
    for item in agent_context_messages(request.agent_state, fallback_history=request.history):
        if IMAGE_CONTEXT_MARKER in (item.get("content") or ""):
            return True
    return False


def _is_image_based_direction_request(request: CreativeDirectionRequest) -> bool:
    text = re.sub(r"\s+", "", request.message or "")
    if image_attachments(request.attachments):
        return bool(re.search(r"图片|照片|参考图|素材|上传|基于|这个|这张|延展|方向|方案|创意", text))
    return bool(re.search(r"基于(上传的?)?(图片|照片|参考图|素材)|就(这个|这张)(图片|照片|参考图)|参考(这张|这个)?(图片|照片|素材)", text))


def _build_image_context_unavailable_reply(request: CreativeDirectionRequest) -> str:
    names = [
        attachment.name
        for attachment in image_attachments(request.attachments)
        if (attachment.name or "").strip()
    ]
    file_text = f"（{ '、'.join(names) }）" if names else ""
    return (
        f"我已经收到您上传的图片{file_text}，但这次没有稳定拿到图片内容，"
        "所以不先基于文件名做假设性延展。\n\n"
        "为了让创意判断更贴近真实画面，您可以用一句话补充这张图里最关键的主体、场景或风格。"
        "我会基于这些视觉线索，把它拆成几个适合裸眼3D延展的方向。"
    )


def _build_missing_image_attachment_reply() -> str:
    return (
        "我还没有看到这轮消息里有图片附件，所以不能直接基于图片内容做创意延展。\n\n"
        "您可以先把图片上传上来，或者用一句话描述图片里最关键的主体、场景或风格；"
        "我再基于真实视觉线索，把它拆成几个适合裸眼3D的延展方向。"
    )


def _current_user_id(current_user: Any) -> str:
    user_id = getattr(current_user, "id", "") or ""
    return str(user_id).strip()


def _agent_state_for_response(request: CreativeDirectionRequest, current_user: Any = None) -> dict[str, Any]:
    if isinstance(request.agent_state, dict):
        state = deepcopy(request.agent_state)
    else:
        user_id = _current_user_id(current_user)
        state = load_agent_state(request.session_id, user_id, request.business_type) if user_id else {}
    state.setdefault("business_type", request.business_type)
    return state


def _save_response_agent_state(request: CreativeDirectionRequest, current_user: Any, state: dict[str, Any]) -> None:
    user_id = _current_user_id(current_user)
    if not user_id:
        return
    save_agent_state(request.session_id, user_id, state)


def _mark_pending_creative_direction(
    request: CreativeDirectionRequest,
    current_user: Any,
    *,
    status: str,
    reason: str,
) -> dict[str, Any]:
    state = _agent_state_for_response(request, current_user)
    now = beijing_now().isoformat()
    state["pending_creative_direction"] = {
        "status": status,
        "source": "creative_direction_agent",
        "reason": reason,
        "prompt_message": (request.message or "")[:240],
        "updated_at": now,
    }
    state["pending_evaluation"] = None
    state["current_agent"] = "creative_direction_agent"
    state["stage"] = "creative_direction"
    state["business_type"] = request.business_type
    state["updated_at"] = now
    _save_response_agent_state(request, current_user, state)
    return state


def _clear_pending_creative_direction(request: CreativeDirectionRequest, current_user: Any) -> dict[str, Any]:
    state = _agent_state_for_response(request, current_user)
    state["pending_creative_direction"] = None
    state["current_agent"] = "brief_agent"
    state["stage"] = "brief_building"
    state["business_type"] = request.business_type
    state["updated_at"] = beijing_now().isoformat()
    _save_response_agent_state(request, current_user, state)
    return state


def _creative_direction_confidence(request: CreativeDirectionRequest) -> str:
    readiness = (_brief_state(request).get("readiness") or {})
    level = readiness.get("level")
    if level == "formal":
        return "high"
    if level == "provisional" or _has_minimum_brief_for_creative_direction(request):
        return "medium"
    return "low"


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


def _current_message_for_prompt(request: CreativeDirectionRequest) -> str:
    current_message = latest_user_context_message(request.agent_state, request.message)
    if IMAGE_CONTEXT_MARKER in (request.message or "") and IMAGE_CONTEXT_MARKER not in current_message:
        return request.message
    return current_message


def _build_fallback_message(request: CreativeDirectionRequest) -> str:
    if not _has_minimum_brief_for_creative_direction(request):
        return _build_low_confidence_fallback_message(request)

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
    if "边界说明" not in text:
        return False
    has_boundary = any(
        marker in text
        for marker in [
            "不是完整创意方案",
            "还不是完整创意方案",
            "并非完整的创意方案",
            "并非完整创意方案",
            "不是完整的创意方案",
            "非完整创意方案",
        ]
    )
    has_handoff_context = "策划专家" in text or "继续深化" in text or "实际落地" in text
    return has_boundary and has_handoff_context


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
    recent_history = agent_context_messages(
        request.agent_state,
        fallback_history=request.history,
    )
    current_message = _current_message_for_prompt(request)
    if recent_history and recent_history[-1]["role"] == "user" and recent_history[-1]["content"] == current_message:
        recent_history = recent_history[:-1]
    brief_values = {
        FIELD_LABELS.get(field, field): value
        for field, value in _brief_fields(request).items()
    }
    payload = {
        "current_user_message": current_message,
        "recent_history": recent_history,
        "confirmed_brief": brief_values,
        "creative_direction_confidence": _creative_direction_confidence(request),
        "next_brief_question": _next_brief_question(request),
    }
    system_prompt = (
        "你是 Unique Vision AI 的创意提案总监，专注裸眼3D户外媒体内容定制。"
        "你的任务是生成一版轻量、专业、可讨论的创意方向草案，或基于已有创意、评估意见和用户反馈继续优化方案；"
        "不要把优化请求回答成创意评估。\n\n"
        "草案必须基于当前已确认 Brief；信息不足时可以做阶段性方向，但必须说明还不是完整提案。"
        "如果 creative_direction_confidence 为 low，必须明确标注低置信度，只输出方向框架和假设，不要编造具体点位、角色、预算或上刊时间。"
        "不要输出完整分镜脚本、时间轴脚本、制作排期、报价或执行说明。\n\n"
        "如果 current_user_message 是要求优化、修改、改写、调整或升级上一版创意，必须结合 recent_history 中最近的创意方案、"
        "阶段性评估和用户反馈，输出 **创意方向优化稿**；优先解决评估中指出的风险点，不要重新从零发散。"
        "优化稿结构为：**优化原则**、**优化后创意概念**、**优化后动态设计**、**为什么更成立**、**边界说明**。"
        "如果 current_user_message 是要求新生成方向，输出结构为：**创意方向草案**，包含 **创意方向名称**、**计划概括**、"
        "**适合的原因**、**传播价值**，然后输出 **边界说明**。"
        "边界说明必须明确：这只是创意方向草案，不是完整创意方案；具体创意方案还需要策划专家结合品牌目标、屏幕参数、现场观看动线、现场素材、审核规范、预算周期等信息继续深化。"
        "最后用一段自然口语承接到 next_brief_question，只问一个问题，不要使用英文 Brief 的返回标题、附件式表达或已记录式固定话术。"
        "不要输出【需求收集完成】；表单触发只由主 Brief 流程负责。"
    )
    image_feedback_instruction = build_image_feedback_reply_instruction(request.message)
    if image_feedback_instruction:
        system_prompt += image_feedback_instruction
        system_prompt += (
            "\n\n【基于图片做创意延展的约束】\n"
            "- 当用户要求基于图片、参考图、现场图或上传素材做创意延展时，必须直接围绕图片理解摘要里的可见主体、风格质感、场景关系做延展；"
            "每个方向都要能对应到图片中的一个具体视觉线索。\n"
            "- 不要按平台业务类型分类，不要输出 AI驱动3D OOH内容定制、数字艺术与沉浸式视觉设计、广告视觉与动态影像制作 这类服务清单式回答；"
            "也不要只介绍 Unique Vision AI 的能力范围。\n"
        )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]


@creative_direction_router.post("/creative-direction")
async def ai_creative_direction(
    request: CreativeDirectionRequest,
    current_user: AnyUser = Depends(get_current_user_for_public_deployment),
):
    """Generate a creative direction draft, then return to Brief collection."""
    request = await _request_with_image_context(request)
    if _is_image_based_direction_request(request) and not _has_image_context_available(request):
        if not image_attachments(request.attachments):
            next_state = _mark_pending_creative_direction(
                request,
                current_user,
                status="awaiting_image",
                reason="image_based_direction_missing_attachment",
            )
            return {
                "message": _build_missing_image_attachment_reply(),
                "return_to_brief": False,
                "agent_state": next_state,
            }
        next_state = _mark_pending_creative_direction(
            request,
            current_user,
            status="awaiting_image_context",
            reason="image_context_unavailable",
        )
        return {
            "message": _build_image_context_unavailable_reply(request),
            "return_to_brief": False,
            "agent_state": next_state,
        }

    if not settings.AI_API_KEY:
        next_state = _clear_pending_creative_direction(request, current_user)
        return {"message": _ensure_boundary_note(_build_fallback_message(request)), "return_to_brief": True, "agent_state": next_state}

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
        next_state = _clear_pending_creative_direction(request, current_user)
        return {"message": message, "return_to_brief": True, "agent_state": next_state}
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
