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
    reply = """你好！我是 Unique Video AI 的智能助手小U 👋

很高兴为您服务！我们是一家专注于**裸眼3D视觉内容**和**数字艺术创意**的技术公司，服务过众多知名品牌。

我可以帮您：
🛒 **咨询下单** — 告诉我您的需求，我来帮您梳理并创建订单
📋 **查看订单** — 查询您的订单进展和状态
💡 **了解业务** — 为您介绍我们的服务和成功案例

您可以直接告诉我您的需求，或者点击下方的快捷入口开始 😊"""
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
            "你的任务是通过自然对话，逐步收集客户的项目需求信息。\n\n"

            "【你需要收集的完整字段清单（共14项）】\n"
            "★ 核心必问项（这6项务必逐一主动询问，缺一不可）：\n"
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

            "【对话规则 — 严格遵守！】\n"
            "1. 每次回复只问一个问题！绝对不要一次性问两三个。"
            "如果客户的回答包含多个信息，先确认收到，再自然地追问下一个缺失项。"
            "切勿重复问已经问过的问题！\n\n"

            "2. 【触发完成的严格条件】在输出【需求收集完成】之前，"
            "你必须在心里逐项检查核心6项的收集情况：\n"
            "  ✅ 品牌/产品: 是否已知？\n"
            "  ✅ 目标受众: 是否已知？\n"
            "  ✅ 内容需求: 是否已知？\n"
            "  ✅ 投放地点: 是否已知？\n"
            "  ✅ 预算范围: 是否已知？\n"
            "  ✅ 上刊时间: 是否已知？\n"
            "只有当至少5项有了客户的实质性回答后，你才可以输出【需求收集完成】标记。"
            "如果不足5项，你必须继续追问缺失的项目，不要提前结束！\n\n"

            "3. 当你确认满足上述条件后，用热情话语总结已收集的信息，"
            "在回复的最末尾加上标记：【需求收集完成】。\n\n"

            "4. 【被动结束情况】只有当客户明确表达不想继续时（比如'算了''就这样吧''先这样''回头再说''直接填表吧'、语气明显不耐烦），"
            "你才可以提前结束。此时友好总结已收集的信息，告知哪些重要项还缺失，然后加上【需求收集完成】标记。"
            "客户正常回答问题时，绝对不要主动结束！\n\n"

            "5. 保持像真人聊天一样轻松舒缓的节奏，态度专业且热情。"
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


# ===== 意图分类 =====
class ClassifyRequest(BaseModel):
    message: str
    history: list = []

@router.post("/classify")
async def ai_classify(request: ClassifyRequest):
    """对用户消息进行意图分类"""
    # 关键词快速匹配（优先级高于 LLM，节省调用）
    msg = request.message.strip()
    quick_map = {
        "order_query": ["订单", "进度", "状态", "查看", "查询", "我的单", "下过的"],
        "business_intro": ["了解", "介绍", "业务", "案例", "服务", "你们做什么", "什么公司"],
    }
    for intent, keywords in quick_map.items():
        if any(kw in msg for kw in keywords):
            return {"intent": intent}
    
    # 如果没有命中关键词且有 LLM，使用 LLM 分类
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
                valid = ["order_create", "order_query", "business_intro", "general"]
                intent = result if result in valid else "order_create"
                return {"intent": intent}
        except Exception as e:
            print(f"意图分类 LLM 调用失败: {e}")
    
    # 默认当作下单意图
    return {"intent": "order_create"}


# ===== 订单查询 Agent =====
class QueryOrdersRequest(BaseModel):
    message: str
    history: list = []

@router.post("/query-orders")
async def ai_query_orders(request: QueryOrdersRequest, raw_request: Request):
    """在聊天中查询用户订单"""
    from app.database import async_session_maker
    from app.services.order_service import OrderService
    from app.models.user import User
    from sqlalchemy import select
    
    # 鉴权
    user_id = "anonymous"
    auth_header = raw_request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        payload = decode_access_token(auth_header[7:])
        if payload:
            user_id = payload.get("user_id", "anonymous")
    
    if user_id == "anonymous":
        return {
            "message": "抱歉，我需要先确认您的身份才能查询订单。请确保您已登录。",
            "orders": []
        }
    
    # 查询数据库
    orders_data = []
    try:
        async with async_session_maker() as db:
            user_result = await db.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one_or_none()
            if user:
                orders = await OrderService.get_orders(db, user)
                # 只取最近10条
                orders_data = orders[:10]
    except Exception as e:
        print(f"查询订单失败: {e}")
        return {
            "message": "非常抱歉，查询订单时遇到了问题，请稍后再试。",
            "orders": []
        }
    
    if not orders_data:
        return {
            "message": "您目前还没有任何订单记录。如果您有项目需求，我可以帮您快速创建一个订单！只需要告诉我您想做什么样的内容就好 😊",
            "orders": []
        }
    
    # 构建订单摘要给 LLM 生成自然语言描述
    status_map = {
        "draft": "草稿", "pending_assign": "待分配", "in_production": "制作中",
        "pending_review": "待审核", "review_rejected": "审核驳回",
        "preview_ready": "初稿就绪", "final_preview": "终稿就绪",
        "revision_needed": "需修改", "completed": "已完成", "cancelled": "已取消"
    }
    type_map = {
        "video_purchase": "裸眼3D成片购买适配",
        "ai_3d_custom": "AI裸眼3D内容定制",
        "digital_art": "数字艺术内容定制"
    }
    
    summary_lines = []
    for i, o in enumerate(orders_data[:5], 1):
        status_text = status_map.get(o.get("status", ""), o.get("status", ""))
        type_text = type_map.get(o.get("order_type", ""), o.get("order_type", ""))
        order_num = o.get("order_number", "N/A")
        summary_lines.append(f"{i}. 订单号 {order_num} | {type_text} | 状态：{status_text}")
    
    summary = "\n".join(summary_lines)
    message = f"为您查询到 {len(orders_data)} 个订单，以下是最近的记录：\n\n{summary}\n\n如需查看详情，可以告诉我具体的订单号。"
    
    return {
        "message": message,
        "orders": orders_data[:5]
    }



