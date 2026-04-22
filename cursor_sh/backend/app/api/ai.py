"""
AI 智能体 — 主路由入口
保留：需求收集（/chat, /extract, /assess）、初始欢迎（/start）、
      案例数据（/cases）、会话存储工具函数。
其余 Agent 拆分为独立模块并通过 include_router 引入。
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import httpx
import json
import os
from datetime import datetime
from app.config import settings
from app.utils.security import decode_access_token

router = APIRouter(prefix="/ai", tags=["AI 智能体对话"])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 引入独立 Agent 模块
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from app.api.ai_classify import classify_router
from app.api.ai_order_agent import order_router
from app.api.ai_intro_agent import intro_router
from app.api.ai_general_agent import general_router

router.include_router(classify_router)
router.include_router(order_router)
router.include_router(intro_router)
router.include_router(general_router)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 公共数据模型
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ChatRequest(BaseModel):
    session_id: str
    message: str
    history: list = []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 初始欢迎
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/start")
async def ai_start(session_id: str):
    """获取对话的初始欢迎语"""
    reply = """您好，我是 Unique Video AI 的项目顾问。

我们是国内裸眼3D视觉内容与数字艺术创意领域的头部服务商，核心团队深耕行业多年，已为众多一线品牌提供过高品质的视觉解决方案。

您可以通过以下方式开始：

**咨询下单** — 描述您的项目需求，由我协助梳理并生成完整需求单
**查看订单** — 查询您名下的订单进展与状态
**了解业务** — 了解我们的服务体系与过往案例

