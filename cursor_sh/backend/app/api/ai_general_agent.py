"""
通用问答 Agent — 独立模块
兜底处理：当用户意图不属于下单/查订单/了解业务时，提供通用应答并引导。
"""

import json
import re
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from app.config import settings
from app.services.ai_client import post_chat_completion
from app.utils.business_log import log_business_event
from app.utils.log_setup import get_module_logger

general_router = APIRouter()
logger = get_module_logger("ai")

VALID_INTENTS = {"order_create", "order_query", "business_intro", "general"}
VALID_BUSINESS_TYPES = {"ai_3d_custom", "video_purchase", "digital_art"}
ROUTE_MESSAGES = {
    "order_create": "好的，我来为您进入需求梳理流程。",
    "order_query": "好的，我来为您查询订单信息。",
    "business_intro": "好的，我来为您介绍业务信息。",
}


class GeneralRequest(BaseModel):
    session_id: str
    message: str
    history: list = Field(default_factory=list)


def _detect_business_type(message: str) -> str | None:
    text = message.strip()
    lower = text.lower()
    direct_names = {
        "ai裸眼3d内容定制": "ai_3d_custom",
        "裸眼3d内容定制": "ai_3d_custom",
        "裸眼3d成片购买适配": "video_purchase",
        "成片购买适配": "video_purchase",
        "数字艺术内容定制": "digital_art",
    }
    for name, business_type in direct_names.items():
        if name in lower:
            return business_type

    if re.search(r"成片|购买|模板|现成|成品|买", text):
        return "video_purchase"
    if re.search(r"数字艺术|数字.*艺术|沉浸|互动|装置|投影", text):
        return "digital_art"
    if re.search(r"裸眼3d|裸眼3D|3d定制|3D定制|3d内容|3D内容|裸眼.*定制", text):
        return "ai_3d_custom"
    return None


def _quick_route(message: str) -> dict[str, Any] | None:
    text = message.strip()
    if any(kw in text for kw in ["订单", "进度", "状态", "查看", "查询", "我的单", "下过的"]):
        return {"intent": "order_query", "business_type": None, "confidence": 0.9}
    if any(kw in text for kw in ["了解", "介绍", "业务", "案例", "服务", "你们做什么", "什么公司"]):
        return {"intent": "business_intro", "business_type": None, "confidence": 0.85}
    if any(kw in text for kw in [
        "下单", "想下单", "咨询下单", "创建需求", "提交需求",
        "想做", "要做", "做一个", "做个", "定制", "想定制", "要定制",
        "需要做", "想要做", "可以开始", "买", "购买", "成片", "模板",
    ]):
        return {
            "intent": "order_create",
            "business_type": _detect_business_type(text) or "ai_3d_custom",
            "confidence": 0.9,
        }
    return None


def _extract_json_object(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.S)
        if not match:
            raise
        return json.loads(match.group(0))


async def _classify_general_route(request: GeneralRequest) -> dict[str, Any]:
    quick = _quick_route(request.message)
    if quick:
        return quick

    route_prompt = (
        "你是 Unique Video AI 的后端意图路由器。请根据用户最新消息和少量历史，判断应该交给哪个 agent。\n"
        "只返回 JSON，不要输出 Markdown，不要解释。\n\n"
        "intent 只能是以下之一：\n"
        "- order_create: 用户想下单、开始项目、定制内容、描述项目需求、希望有人协助梳理需求\n"
        "- order_query: 用户想查看订单、进度、状态、历史订单\n"
        "- business_intro: 用户想了解公司、业务、案例、服务范围\n"
        "- general: 其他闲聊或通用问题\n\n"
        "business_type 只能是 ai_3d_custom、video_purchase、digital_art 或 null。\n"
        "如果 intent=order_create 但无法判断具体业务，在媒体端默认使用 ai_3d_custom。\n"
        "业务判断：成片/模板/现成/购买 => video_purchase；数字艺术/沉浸/互动/装置/投影 => digital_art；裸眼3D定制/3D内容/一般下单 => ai_3d_custom。\n\n"
        "返回格式：{\"intent\":\"general\",\"business_type\":null,\"confidence\":0.0}"
    )
    messages = [{"role": "system", "content": route_prompt}]
    for h in (request.history or [])[-6:]:
        if h.get("role") in ["user", "assistant"] and h.get("content"):
            messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": request.message})

    data = await post_chat_completion(
        {
            "model": settings.AI_MODEL_NAME,
            "messages": messages,
            "max_tokens": 120,
            "temperature": 0,
        },
        timeout=10.0,
    )
    raw = data["choices"][0]["message"]["content"]
    parsed = _extract_json_object(raw)
    intent = parsed.get("intent") if parsed.get("intent") in VALID_INTENTS else "general"
    business_type = parsed.get("business_type")
    if business_type not in VALID_BUSINESS_TYPES:
        business_type = _detect_business_type(request.message)
    if intent == "order_create" and not business_type:
        business_type = "ai_3d_custom"
    return {
        "intent": intent,
        "business_type": business_type,
        "confidence": parsed.get("confidence"),
    }


@general_router.post("/general")
async def ai_general(request: GeneralRequest, raw_request: Request):
    """通用问答兜底"""
    route = _quick_route(request.message) or {"intent": "general", "business_type": None}
    if not settings.AI_API_KEY:
        reply = (
            "我是 Unique Video AI 的项目顾问。\n\n"
            "我们是国内裸眼3D视觉内容领域的头部服务商，专注于为品牌提供高品质视觉解决方案。\n\n"
            "我可以协助您：\n"
            "- 咨询下单 — 梳理项目需求并创建订单\n"
            "- 查看订单 — 查询订单进展与状态\n"
            "- 了解业务 — 了解服务体系与过往案例\n\n"
            "请问您需要哪方面的支持？"
        )
        return {"message": reply, **route}

    try:
        route = await _classify_general_route(request)
        if route["intent"] != "general":
            log_business_event(
                logger,
                "ai_general_route_detected",
                session_id=request.session_id,
                intent=route["intent"],
                business_type=route.get("business_type"),
                confidence=route.get("confidence"),
            )
            return {
                "message": ROUTE_MESSAGES.get(route["intent"], ""),
                "intent": route["intent"],
                "business_type": route.get("business_type"),
                "confidence": route.get("confidence"),
            }

        system_prompt = (
            "你是 Unique Video AI 公司的项目顾问。\n"
            "公司是国内裸眼3D视觉内容和数字艺术创意领域的头部服务商。\n"
            "当用户的问题不属于下单、查订单、了解业务时，简洁专业地回答，并自然引导用户了解公司业务或开始下单。\n"
            "语气专业沉稳，不使用表情符号，不过度寒暄。"
        )
        llm_messages = [{"role": "system", "content": system_prompt}]
        for h in request.history:
            if h.get("role") in ["user", "assistant"] and h.get("content"):
                llm_messages.append({"role": h["role"], "content": h["content"]})
        llm_messages.append({"role": "user", "content": request.message})

        data = await post_chat_completion(
            {"model": settings.AI_MODEL_NAME, "messages": llm_messages},
            timeout=30.0,
        )
        reply = data["choices"][0]["message"]["content"]
        return {"message": reply, "intent": "general", "business_type": None}
    except HTTPException:
        raise
    except Exception as e:
        log_business_event(
            logger,
            "ai_general_failed",
            level="error",
            session_id=request.session_id,
            history_count=len(request.history or []),
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=str(e))
