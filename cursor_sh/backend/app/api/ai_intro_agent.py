"""
业务介绍 Agent — 独立模块
负责向客户介绍公司业务、服务模式、成功案例等。
"""

import re
import os
import json
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.config import settings

intro_router = APIRouter()


class BusinessIntroRequest(BaseModel):
    message: str
    history: list = []


# ───────────────────────────────────────────────────────
# 数据加载
# ───────────────────────────────────────────────────────

def _load_business_knowledge() -> tuple[str, list]:
    """加载业务介绍文档和案例数据"""
    cases_data = []
    try:
        base_dir = os.path.dirname(__file__)
        intro_path = os.path.join(base_dir, '..', 'data', 'business_intro.md')
        cases_json_path = os.path.join(base_dir, '..', 'data', 'cases.json')

        with open(intro_path, "r", encoding="utf-8") as f:
            intro_text = f.read()

        try:
            with open(cases_json_path, "r", encoding="utf-8") as f:
                cases_data = json.load(f)
            cases_text = "\n\n【真实案例库】\n"
            for c in cases_data:
                cases_text += (
                    f"- 案例ID: {c['id']} | {c['title']}\n"
                    f"  分类: {c['category']} | 渠道: {c.get('channel', '')} | 周期: {c.get('duration', '')}\n"
                    f"  亮点: {c.get('highlights', '')}\n"
                )
        except Exception:
            cases_text = ""

        return f"{intro_text}\n{cases_text}", cases_data
    except Exception as e:
        print(f"读取业务介绍文件失败: {e}")
        return "暂无法读取详细业务介绍", cases_data


# ───────────────────────────────────────────────────────
# 主路由
# ───────────────────────────────────────────────────────

@intro_router.post("/business-intro")
async def ai_business_intro(request: BusinessIntroRequest):
    """业务介绍对话"""
    business_knowledge, cases_data = _load_business_knowledge()

    if not settings.AI_API_KEY:
        msg = request.message.lower()
        if "案例" in msg or "作品" in msg:
            reply = ("以下是我们的代表性项目：\n\n" +
                     "\n\n".join([f"**{c['title']}**\n{c['description']}" for c in cases_data[:3]]) +
                     "\n\n每个案例均附有对应的视频展示，可直接点击查看。")
            return {"message": reply, "cases": cases_data[:3]}
        elif "裸眼" in msg or "3d" in msg or "成片" in msg:
            reply = ("裸眼3D是我们的核心业务，提供两种交付模式：\n\n"
                     "**成片购买适配** — 精选模板库，5个工作日交付，万元级预算\n\n"
                     "**AI内容定制** — 品牌专属定制，15个工作日交付，十万级起\n\n"
                     "请问您倾向于哪种模式？")
            relevant = [c for c in cases_data if c.get("category") == "ai_3d_custom"]
            return {"message": reply, "cases": relevant[:2]}
        elif "数字" in msg or "艺术" in msg:
            reply = ("数字艺术内容定制涵盖数字装置、沉浸式互动体验、创意视觉内容等方向。\n\n"
                     "交付周期约7个工作日，报价根据项目复杂度评估。")
            relevant = [c for c in cases_data if c.get("category") == "digital_art"]
            return {"message": reply, "cases": relevant[:2]}
        else:
            reply = ("Unique Video AI 提供三大核心业务板块：\n\n"
                     "**裸眼3D成片购买适配** — 万元级预算，5个工作日交付\n"
                     "**AI裸眼3D内容定制** — 十万级起，15个工作日交付\n"
                     "**数字艺术内容定制** — 沉浸式互动体验，按项目报价\n\n"
                     "如需了解某个板块的详细信息或过往案例，请直接告知。")
            return {"message": reply, "cases": []}

    try:
        system_prompt = (
            "你是 Unique Video AI 公司的资深项目顾问。\n"
            "你代表公司向客户介绍业务，语气应专业、沉稳、自信，体现行业头部服务商的格调。\n"
            "不使用emoji表情，不使用'哦''呢''呀'等语气词，不过度寒暄客套。\n"
            "以下是公司的业务资料：\n\n"
            f"{business_knowledge}\n\n"
            "【对话规则】\n"
            "1. 根据客户的具体问题，有针对性地介绍对应的服务板块\n"
            "2. 当提及案例时，使用标记格式引用：【推荐案例:case_xxx】（替换为实际的案例ID），系统会自动渲染视频卡片\n"
            "3. 当客户表现出下单意向时，在回复末尾加上标记：【引导下单】\n"
            "4. 保持专业权威的态度，用数据和案例说话\n"
            "5. 只介绍以上三个业务板块，不要编造不存在的服务"
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

            # 提取引用的案例ID
            referenced_ids = re.findall(r'【推荐案例:(case_\w+)】', reply)
            referenced_cases = [c for c in cases_data if c["id"] in referenced_ids]
            clean_reply = re.sub(r'【推荐案例:case_\w+】', '', reply).strip()

            return {"message": clean_reply, "cases": referenced_cases}
    except Exception as e:
        print(f"业务介绍 LLM 调用失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