请直接告知您的需求，或通过下方快捷入口进入对应流程。"""
    return {"reply": reply}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 需求收集 Agent（/chat）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/chat")
async def ai_chat(request: ChatRequest, raw_request: Request):
    """核心聊天接口 — 需求收集对话"""
    user_id = "anonymous"
    username = "anonymous"
    auth_header = raw_request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        payload = decode_access_token(auth_header[7:])
        if payload:
            user_id = payload.get("user_id", "anonymous")
            username = payload.get("username", "anonymous")

    if not settings.AI_API_KEY:
        mock_reply = "【真实后端接口调试中】"
        if "完成" in request.message or "没问题" in request.message:
            mock_reply += "太好了，我已经收集齐了所有核心需求！马上为您生成完整需求单..."
        elif len(request.message) > 5:
            mock_reply += f"收到您的反馈：{request.message[:10]}... 请问这支内容的投放渠道和大概预算是多少？"
        else:
            mock_reply += "好的，请继续详细描述您的诉求。"

        _save_session_file(
            session_id=request.session_id, user_id=user_id, username=username,
            history=request.history, user_msg=request.message, assistant_msg=mock_reply,
        )
        return {"message": mock_reply}

    try:
        system_prompt = (
            "你是 Unique Video AI 的资深项目顾问，专注于裸眼3D视觉内容定制领域。"
            "你的任务是通过结构化的对话，高效地收集客户的项目需求信息。\n\n"

            "【语气要求】\n"
            "- 专业、简练、沉稳，体现行业专家的权威感\n"
            "- 不使用emoji表情符号\n"
            "- 不使用'哦''呢''呀''哈'等语气词\n"
            "- 不说'很高兴''非常感谢'等客套话\n"
            "- 用行业术语体现专业度\n\n"

            "【你需要收集的完整字段清单（共14项）】\n"
            "核心必问项（这6项务必逐一主动询问，缺一不可）：\n"
            "1. 品牌与产品关键词 — 客户的品牌名和要推广的产品\n"
            "2. 目标受众 — 这支内容是给谁看的\n"
            "3. 内容需求 — 客户想要什么样的创意画面和场景\n"
            "4. 投放城市或站点 — 在哪里投放\n"
            "5. 制作预算 — 预算范围\n"
            "6. 预计上刊时间 — 什么时候需要上线\n\n"

            "自然追问项（对话中自然涉及就记录，不必刻意逐个追问）：\n"
            "7. 项目背景 — 为什么要做这个项目\n"
            "8. 品牌调性 — 高端、年轻、科技感等\n"
            "9. 风格偏好 — 赛博朋克、极简、写实等\n"
            "10. 品牌禁忌内容 — 不希望出现的元素\n"
            "11. 投放媒体及尺寸 — 屏幕类型和分辨率\n"
            "12. 投放时长与数量 — 几秒、几条\n"
            "13. 技术需求 — 分辨率、格式等\n\n"

            "【对话规则 — 严格遵守！】\n"
            "1. 每次回复只问一个问题。不要一次性问两三个。"
            "客户回答包含多个信息时，先确认收到，再追问下一个缺失项。"
            "切勿重复问已经问过的问题。\n\n"

            "2. 【触发完成的严格条件】在输出【需求收集完成】之前，"
            "逐项检查核心6项的收集情况：\n"
            "  - 品牌/产品: 是否已知？\n"
            "  - 目标受众: 是否已知？\n"
            "  - 内容需求: 是否已知？\n"
            "  - 投放地点: 是否已知？\n"
            "  - 预算范围: 是否已知？\n"
            "  - 上刊时间: 是否已知？\n"
            "只有当至少5项有了客户的实质性回答后，才可以输出【需求收集完成】标记。"
            "不足5项时必须继续追问。\n\n"

            "3. 满足条件后，简要总结已收集的信息，"
            "在回复的最末尾加上标记：【需求收集完成】。\n\n"

            "4. 【被动结束情况】只有当客户明确表达不想继续时（比如'算了''就这样吧''先这样''回头再说''直接填表吧'），"
            "才可以提前结束。此时总结已收集的信息，指出哪些重要项还缺失，然后加上【需求收集完成】标记。"
            "客户正常回答问题时，不要主动结束。\n\n"

            "5. 保持专业节奏，语言干练精准，不要寒暄客套。"
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

            _save_session_file(
                session_id=request.session_id, user_id=user_id, username=username,
                history=request.history, user_msg=request.message, assistant_msg=reply,
            )
            return {"message": reply}

    except Exception as e:
        print(f"大模型调用失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 需求提取（/extract）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ExtractRequest(BaseModel):
    history: list = []

@router.post("/extract")
async def ai_extract(request: ExtractRequest):
    """从对话历史中提取结构化信息"""
    if not settings.AI_API_KEY:
        return {
            "brand": "示例品牌 (Mock)",
            "target_group": "年轻群体",
            "style": "科技感设计",
            "budget": "10万以上"
        }

    try:
        system_prompt = (
            "你是一个数据提取专家。请阅读以下对话记录，提取客户的项目需求信息。\n"
            "将提取的信息整理为严格的 JSON 格式返回，只返回 JSON，不要任何其他废话。\n"
            "支持的字段名（如果有对应信息则提取，没有则留空字符串）：\n"
            "brand, background, target_group, brand_tone, content, style, prohibited_content, "
            "city, media_size, time_number, technology, budget, online_time."
        )

        chat_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in request.history])

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
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"对话记录如下：\n{chat_text}\n\n请提取为JSON。"}
                    ],
                    "response_format": {"type": "json_object"}
                },
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]

            if content.startswith("```json"):
                content = content.split("```json")[-1].split("```")[0].strip()
            elif content.startswith("```"):
                content = content.split("```")[-1].split("```")[0].strip()

            parsed = json.loads(content)
            return parsed

    except Exception as e:
        print(f"提取信息失败: {e}")
        return {}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 项目评估（/assess）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class AssessRequest(BaseModel):
    extracted: dict = {}

@router.post("/assess")
async def ai_assess(request: AssessRequest):
    """根据提取的需求数据生成专业项目评估"""
    d = request.extracted
    brand = d.get("brand", "")
    content_desc = d.get("content", "")
    city = d.get("city", "")
    budget = d.get("budget", "")
    online_time = d.get("online_time", "")
    style = d.get("style", "")

    if not settings.AI_API_KEY:
        has_custom_need = bool(content_desc) or bool(style)
        if budget and ("万" in budget):
            try:
                num = int(''.join(filter(str.isdigit, budget.split("万")[0])))
                recommend_mode = "AI裸眼3D内容定制" if num >= 8 else "裸眼3D成片购买适配"
                timeline = "约15个工作日" if num >= 8 else "约5个工作日"
            except Exception:
                recommend_mode = "AI裸眼3D内容定制" if has_custom_need else "裸眼3D成片购买适配"
                timeline = "约15个工作日" if has_custom_need else "约5个工作日"
        else:
            recommend_mode = "AI裸眼3D内容定制" if has_custom_need else "裸眼3D成片购买适配"
            timeline = "约15个工作日" if has_custom_need else "约5个工作日"

        assessment = f"**项目评估**\n\n"
        assessment += f"根据您提供的需求信息，初步评估如下：\n\n"
        assessment += f"- **推荐方案**：{recommend_mode}\n"
        assessment += f"- **预计制作周期**：{timeline}\n"
        if budget:
            assessment += f"- **预算匹配度**：{budget} 在该类型项目中属合理区间\n"
        if city:
            assessment += f"- **投放区域**：{city}，我们在该区域有成熟的媒体资源与执行经验\n"
        if online_time:
            assessment += f"- **上线节点**：{online_time}，建议提前2-3个工作日完成终稿交付以预留调试时间\n"
        assessment += f"\n以下是整理后的需求明细，请确认或修改："

        return {"assessment": assessment}

    try:
        system_prompt = (
            "你是一位资深的裸眼3D视觉项目顾问。根据以下客户需求信息，给出简洁专业的项目评估。\n"
            "评估应包含：推荐方案（成片购买适配 / AI内容定制 / 数字艺术定制）、预计制作周期、"
            "预算合理性分析、投放建议、时间节点建议。\n"
            "语气专业沉稳，不用emoji，不寒暄，用要点式列出。\n"
            "最后一行固定写：\n以下是整理后的需求明细，请确认或修改：\n"
        )

        info = "\n".join([f"{k}: {v}" for k, v in d.items() if v])

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
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"客户需求信息：\n{info}"}
                    ]
                },
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            assessment = data["choices"][0]["message"]["content"]
            return {"assessment": assessment}
    except Exception as e:
        print(f"项目评估生成失败: {e}")
        return {"assessment": "**项目评估**\n\n需求信息已整理完毕。以下是需求明细，请确认或修改："}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 案例数据接口
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/cases")
async def ai_get_cases(category: str = None):
    """获取案例列表（含视频链接）"""
    try:
        cases_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'cases.json')
        with open(cases_path, "r", encoding="utf-8") as f:
            cases = json.load(f)
        if category:
            cases = [c for c in cases if c.get("category") == category]
        return {"cases": cases}
    except Exception as e:
        print(f"读取案例数据失败: {e}")
        return {"cases": []}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 会话存储工具
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _save_session_file(
    session_id: str,
    user_id: str,
    username: str,
    history: list,
    user_msg: str,
    assistant_msg: str,
):
    """将完整的 AI 对话 session 保存为 JSON 文件

    文件结构：
    logs/ai_sessions/
    └── {user_id}/
        └── {session_id}.json
    """
    try:
        full_messages = []
        for h in history:
            if h.get("role") in ["user", "assistant"] and h.get("content"):
                full_messages.append({
                    "role": h["role"],
                    "content": h["content"],
                    "timestamp": h.get("timestamp", ""),
                })

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_messages.append({"role": "user", "content": user_msg, "timestamp": now})
        full_messages.append({"role": "assistant", "content": assistant_msg, "timestamp": now})

        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "username": username,
            "message_count": len(full_messages),
            "created_at": full_messages[0].get("timestamp", now) if full_messages else now,
            "updated_at": now,
            "messages": full_messages,
        }

        session_dir = os.path.join(settings.LOG_DIR, "ai_sessions", user_id)
        os.makedirs(session_dir, exist_ok=True)

        filepath = os.path.join(session_dir, f"{session_id}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"AI 会话保存失败: {e}")
