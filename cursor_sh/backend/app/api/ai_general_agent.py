"""
通用问答 Agent — 独立模块
兜底处理：当用户意图不属于下单/查订单/了解业务时，提供通用应答并引导。
"""

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from app.config import settings

general_router = APIRouter()


class GeneralRequest(BaseModel):
    session_id: str
    message: str
    history: list = []


@general_router.post("/general")
async def ai_general(request: GeneralRequest, raw_request: Request):
    """通用问答兜底"""
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
        return {"message": reply}

    try:
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

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.AI_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.AI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={"model": settings.AI_MODEL_NAME, "messages": llm_messages},
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            reply = data["choices"][0]["message"]["content"]
            return {"message": reply}
    except Exception as e:
        print(f"通用问答 LLM 调用失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
