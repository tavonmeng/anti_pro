"""
意图分类器 — 独立模块
负责对用户消息进行意图分类，决定路由到哪个 Agent。
"""

import httpx
import re
from fastapi import APIRouter
from pydantic import BaseModel, Field
from app.config import settings
from app.services.ai_client import post_chat_completion
from app.services.platform_service_catalog import VALID_BUSINESS_TYPES
from app.utils.business_log import log_business_event
from app.utils.log_setup import get_module_logger

classify_router = APIRouter()
logger = get_module_logger("ai")


class ClassifyRequest(BaseModel):
    message: str
    history: list = Field(default_factory=list)


# ───────────────────────────────────────────────────────
# 关键词规则（快速匹配，无需调用 LLM）
# ───────────────────────────────────────────────────────

_QUICK_MAP = {
    "order_create": [
        "下单", "想下单", "咨询下单", "创建需求", "提交需求",
        "想做", "要做", "做一个", "做个", "定制", "想定制", "要定制",
        "需要做", "想要做", "可以开始", "买", "购买", "成片", "模板",
    ],
    "order_query": [
        "订单", "进度", "状态", "查看", "查询", "我的单", "下过的",
        "怎么样了", "什么情况",
    ],
    "business_intro": [
        "了解", "介绍", "业务", "案例", "服务",
        "你们做什么", "什么公司", "你们公司",
    ],
}

# 支持的意图列表
_VALID_INTENTS = ["order_create", "order_query", "business_intro", "general"]


def _detect_business_type(message: str) -> str | None:
    """根据用户原话判断业务类型。只在后端做路由判断，前端只消费结果。"""
    text = message.strip()
    lower = text.lower()
    direct_names = {
        "3d ooh数字内容资源库": "video_purchase",
        "3dooh数字内容资源库": "video_purchase",
        "ai驱动3d ooh内容定制": "ai_3d_custom",
        "ai驱动3dooh内容定制": "ai_3d_custom",
        "数字艺术与沉浸式视觉设计": "digital_art",
        "广告视觉与动态影像制作": "motion_content",
        "广告视觉": "motion_content",
        "动态影像制作": "motion_content",
        "户外媒体后期制作服务": "media_post_production",
        "户外媒体后期": "media_post_production",
        "广告投放分析与效果报告": "campaign_analytics",
        "投放分析": "campaign_analytics",
        "效果报告": "campaign_analytics",
        "ai裸眼3d内容定制": "ai_3d_custom",
        "裸眼3d内容定制": "ai_3d_custom",
        "裸眼3d3D OOH数字内容资源库": "video_purchase",
        "3D OOH数字内容资源库": "video_purchase",
        "数字艺术与沉浸式视觉设计": "digital_art",
    }
    for name, business_type in direct_names.items():
        if name in lower:
            return business_type

    if re.search(r"成片|购买|模板|现成|成品|买", text):
        return "video_purchase"
    if re.search(r"tvc|fooh|vj|动态影像|动态视觉|广告视觉|广告影片|平面广告|motion", text, re.I):
        return "motion_content"
    if re.search(r"后期|精修|修图|视频精修|cgi|商业摄影|拍摄|航拍|drone|retouch", text, re.I):
        return "media_post_production"
    if re.search(r"投放分析|效果报告|数据报告|受众分析|传播效果|campaign|analytics|report", text, re.I):
        return "campaign_analytics"
    if re.search(r"数字艺术|数字.*艺术|沉浸|互动|装置|投影", text):
        return "digital_art"
    if re.search(r"裸眼3d|裸眼3D|3d定制|3D定制|3d内容|3D内容|裸眼.*定制", text):
        return "ai_3d_custom"
    return None


# ───────────────────────────────────────────────────────
# 主路由
# ───────────────────────────────────────────────────────

@classify_router.post("/classify")
async def ai_classify(request: ClassifyRequest):
    """对用户消息进行意图分类

    返回值：
    - order_create: 咨询下单 / 描述项目需求
    - order_query: 查看订单状态 / 进度
    - business_intro: 了解公司业务 / 看案例
    - general: 其他闲聊或通用问题
    """
    msg = request.message.strip()

    # ── 1. 关键词快速匹配（零成本） ──
    for intent, keywords in _QUICK_MAP.items():
        if any(kw in msg for kw in keywords):
            business_type = _detect_business_type(msg)
            if intent == "order_create" and not business_type:
                business_type = "ai_3d_custom"
            return {"intent": intent, "business_type": business_type}

    # ── 2. LLM 分类（关键词未命中时） ──
    if settings.AI_API_KEY:
        try:
            classify_prompt = (
                "你是一个意图分类器。根据用户消息判断意图，只返回以下4个词之一，不要输出任何其他内容：\n"
                "- order_create: 用户想咨询下单、描述项目需求、定制内容\n"
                "- order_query: 用户想查看订单状态、进度、历史订单\n"
                "- business_intro: 用户想了解公司业务、看案例、咨询服务范围\n"
                "- general: 其他闲聊或通用问题"
            )
            data = await post_chat_completion(
                {
                    "model": settings.AI_MODEL_NAME,
                    "messages": [
                        {"role": "system", "content": classify_prompt},
                        {"role": "user", "content": msg}
                    ],
                    "max_tokens": 20,
                    "temperature": 0
                },
                timeout=10.0,
            )
            result = data["choices"][0]["message"]["content"].strip().lower()
            intent = result if result in _VALID_INTENTS else "order_create"
            business_type = _detect_business_type(msg)
            if business_type not in VALID_BUSINESS_TYPES:
                business_type = None
            if intent == "order_create" and not business_type:
                business_type = "ai_3d_custom"
            return {"intent": intent, "business_type": business_type}
        except Exception as e:
            log_business_event(
                logger,
                "ai_intent_classify_failed",
                level="warning",
                history_count=len(request.history or []),
                error=str(e),
            )

    # ── 3. 默认兜底 ──
    return {"intent": "order_create", "business_type": _detect_business_type(msg) or "ai_3d_custom"}
