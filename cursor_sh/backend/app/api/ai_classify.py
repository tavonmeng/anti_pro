"""
意图分类器 — 独立模块
负责对用户消息进行意图分类，决定路由到哪个 Agent。
"""

import httpx
from fastapi import APIRouter
from pydantic import BaseModel
from app.config import settings

classify_router = APIRouter()


class ClassifyRequest(BaseModel):
    message: str
    history: list = []


# ───────────────────────────────────────────────────────
# 关键词规则（快速匹配，无需调用 LLM）
# ───────────────────────────────────────────────────────

_QUICK_MAP = {
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
            return {"intent": intent}

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
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.AI_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.AI_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": settings.AI_MODEL_NAME,
                        "messages": [
                            {"role": "system", "content": classify_prompt},
                            {"role": "user", "content": msg}
                        ],
                        "max_tokens": 20,
                        "temperature": 0
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                result = data["choices"][0]["message"]["content"].strip().lower()
                intent = result if result in _VALID_INTENTS else "order_create"
                return {"intent": intent}
        except Exception as e:
            print(f"意图分类 LLM 调用失败: {e}")

    # ── 3. 默认兜底 ──
    return {"intent": "order_create"}