# ===== 案例数据接口 =====
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


# ===== 业务介绍 Agent =====
class BusinessIntroRequest(BaseModel):
    message: str
    history: list = []

@router.post("/business-intro")
async def ai_business_intro(request: BusinessIntroRequest):
    """业务介绍对话"""
    # 从文档动态读取业务配置和真实案例
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
            
        business_knowledge = f"{intro_text}\n{cases_text}"
    except Exception as e:
        print(f"读取业务介绍文件失败: {e}")
        business_knowledge = "暂无法读取详细业务介绍"
    
    if not settings.AI_API_KEY:
        msg = request.message.lower()
        if "案例" in msg or "作品" in msg:
            reply = ("当然！我来分享几个我们的代表性项目 🎬\n\n" +
                     "\n\n".join([f"**{c['title']}**\n{c['description']}" for c in cases_data[:3]]) +
                     "\n\n以上每个案例都有对应的视频展示，您可以直接点击播放！")
            return {"message": reply, "cases": cases_data[:3]}
        elif "裸眼" in msg or "3d" in msg or "成片" in msg:
            reply = ("我们的裸眼3D业务是核心优势！主要分两种模式：\n\n"
                     "1️⃣ **成片购买适配** — 5个工作日交付，预算友好\n\n"
                     "2️⃣ **AI内容定制** — 15个工作日交付，品牌专属\n\n"
                     "您对哪种模式更感兴趣呢？")
            relevant = [c for c in cases_data if c.get("category") == "ai_3d_custom"]
            return {"message": reply, "cases": relevant[:2]}
        elif "数字" in msg or "艺术" in msg:
            reply = ("数字艺术定制是我们另一大热门服务！🎨\n\n"
                     "沉浸式视觉体验，7个工作日交付。")
            relevant = [c for c in cases_data if c.get("category") == "digital_art"]
            return {"message": reply, "cases": relevant[:2]}
        else:
            reply = ("感谢关注！Unique Video AI 三大业务板块 👇\n\n"
                     "🎬 裸眼3D成片购买适配 | 🤖 AI裸眼3D内容定制 | 🎨 数字艺术内容定制\n\n"
                     "想了解哪个板块？或者看看我们的案例？")
            return {"message": reply, "cases": []}
    
    try:
        system_prompt = (
            "你是 Unique Video AI 公司的资深客户经理——小U。\n"
            "你的性格热情阳光专业，把自己当做公司的一员来介绍业务。\n"
            "以下是公司的业务资料，用来回答客户的问题：\n\n"
            f"{business_knowledge}\n\n"
            "【对话规则】\n"
            "1. 根据客户的具体问题，有针对性地介绍对应的服务板块\n"
            "2. 当提及案例时，使用标记格式引用：【推荐案例:case_xxx】（替换为实际的案例ID），系统会自动渲染视频卡片\n"
            "3. 当客户表现出下单意向时，在回复末尾加上标记：【引导下单】\n"
            "4. 保持热情专业、积极阳光的态度\n"
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
            
            # 从回复中提取引用的案例ID
            import re
            referenced_ids = re.findall(r'【推荐案例:(case_\w+)】', reply)
            referenced_cases = [c for c in cases_data if c["id"] in referenced_ids]
            clean_reply = re.sub(r'【推荐案例:case_\w+】', '', reply).strip()
            
            return {"message": clean_reply, "cases": referenced_cases}
    except Exception as e:
        print(f"业务介绍 LLM 调用失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== 通用问答（兜底） =====
@router.post("/general")
async def ai_general(request: ChatRequest, raw_request: Request):
    """通用问答兜底"""
    if not settings.AI_API_KEY:
        reply = (
            "感谢您的提问！我是 Unique Video AI 的智能助手小U 😊\n\n"
            "我们是国内领先的裸眼3D视觉内容服务商，致力于用AI技术为品牌打造震撼的视觉体验。\n\n"
            "我可以帮您：\n"
            "🛒 咨询下单 — 告诉我项目需求，帮您一键创建订单\n"
            "📋 查看订单 — 实时查询订单进展\n"
            "💡 了解业务 — 介绍我们的服务和案例\n\n"
            "请问您想了解哪方面呢？"
        )
        return {"message": reply}
    
    try:
        system_prompt = (
            "你是 Unique Video AI 公司的智能助手小U。\n"
            "你是公司的一员，性格热情阳光专业。公司是国内领先的裸眼3D视觉内容和数字艺术创意技术公司。\n"
            "当用户的问题不属于下单、查订单、了解业务时，你友好地回答，并自然引导用户了解公司业务或开始下单。\n"
            "保持简洁热情，结尾给出下一步建议。"
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
