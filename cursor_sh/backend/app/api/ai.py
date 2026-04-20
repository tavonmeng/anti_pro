from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import httpx
import json
import os
from datetime import datetime
from app.config import settings
from app.utils.security import decode_access_token

router = APIRouter(prefix="/ai", tags=["AI 智能体对话"])

class ChatRequest(BaseModel):
    session_id: str
    message: str
    history: list = []

@router.get("/start")
async def ai_start(session_id: str):
    """获取对话的初始欢迎语"""
    # 使用带有温度和友好的自定义话术
    reply = """你好！我是您的项目需求AI助手 👋

你可以直接告诉我你的项目想法，不用担心格式——哪怕只是一段随意的描述，比如：

> "我们是一个运动饮料品牌，想在今年夏天做一波地铁广告投放，主要面向年轻白领..."

我会从你的描述里提取需要的信息，然后针对还不清楚的地方，我们会一个个讨论 😊

**所以，先告诉我你的项目是什么吧？**"""
    return {"reply": reply}

@router.post("/chat")
async def ai_chat(request: ChatRequest, raw_request: Request):
    """核心聊天接口"""
    # 提取用户信息（用于会话文件归档）
    user_id = "anonymous"
    username = "anonymous"
    auth_header = raw_request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        payload = decode_access_token(auth_header[7:])
        if payload:
            user_id = payload.get("user_id", "anonymous")
            username = payload.get("username", "anonymous")

    # 如果系统没有配置大模型的 KEY，先使用高级模拟测试逻辑
    if not settings.AI_API_KEY:
        mock_reply = "【真实后端接口调试中】"
        if "完成" in request.message or "没问题" in request.message:
            mock_reply += "太好了，我已经收集齐了所有核心需求！马上为您生成完整需求单..."
        elif len(request.message) > 5:
            mock_reply += f"收到您的反馈：{request.message[:10]}... 请问这支内容的投放渠道和大概预算是多少？"
        else:
            mock_reply += "好的，请继续详细描述您的诉求。"
            
        # 保存会话记录
        _save_session_file(
            session_id=request.session_id,
            user_id=user_id,
            username=username,
            history=request.history,
            user_msg=request.message,
            assistant_msg=mock_reply,
        )
        return {"message": mock_reply}

        
    try:
        # 构建历史对话上下文
        system_prompt = (
            "你是一位专业的 3D 视觉内容定制服务 AI 助理。"
            "你的任务是通过自然对话，尽可能多地收集客户的项目需求信息。\n\n"

            "【你需要收集的完整字段清单（共14项）】\n"
            "★ 核心必问项（这6项务必主动询问）：\n"
            "1. 品牌与产品关键词 — 客户的品牌名和要推广的产品\n"
            "2. 目标受众 — 这支内容是给谁看的\n"
            "3. 内容需求 — 客户想要什么样的创意画面和场景\n"
            "4. 投放城市或站点 — 在哪里投放\n"
            "5. 制作预算 — 预算范围\n"
            "6. 预计上刊时间 — 什么时候需要上线\n\n"

            "☆ 自然追问项（对话中自然涉及就记录，不必刻意逐个追问）：\n"
            "7. 项目背景 — 为什么要做这个项目\n"
            "8. 品牌调性 — 高端、年轻、科技感等\n"
            "9. 风格偏好 — 赛博朋克、极简、写实等\n"
            "10. 品牌禁忌内容 — 不希望出现的元素\n"
            "11. 投放媒体及尺寸 — 屏幕类型和分辨率\n"
            "12. 投放时长与数量 — 几秒、几条\n"
            "13. 技术需求 — 分辨率、格式等\n\n"

            "【对话规则】\n"
            "1. 每次回复只问一个问题！绝对不要一次性问两三个。"
            "如果客户的回答包含多个信息，先确认收到，再自然地追问下一个缺失项。"
            "切勿重复问已经问过的问题！\n"
            "2. 当你判断核心6项已基本收集完毕（不需要全部14项都齐），"
            "用热情话语总结已收集的信息，并在回复最后加上标记：【需求收集完成】。"
            "这将触发前端自动建单，未收集到的项目客户可以在表单中手动补充。\n"
            "3. 如果客户表达出不想继续沟通的意愿（比如'算了'、'就这样吧'、'先这样'、"
            "'回头再说'、'直接填表吧'、语气不耐烦等），"
            "你必须立即停止追问，友好总结目前已收集的信息，"
            "告知哪些重要项还缺失需要在表单中补充，然后同样加上【需求收集完成】标记。"
            "绝对不要强留客户！\n"
            "4. 保持像真人聊天一样轻松舒缓的节奏，态度专业且热情。"
        )

        llm_messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # 提取过去的历史轮次
        for h in request.history:
            if h.get("role") in ["user", "assistant"] and h.get("content"):
                llm_messages.append({"role": h["role"], "content": h["content"]})
                
        # 追加本次的新消息
        llm_messages.append({"role": "user", "content": request.message})

        # 这里是一套标准的调用大模型（兼容OpenAI接口规范）的代码
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.AI_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.AI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": settings.AI_MODEL_NAME,
                    "messages": llm_messages
                },
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            reply = data["choices"][0]["message"]["content"]
            
            # 保存会话记录
            _save_session_file(
                session_id=request.session_id,
                user_id=user_id,
                username=username,
                history=request.history,
                user_msg=request.message,
                assistant_msg=reply,
            )
            return {"message": reply}

            
    except Exception as e:
        print(f"大模型调用失败: {e}")
        # 抛出异常，前端会自动切回 fallback
        raise HTTPException(status_code=500, detail=str(e))


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
        # 构建完整的对话历史（原有 history + 本次交互）
        full_messages = []
        for h in history:
            if h.get("role") in ["user", "assistant"] and h.get("content"):
                full_messages.append({
                    "role": h["role"],
                    "content": h["content"],
                    "timestamp": h.get("timestamp", ""),
                })
        
        # 追加本次的新对话
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
        
        # 确保目录存在
        session_dir = os.path.join(settings.LOG_DIR, "ai_sessions", user_id)
        os.makedirs(session_dir, exist_ok=True)
        
        # 写入 JSON 文件（覆写模式，保持为最新状态）
        filepath = os.path.join(session_dir, f"{session_id}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        # 会话保存失败不影响主业务
        print(f"AI 会话保存失败: {e}")

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
            
            import json
            # 简单的清洗，如果有 markdown 格式
            if content.startswith("```json"):
                content = content.split("```json")[-1].split("```")[0].strip()
            elif content.startswith("```"):
                content = content.split("```")[-1].split("```")[0].strip()
                
            parsed = json.loads(content)
            return parsed
            
    except Exception as e:
        print(f"提取信息失败: {e}")
        return {}
