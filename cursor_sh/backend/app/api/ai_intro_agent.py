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
    from app.utils.knowledge import get_knowledge_file

    cases_data = []
    try:
        intro_path = get_knowledge_file('business_intro.md')
        cases_json_path = get_knowledge_file('cases.json')

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

            "【案例引用规则 — 最高优先级】\n"
            "1. 当客户询问案例、作品、成功项目、过往经验、案例展示时，你**只能**引用上述【真实案例库】中的案例，**绝对禁止**编造、虚构或假设任何案例\n"
            "2. 回复中提到案例时，**必须**使用标记格式：【推荐案例:case_xxx】（替换为实际的案例ID），系统会自动展示对应的视频卡片\n"
            "3. 介绍案例时直接使用案例库中的标题、描述、亮点、渠道等真实数据，不要自行改编或增添\n"
            "4. 即使案例库中没有完全匹配客户需求的案例，也必须从库中推荐最接近的1-2个案例，并说明'虽然行业不同，但在技术实现和视觉呈现上有很强的参考价值'，绝不可以说没有案例\n"
            "5. 每次提及案例，都必须附带对应的【推荐案例:case_xxx】标记，不可省略\n"
            "6. **每次只展示1个案例**，不要一次性把所有案例全部列出。展示完一个案例后，主动询问客户是否想看更多案例或其他类型的案例，例如：'还有其他几个不同行业的代表项目，需要继续了解吗？'\n"
            "7. **当案例库中的所有案例都已经展示过后，绝对不可以再编造新的案例**。应自然地告知客户：'以上是我们目前可公开展示的代表性项目。由于部分客户项目涉及保密协议，更多案例需要在具体合作洽谈时提供。' 然后引导客户进一步了解业务细节或进入需求梳理流程\n\n"

            "【对话节奏规则】\n"
            "1. 当你完成业务板块介绍后，主动询问客户是否想看一些案例，例如：\n"
            "   '以上是我们核心服务的概览。我们在多个行业均有成功落地案例，需要我为您展示几个代表性的项目吗？'\n"
            "2. 根据客户的具体问题，有针对性地介绍对应的服务板块\n"
            "3. 保持专业权威的态度，用真实数据和案例说话\n"
            "4. 只介绍以上三个业务板块，不要编造不存在的服务\n\n"

            "【引导下单规则 — 核心】\n"
            "只有在以下明确信号出现时，才在回复的最后一行加上标记：【引导下单】\n"
            "  a) 客户直接表达下单意向（如'怎么下单''可以开始吗''我想定制一个'）\n"
            "  b) 客户描述了具体的项目需求或场景（如'我们品牌想做一个...'、'我们有个项目需要...'）\n"
            "  c) 客户主动问价格、报价、周期、合同、付款等执行层面的问题\n"
            "  d) 客户在多轮对话后明确表示不再有其他疑问了（如'没有了''就这些''了解了，怎么开始'）\n\n"

            "当客户描述了具体需求并触发引导下单时，你需要：\n"
            "  1. 根据需求匹配最合适的业务类型（ai_3d_custom / video_purchase / digital_art）\n"
            "  2. 提取客户已经提到的需求要素（品牌、场景、风格、城市等）\n"
            "  3. 使用格式：【引导下单:业务类型:需求摘要】，例如：\n"
            "     【引导下单:ai_3d_custom:耐克品牌，成都太古里投放，运动鞋主题】\n"
            "     【引导下单:digital_art:美妆品牌快闪店，沉浸式互动装置】\n"
            "  4. 如果无法判断具体业务类型，使用：【引导下单】（不带参数，由用户自选）\n\n"

            "【禁止过早引导】\n"
            "以下情形绝对不能加【引导下单】标记：\n"
            "  - 刚介绍完公司业务概览，客户还没有深入提问\n"
            "  - 刚展示完案例，客户还在浏览或追问细节\n"
            "  - 客户只是简单回应'不错''挺好的''有意思'，但没有表达进一步意向\n"
            "  - 对话不足3轮（用户发言不足3次）\n"
            "  - 客户仍在问业务相关的问题（如'还有其他案例吗''数字艺术是什么意思'）\n\n"

            "引导方式要自然、不生硬，像顾问做完介绍后的自然收尾。示例：\n"
            "  - '如果您已有初步的项目构想，我可以直接进入需求梳理环节，帮您快速推进。'\n"
            "  - '从您描述的场景来看，AI裸眼3D内容定制会是比较匹配的方案。我们可以进一步聊聊具体需求。'\n"
            "注意：引导语要融入回答的结尾，不要单独一行突兀地出现。标记放在全文最后即可。\n"
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
            valid_case_ids = {c["id"] for c in cases_data}
            # 硬性防护：过滤掉 LLM 编造的不存在的案例ID
            fake_ids = [cid for cid in referenced_ids if cid not in valid_case_ids]
            if fake_ids:
                # 从回复文本中移除伪造案例的标记
                for fid in fake_ids:
                    reply = reply.replace(f'【推荐案例:{fid}】', '')
                referenced_ids = [cid for cid in referenced_ids if cid in valid_case_ids]
            referenced_cases = [c for c in cases_data if c["id"] in referenced_ids]
            clean_reply = re.sub(r'【推荐案例:case_\w+】', '', reply).strip()

            # 硬性兜底：对话不足3轮时，即使 LLM 输出了引导标记也强制移除
            user_turn_count = sum(1 for h in request.history if h.get("role") == "user") + 1
            guide_info = {}

            # 解析引导下单标记（支持带参数和不带参数两种格式）
            guide_match = re.search(r'【引导下单(?::([^:】]+):([^】]+))?】', clean_reply)
            if guide_match:
                if user_turn_count < 3:
                    # 对话不足3轮，强制移除
                    clean_reply = re.sub(r'【引导下单(?::[^】]+)?】', '', clean_reply).strip()
                else:
                    clean_reply = re.sub(r'【引导下单(?::[^】]+)?】', '', clean_reply).strip()
                    guide_info["should_guide"] = True
                    if guide_match.group(1) and guide_match.group(2):
                        guide_info["business_type"] = guide_match.group(1).strip()
                        guide_info["requirement_summary"] = guide_match.group(2).strip()

            # 兜底：如果用户明确问案例但 LLM 没有使用标记，强制附加全部案例
            user_msg_lower = request.message.lower()
            case_keywords = ["案例", "作品", "成功项目", "过往", "看看你们做过", "之前做过", "有什么案例", "展示"]
            if not referenced_cases and any(kw in user_msg_lower for kw in case_keywords):
                referenced_cases = cases_data[:5]  # 附加全部真实案例

            return {"message": clean_reply, "cases": referenced_cases, "guide": guide_info}
    except Exception as e:
        print(f"业务介绍 LLM 调用失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
