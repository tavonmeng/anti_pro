"""
AI 智能体 — 主路由入口
保留：需求收集（/chat, /extract, /assess）、初始欢迎（/start）、
      案例数据（/cases）、会话存储工具函数。
其余 Agent 拆分为独立模块并通过 include_router 引入。
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import httpx
import asyncio
import json
import os
import re
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from app.config import settings
from app.services.ai_client import (
    post_chat_completion,
    should_use_responses_api,
    stream_chat_completion,
    stream_chat_completion_events,
    stream_responses_completion,
)
from app.services.platform_service_catalog import (
    get_business_type_label,
    get_consultation_intro,
    is_consultation_business_type,
)
from app.utils.business_log import log_business_event
from app.utils.log_setup import get_module_logger
from app.utils.security import decode_access_token

router = APIRouter(prefix="/ai", tags=["AI 智能体对话"])
logger = get_module_logger("ai")


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
    history: list = Field(default_factory=list)
    business_type: str = "ai_3d_custom"
    user_message_id: str | None = None
    assistant_message_id: str | None = None


def _strip_completion_marker(message: str) -> str:
    return message.replace("【需求收集完成】", "").strip()


def _substantive_user_message_count(history: list, latest_message: str = "") -> int:
    """Count user answers that can carry requirement information."""
    user_messages = [
        (m.get("content") or "").strip()
        for m in (history or [])
        if m.get("role") == "user" and (m.get("content") or "").strip()
    ]
    if latest_message and latest_message.strip():
        user_messages.append(latest_message.strip())

    ignored = {"你好", "您好", "hi", "hello", "下单", "咨询下单", "开始", "好的", "是的", "嗯", "好"}
    return sum(1 for text in user_messages if text.lower() not in ignored and len(text) >= 2)


def _has_media_completion_floor(history: list, latest_message: str = "") -> bool:
    """Keep media-mode completion from firing before enough real answers exist."""
    return _substantive_user_message_count(history, latest_message) >= 7


def _has_media_upload_wrap_up(history: list) -> bool:
    """Completion should happen only after the agent has asked the final asset question."""
    upload_keywords = ("现场实拍图", "屏幕照片", "参考素材", "上传按钮", "上传文件")
    return any(
        m.get("role") == "assistant" and any(keyword in (m.get("content") or "") for keyword in upload_keywords)
        for m in (history or [])
    )


def _fallback_extract_media(history: list) -> dict:
    """Best-effort deterministic extraction when the LLM extraction call times out."""
    messages = [
        (m.get("role") or "", (m.get("content") or "").strip())
        for m in (history or [])
        if (m.get("content") or "").strip()
    ]
    text = "\n".join(content for _, content in messages)
    user_text = "\n".join(content for role, content in messages if role == "user")

    def contains(pattern: str, source: str = text) -> bool:
        return re.search(pattern, source, re.I) is not None

    city_location = ""
    if "杭州" in text:
        if "钱江新城万象城天幕" in text:
            city_location = "杭州钱江新城万象城天幕"
        elif "天幕" in text:
            city_location = "杭州天幕巨屏"
        else:
            city_location = "杭州"

    audience_scene = ""
    audience_match = re.search(r"面向([^，。\n]+)", user_text)
    if audience_match:
        audience_scene = f"面向{audience_match.group(1).strip()}"

    theme_parts = []
    if "西湖" in text:
        theme_parts.append("杭州西湖美景")
    if "标志性" in text:
        theme_parts.append("西湖标志性景观")
    theme_concept = "，".join(dict.fromkeys(theme_parts))

    art_direction = ""
    if contains(r"写意|传统意境|水墨"):
        art_direction = "写意的传统意境"
    elif contains(r"未来科技|科技感"):
        art_direction = "未来科技"
    elif contains(r"自然生态|自然"):
        art_direction = "自然生态"

    timing_number = ""
    duration_match = re.search(r"(\d{1,3})\s*(?:s|秒)", user_text, re.I)
    if duration_match:
        timing_number = f"{duration_match.group(1)}秒"

    online_time = ""
    if "下个月" in user_text and "月底" in user_text:
        now = datetime.now()
        year = now.year + (1 if now.month == 12 else 0)
        month = 1 if now.month == 12 else now.month + 1
        online_time = f"{year}年{month}月底"
    elif "下个月" in user_text:
        online_time = "下个月"

    media_specs = ""
    specs_match = re.search(r"(\d{3,5})\s*[×xX*]\s*(\d{3,5})", text)
    if specs_match:
        media_specs = f"{specs_match.group(1)}×{specs_match.group(2)}"
        if "天幕" in text or "超宽幅" in text:
            media_specs += " 超宽幅天幕"

    viewing_path = ""
    if "地面仰视" in text or "二层连廊平视" in text:
        viewing_path = "地面仰视与二层连廊平视双视角"

    resource_background = ""
    if "钱江新城万象城天幕" in text:
        resource_background = "杭州钱江新城万象城天幕，超宽幅屏幕资源，位于主广场中轴高人流区"

    tech_delivery = ""
    if "没有特定的要求" in user_text:
        tech_delivery = "客户无特定技术要求，可按媒体方原生参数与常规安全区规范适配"

    project_name = ""
    if city_location or theme_concept:
        name_parts = []
        if "钱江新城万象城" in city_location:
            name_parts.append("杭州钱江新城万象城")
        elif "杭州" in city_location:
            name_parts.append("杭州")
        if "西湖" in theme_concept:
            name_parts.append("西湖美景")
        name_parts.append("裸眼3D天幕项目")
        project_name = "".join(name_parts)

    result = {
        "project_name": project_name,
        "resource_background": resource_background,
        "audience_scene": audience_scene,
        "media_positioning": "游客宣传与文旅形象传播" if "游客" in text or "宣传" in text else "",
        "city_location": city_location,
        "viewing_path": viewing_path,
        "art_direction": art_direction,
        "theme_concept": theme_concept,
        "media_specs": media_specs,
        "timing_number": timing_number,
        "tech_delivery": tech_delivery,
        "content_review": "",
        "budget": "",
        "online_time": online_time,
        "special_requirements": "",
        "site_photos": "",
        "remarks": "",
    }
    return {key: value for key, value in result.items() if value}


_HUMAN_HANDOFF_MARKER = "【转人工】"

_HUMAN_HANDOFF_REPLY = (
    "已收到您的诉求。我会先把当前已经沟通的项目信息整理并保存到草稿箱，同时转入人工项目顾问跟进。\n\n"
    "专属顾问会根据当前聊天记录继续对接。"
)

_HUMAN_HANDOFF_APPEND_REPLY = "已收到，我已将这条补充内容追加到人工对接记录中，专属顾问跟进时会一并查看。"


def _handoff_reply_for_business_type(business_type: str) -> str:
    if is_consultation_business_type(business_type):
        label = get_business_type_label(business_type)
        return f"已收到，我已把您关于「{label}」的咨询内容和聊天记录同步给后台项目顾问。\n\n专属顾问会继续跟进需求、报价和排期。"
    return _HUMAN_HANDOFF_REPLY


def _is_human_handoff_request(message: str) -> bool:
    """识别用户明确希望停止 AI 引导并转人工的表达。"""
    text = re.sub(r"\s+", "", (message or "").lower())
    if not text:
        return False

    negative_patterns = [
        "不需要人工", "不用人工", "无需人工", "不要人工", "别转人工",
        "不转人工", "暂不转人工", "先不转人工", "不是要人工", "不是找人工",
        "不是转人工", "不用真人", "不需要真人",
    ]
    if any(pattern in text for pattern in negative_patterns):
        return False

    handoff_text = text.replace("人工智能", "")

    explicit_patterns = [
        "转人工", "接人工", "切人工", "换人工", "找人工", "人工客服",
        "人工服务", "人工顾问", "人工接待", "真人客服", "真人顾问",
        "真人服务", "找真人", "联系人工", "联系顾问", "联系销售",
        "客服介入", "销售联系", "顾问联系", "人工",
    ]
    if any(pattern in handoff_text for pattern in explicit_patterns):
        return True

    no_ai_patterns = [
        "不想用ai", "不使用ai", "不用ai", "不要ai", "别用ai",
        "不想用智能体", "不使用智能体", "不用智能体", "不要智能体", "别用智能体",
        "不想和机器人聊", "不跟机器人聊", "不要机器人", "不用机器人",
        "不想和agent聊", "不用agent", "不要agent",
    ]
    return any(pattern in text for pattern in no_ai_patterns)


async def _record_handoff(
    *,
    user_id: str,
    username: str,
    session_id: str,
    business_type: str,
    history: list,
    user_msg: str,
    assistant_msg: str,
) -> dict:
    from app.services.human_handoff_service import record_handoff

    return await record_handoff(
        user_id=user_id,
        username=username,
        session_id=session_id,
        business_type=business_type,
        history=history,
        user_msg=user_msg,
        assistant_msg=assistant_msg,
    )


async def _append_handoff_message(
    *,
    user_id: str,
    username: str,
    session_id: str,
    business_type: str,
    history: list,
    user_msg: str,
    assistant_msg: str,
) -> dict | None:
    from app.services.human_handoff_service import append_handoff_message

    return await append_handoff_message(
        user_id=user_id,
        username=username,
        session_id=session_id,
        business_type=business_type,
        history=history,
        user_msg=user_msg,
        assistant_msg=assistant_msg,
    )


def _uploaded_file_names(message: str) -> list[str]:
    names: list[str] = []
    for match in re.findall(r"\[已上传文件:\s*([^\]]+)\]", message or ""):
        names.extend([item.strip() for item in re.split(r"[、,，]", match) if item.strip()])
    for match in re.findall(r"\[已上传\s*\d+\s*个文件:\s*([^\]]+)\]", message or ""):
        names.extend([item.strip() for item in re.split(r"[、,，]", match) if item.strip()])
    return list(dict.fromkeys(names))


def _sanitize_upload_reply(current_message: str, reply: str) -> str:
    """文件上传消息只带文件名时，避免模型假装看过图片内容。"""
    file_names = _uploaded_file_names(current_message)
    if not file_names:
        return reply

    visual_claims = [
        "从画面可见", "从图片可见", "从照片可见", "画面可见", "图片中", "照片中",
        "图中", "画面中", "可以看到", "可见屏幕", "左右有", "前方为", "遮挡区",
    ]
    if not any(claim in reply for claim in visual_claims):
        return reply

    file_label = "、".join(file_names)
    return (
        f"已收到您上传的现场实拍图（{file_label}），我会把它作为本次项目的现场参考素材一并整理。\n\n"
        "还有其他现场照片、屏幕参数文件或参考素材需要一起上传吗？如果没有，我们可以继续把剩下的信息补齐。"
    )


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _build_requirement_llm_messages(request: ChatRequest, memory_context: str = "") -> list[dict[str, str]]:
    system_prompt = _get_requirement_prompt(request.business_type)
    if memory_context:
        system_prompt += memory_context

    llm_messages = [{"role": "system", "content": system_prompt}]
    for h in request.history:
        if h.get("role") in ["user", "assistant"] and h.get("content"):
            llm_messages.append({"role": h["role"], "content": h["content"]})
    llm_messages.append({"role": "user", "content": request.message})
    return llm_messages


def _build_responses_input(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {"role": item["role"], "content": item["content"]}
        for item in messages
        if item.get("role") and item.get("content")
    ]


def _should_enable_design_thinking(message: str) -> bool:
    """Only enable Qwen thinking for explicit creative/design plan generation."""
    text = re.sub(r"\s+", "", (message or "").lower())
    if not text:
        return False

    excluded_keywords = [
        "排期", "报价", "预算", "可行", "能不能做", "能做吗",
        "怎么落地", "怎么执行", "周期", "多久", "合同",
    ]
    if any(keyword in text for keyword in excluded_keywords):
        return False

    design_plan_keywords = [
        "设计方案", "策划方案", "创意方案", "视觉方案", "内容方案",
        "设计提案", "创意提案", "视觉提案", "内容策划",
        "帮我设计方案", "帮我策划方案", "生成设计", "生成策划",
        "写个设计方案", "写一版设计方案", "写个策划方案", "写一版策划方案",
        "出个设计方案", "出个策划方案",
    ]
    return any(keyword in text for keyword in design_plan_keywords)


async def _finalize_ai_chat_reply(
    *,
    request: ChatRequest,
    user_id: str,
    username: str,
    reply: str,
) -> tuple[str, bool, dict]:
    if settings.AGENT_MODE == "media":
        reply = _sanitize_upload_reply(request.message, reply)
        if "【需求收集完成】" in reply and (
            not _has_media_completion_floor(request.history, request.message)
            or not _has_media_upload_wrap_up(request.history)
        ):
            log_business_event(
                logger,
                "ai_completion_marker_stripped",
                level="warning",
                user_id=user_id,
                username=username,
                session_id=request.session_id,
                business_type=request.business_type,
                substantive_user_count=_substantive_user_message_count(request.history, request.message),
                has_upload_wrap_up=_has_media_upload_wrap_up(request.history),
            )
            reply = _strip_completion_marker(reply) + "\n\n我还需要再补充一个关键信息：您这边是否有现场实拍图、屏幕照片或其他参考素材可以上传？如果暂时没有，也可以直接说明没有。"

    handoff = _HUMAN_HANDOFF_MARKER in reply
    if handoff:
        reply = reply.replace(_HUMAN_HANDOFF_MARKER, "").strip()

    handoff_meta = {}
    if handoff:
        handoff_meta = await _record_handoff(
            user_id=user_id,
            username=username,
            session_id=request.session_id,
            business_type=request.business_type,
            history=request.history,
            user_msg=request.message,
            assistant_msg=reply,
        )
        log_business_event(
            logger,
            "ai_handoff_triggered",
            user_id=user_id,
            username=username,
            session_id=request.session_id,
            business_type=request.business_type,
            trigger_source="llm_marker",
            handoff_id=handoff_meta.get("handoff_id"),
            draft_order_id=handoff_meta.get("draft_order_id"),
            history_count=len(request.history or []),
        )

    _save_session_file(
        session_id=request.session_id, user_id=user_id, username=username,
        history=request.history, user_msg=request.message, assistant_msg=reply,
        business_type=request.business_type,
        user_message_id=request.user_message_id,
        assistant_message_id=request.assistant_message_id,
    )

    if user_id != "anonymous":
        try:
            from app.services.memory_service import learn_from_conversation
            full_conversation = []
            for h in request.history:
                if h.get("role") in ["user", "assistant"] and h.get("content"):
                    full_conversation.append({"role": h["role"], "content": h["content"]})
            full_conversation.append({"role": "user", "content": request.message})
            full_conversation.append({"role": "assistant", "content": reply})
            asyncio.create_task(learn_from_conversation(user_id, full_conversation))
        except Exception:
            pass

    log_business_event(
        logger,
        "ai_chat_completed",
        user_id=user_id,
        username=username,
        session_id=request.session_id,
        business_type=request.business_type,
        handoff=handoff,
        handoff_id=handoff_meta.get("handoff_id"),
        draft_order_id=handoff_meta.get("draft_order_id"),
        history_count=len(request.history or []),
        reply_length=len(reply or ""),
    )
    return reply, handoff, handoff_meta


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 初始欢迎
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/start")
async def ai_start(session_id: str, business_type: str | None = None):
    """获取对话的初始欢迎语"""
    if business_type:
        business_labels = {
            "ai_3d_custom": "AI驱动3D OOH内容定制",
            "video_purchase": "3D OOH数字内容资源库",
            "digital_art": "数字艺术与沉浸式视觉设计",
        }
        label = business_labels.get(business_type, business_labels["ai_3d_custom"])
        if business_type == "video_purchase":
            reply = (
                f"好的，我们进入「{label}」需求梳理。\n\n"
                "我会先确认品牌、内容使用场景、屏幕规格和期望上线时间。"
                "请先告诉我品牌名称。"
            )
        elif business_type == "digital_art":
            reply = (
                f"好的，我们进入「{label}」需求梳理。\n\n"
                "我会先确认项目场景、空间条件、艺术方向和交付要求。"
                "请先告诉我项目或活动名称。"
            )
        else:
            reply = (
                f"好的，我们进入「{label}」需求梳理。\n\n"
                "我会按项目基础信息、创意方向、投放场景和技术交付逐步确认。"
                "请先告诉我品牌或项目名称。"
            )
        return {"reply": reply, "agent_mode": settings.AGENT_MODE, "business_type": business_type}

    if settings.AGENT_MODE == "media":
        reply = """您好，我是 Unique Vision AI 的项目顾问。

我们是国内裸眼3D视觉内容与数字艺术创意领域的头部服务商，核心团队深耕行业多年，已为众多媒体方客户提供过高品质的裸眼3D视觉内容解决方案。

您可以通过以下方式开始：

**咨询下单** — 描述您的媒体资源与项目需求，由我协助梳理并生成完整需求单
**查看订单** — 查询您名下的订单进展与状态
**了解业务** — 了解我们的服务体系与过往案例

请直接告知您的需求，或通过下方快捷入口进入对应流程。"""
    else:
        reply = """您好，我是 Unique Vision AI 的项目顾问。

我们是国内裸眼3D视觉内容与数字艺术创意领域的头部服务商，核心团队深耕行业多年，已为众多一线品牌提供过高品质的视觉解决方案。

您可以通过以下方式开始：

**咨询下单** — 描述您的项目需求，由我协助梳理并生成完整需求单
**查看订单** — 查询您名下的订单进展与状态
**了解业务** — 了解我们的服务体系与过往案例

请直接告知您的需求，或通过下方快捷入口进入对应流程。"""
    return {"reply": reply, "agent_mode": settings.AGENT_MODE}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 需求收集 Prompt 模板（按业务类型）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_TONE_RULES = (
    "【语气要求】\n"
    "- 专业、简练、沉稳，体现行业专家的权威感\n"
    "- 不使用emoji表情符号\n"
    "- 不使用'哦''呢''呀''哈'等语气词\n"
    "- 不说'很高兴''非常感谢'等客套话\n"
    "- 用行业术语体现专业度\n\n"
)

_DIALOG_RULES = (
    "【对话规则 — 严格遵守！】\n"
    "1. 每次回复只问一个问题。不要一次性问两三个。"
    "客户回答包含多个信息时，先确认收到，再追问下一个缺失项。"
    "切勿重复问已经问过的问题。\n\n"

    "2. 【默认追问顺序】按以下业务节奏推进："
    "品牌/项目基础信息 → 目标受众/活动场景 → 内容创意方向 → 投放城市/站点/场地 → "
    "屏幕规格/技术交付 → 预计上刊或活动时间 → 预算范围 → 现场实拍图/参考素材。"
    "如果客户提前给出了后续信息，直接记录，下一轮追问最靠前的缺失项。\n\n"

    "3. 【预算靠后】制作预算属于敏感信息，尽量在内容、投放、技术和时间节点基本明确后再问。"
    "询问时说明用途：用于匹配制作方案和交付配置。\n\n"

    "4. 【触发完成的严格条件】在输出【需求收集完成】之前，"
    "逐项检查核心必问项的收集情况。"
    "只有当至少5项有了客户的实质性回答后，才可以输出【需求收集完成】标记。"
    "不足5项时必须继续追问。除非客户明确不想继续，否则必须完成最后的素材上传收尾问题后再结束。\n\n"

    "5. 满足条件后，简要总结已收集的信息，"
    "在回复的最末尾加上标记：【需求收集完成】。\n\n"

    "6. 【被动结束情况】只有当客户明确表达不想继续时（比如'算了''就这样吧''先这样''回头再说''直接填表吧'），"
    "才可以提前结束。此时总结已收集的信息，指出哪些重要项还缺失，然后加上【需求收集完成】标记。"
    "客户正常回答问题时，不要主动结束。\n\n"

    "7. 【转人工】如果客户明确表示不想使用 AI、想找人工/真人/客服/销售/项目顾问，"
    "立即停止继续追问需求，不要输出【需求收集完成】，不要生成表单总结。"
    "只需简短确认已为其转入人工项目顾问处理，并在回复末尾加上标记：【转人工】。\n\n"

    "8. 保持专业节奏，语言干练精准，不要寒暄客套。\n\n"

    "9. 【上传环节放在最后】文件上传（现场实拍图/参考文件）是需求收集的最后一步。"
    "在核心业务信息都已收集之后，再主动询问客户是否有现场实拍图或参考文件需要上传。"
    "告知客户：'核心需求信息已基本收集完毕。最后一步——如果您有现场实拍图、屏幕照片或其他参考素材，"
    "可以通过输入框左侧的上传按钮直接上传。如果暂时没有，我们就可以整理信息了。'\n\n"

    "10. 【文件上传确认】当客户上传了文件（消息中包含'已上传文件'或'已上传'字样）时，"
    "先确认收到文件，然后询问是否还有其他文件需要上传。"
    "如果客户表示没有更多文件了，直接总结所有已收集的信息并输出【需求收集完成】标记。"
    "示例回复：'已收到您上传的文件。请问还有其他参考素材需要上传吗？没有的话，我来为您整理需求信息。'\n\n"

    "11. 如果客户提供的补充内容无法归入上述任何结构化字段，将其完整记录，"
    "在最终提取时归入'备注'字段，确保不遗漏任何客户诉求。"
)

_PROMPT_AI_3D = (
    "你是 Unique Vision AI 的资深项目顾问，专注于AI驱动3D OOH内容定制领域。"
    "你的任务是通过结构化的对话，高效地收集客户的裸眼3D项目需求信息。\n\n"
    + _TONE_RULES +
    "【你需要收集的字段清单】\n"
    "核心必问项（前6项务必逐一主动询问，缺一不可；第7项为收尾确认）：\n"
    "1. 品牌与产品关键词 — 客户的品牌名和要推广的产品\n"
    "2. 目标受众 — 这支内容是给谁看的\n"
    "3. 内容需求 — 客户想要什么样的裸眼3D创意画面和场景\n"
    "4. 投放城市或站点 — 在哪个城市/哪块屏投放\n"
    "5. 预计上刊时间 — 什么时候需要上线\n"
    "6. 制作预算 — 预算范围（参考：十万级起步，放在时间节点之后再问）\n"
    "7. 现场实拍图 — 主动询问客户是否有现场实拍图或其他相关参考文件可以提供（如投放屏幕实景照片、场地照片等），告知客户可以通过输入框左侧的上传按钮直接上传图片或文件。此项为选填，客户可以跳过。\n\n"
    "自然追问项（对话中自然涉及就记录，不必刻意逐个追问）：\n"
    "8. 项目背景 — 为什么要做这个项目\n"
    "9. 品牌调性 — 高端、年轻、科技感等\n"
    "10. 风格偏好 — 赛博朋克、极简、写实等\n"
    "11. 品牌禁忌内容 — 不希望出现的元素\n"
    "12. 投放媒体及尺寸 — 屏幕类型和分辨率\n"
    "13. 投放时长与数量 — 几秒、几条\n"
    "14. 技术需求 — 分辨率、格式等\n\n"
    + _DIALOG_RULES
)

_PROMPT_VIDEO_PURCHASE = (
    "你是 Unique Vision AI 的资深项目顾问，专注于3D OOH数字内容资源库服务。"
    "你的任务是通过结构化的对话，高效地收集客户的成片选购与适配需求。\n\n"
    "【业务背景】\n"
    "3D OOH数字内容资源库是从我们的精选模板库中挑选现成的裸眼3D视频，"
    "再根据客户的屏幕尺寸和品牌需求进行适配调整。交付周期约5个工作日，预算万元级。\n\n"
    + _TONE_RULES +
    "【你需要收集的字段清单】\n"
    "核心必问项（前6项务必逐一主动询问，缺一不可；第7项为收尾确认）：\n"
    "1. 品牌名称 — 客户的品牌，用于在成片上叠加品牌元素\n"
    "2. 内容偏好 — 客户喜欢什么风格/主题的成片（科技感、自然、动物、抽象等）\n"
    "3. 投放城市与屏幕位置 — 在哪个城市/哪块屏投放\n"
    "4. 屏幕尺寸与分辨率 — 具体的屏幕物理尺寸和分辨率（如 LED 大屏 16:9 等）\n"
    "5. 预计上刊时间 — 什么时候需要投放\n"
    "6. 制作预算 — 预算范围（参考：万元级，放在时间节点之后再问）\n"
    "7. 现场实拍图 — 最后主动询问客户是否有现场实拍图或参考文件（如屏幕实景照片等），告知可以通过输入框左侧的上传按钮上传。此项选填，可跳过。\n\n"
    "自然追问项（对话中自然涉及就记录）：\n"
    "8. 投放时长 — 每条视频多少秒\n"
    "9. 购买数量 — 需要几条不同的成片\n"
    "10. 品牌定制需求 — 是否需要在成片上叠加 logo、slogan、产品画面等\n"
    "11. 投放场景 — 户外地标屏、商场内屏、交通枢纽等\n\n"
    + _DIALOG_RULES
)

_PROMPT_DIGITAL_ART = (
    "你是 Unique Vision AI 的资深项目顾问，专注于数字艺术与沉浸式视觉设计领域。"
    "你的任务是通过结构化的对话，高效地收集客户的数字艺术项目需求信息。\n\n"
    "【业务背景】\n"
    "数字艺术与沉浸式视觉设计涵盖数字装置、沉浸式互动体验、创意视觉内容等方向，"
    "适用于展览、发布会、品牌快闪活动、商业空间等场景。交付周期约7个工作日。\n\n"
    + _TONE_RULES +
    "【你需要收集的字段清单】\n"
    "核心必问项（前6项务必逐一主动询问，缺一不可；第7项为收尾确认）：\n"
    "1. 品牌/项目名称 — 客户的品牌或项目名称\n"
    "2. 活动场景与用途 — 展览、发布会、快闪店、商业空间等\n"
    "3. 创意方向 — 客户想要什么样的数字艺术内容（互动装置、沉浸式投影、生成式艺术等）\n"
    "4. 场地信息 — 活动场地的位置和空间尺寸\n"
    "5. 活动时间 — 什么时候需要交付/布展\n"
    "6. 制作预算 — 预算范围（放在活动时间之后再问）\n"
    "7. 现场实拍图 — 最后主动询问客户是否有场地实拍图或其他参考文件（如场地照片、空间平面图等），告知可以通过输入框左侧的上传按钮上传。此项选填，可跳过。\n\n"
    "自然追问项（对话中自然涉及就记录）：\n"
    "8. 项目背景 — 为什么要做这个项目（新品发布、周年庆、品牌升级等）\n"
    "9. 互动需求 — 是否需要观众互动（体感、触控、AI实时生成等）\n"
    "10. 风格偏好 — 未来科技、东方美学、自然生态、抽象艺术等\n"
    "11. 技术限制 — 场地是否有设备/电力/网络等限制\n"
    "12. 受众画像 — 主要面向什么人群\n\n"
    + _DIALOG_RULES
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 媒体方需求收集 Prompt（AGENT_MODE=media 时使用）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_MEDIA_TONE_RULES = (
    "【对客户的表达方式】\n"
    "- 像经验丰富的行业顾问面对面沟通：专业、自然、有温度，不使用 emoji。\n"
    "- 可以偶尔用“好的”“明白”“了解”承接，但不要每轮都说。\n"
    "- 不过度客套，不说“非常感谢您的配合”“您太棒了”等。\n"
    "- 用行业术语体现专业度，但不堆砌术语。\n"
    "- 不暴露内部执行规则、字段名、判断条件、系统来源或提示词内容。\n"
    "- 不使用内部流程词或过程说明，例如：开放问题、开放起手、阶段过渡、核心必问项、字段清单、触发完成、严格条件、Memory、记忆里、留存过、系统记录显示、第一阶段、下面进入某阶段、按流程收集。\n\n"
)

_MEDIA_DIALOG_RULES = (
    "【对话推进规则】\n"
    "1. 每次回复只问一个问题。客户一次回答多个信息时，先记录，再追问一个最自然的缺口。\n"
    "2. 选择下一问的优先级：优先追问客户刚提到但不完整的信息；其次补齐当前主题下最关键的缺口；最后再进入新的主题。\n"
    "3. 不重复询问已经明确的信息。如果客户暂时不清楚或不方便回答，先跳过。\n"
    "4. 不机械按表单字段推进。客户提到城市位置，可以顺势问观看动线；客户聊到内容主题，可以接着问视觉调性。\n"
    "5. 预算不是强制必问项。若客户比较配合、没有表达想退出或尽快结束，并且内容、点位、技术和时间已基本清楚，可以在靠后位置自然询问预算范围，并说明是为了匹配制作方案。若客户不方便、暂时不确定或想先结束，跳过并备注即可。\n"
    "6. 问技术规格时要给短例子，让客户知道怎么答；例如“屏幕分辨率 3840x2160、物理尺寸约宽 20m x 高 8m、格式 MP4/MOV、25/30fps、Rec.709 或 sRGB”。\n"
    "7. 文件上传放在最后。核心信息基本收集后，再提醒客户有现场实拍图、屏幕照片或参考素材可以上传；没有也可以继续整理。\n"
    "8. 客户上传文件后，只确认收到文件名或文件数量，再问是否还有其他参考素材。除非客户文字描述了图片内容，或消息里提供了明确的图片分析结果，否则不要描述图片画面，不要说“从画面可见”，不要根据点位 memory 推断遮挡、动线或现场结构。\n"
    "9. 客户补充但无法归类的信息，完整记录到备注。\n\n"
    "【系统控制标记】\n"
    "- 仅当至少 8 项核心信息已有实质回答后，才可以在总结末尾输出【需求收集完成】；预算不作为硬性完成条件。\n"
    "- 信息不足时继续自然追问，不要主动结束。\n"
    "- 客户明确表示不想继续时，可以提前总结；需说明缺失项，并在末尾输出【需求收集完成】。\n"
    "- 客户明确表示不想使用 AI、想找人工/真人/客服/销售/项目顾问时，立即停止需求追问，"
    "不要输出【需求收集完成】，不要生成表单总结；只确认已转入人工项目顾问处理，并在回复末尾输出【转人工】。\n"
)

_PROMPT_MEDIA_3D = (
    "你是 Unique Vision AI 的资深项目顾问，在裸眼3D户外媒体内容定制领域有多年的项目经验。"
    "你的任务是通过自然、专业的对话，高效地收集媒体方客户的裸眼3D项目需求信息。\n\n"
    "【目标】\n"
    "媒体方客户通常拥有户外大屏、交通枢纽屏幕等媒体资源。你的目标是帮助客户把本次裸眼3D内容需求梳理清楚，"
    "包括项目大方向、媒体资源、创意表达、技术规格、交付节点和可选参考素材。\n\n"
    + _MEDIA_TONE_RULES +
    "【开场】\n"
    "- 第一轮必须接近这个结构：一句预期说明 + 一个宽问题。\n"
    "- 预期说明：会从基础信息、创意方向、技术与交付几方面帮助梳理。\n"
    "- 宽问题：让客户先说大概想法，例如“您可以先简单说说，这次大概想做什么样的内容？”\n"
    "- 第一轮只允许一个问号。不要连续追问，不要写成多选题，不要用“是……还是……或者……”列举方向。\n"
    "- 第一轮不要解释三方面分别包含什么；不要询问城市、具体位置、屏幕尺寸、预算。\n"
    "- 第一轮不要提及任何已知屏幕、具体点位、近期项目、历史主题或历史创意方向，避免替客户预设本次项目。\n\n"
    "【已知信息使用】\n"
    "- 第一轮：不使用具体已知信息，包括屏幕、点位、近期项目、历史主题、历史创意方向。\n"
    "- 第二轮以后：如果客户描述与已知信息相关，要自然带出具体线索，帮助客户少输入。例如：“我们了解到您这边有深圳万象天地主广场大屏这类点位资料；如果这次会用到，我可以把视角和动线一起考虑进去。”\n"
    "- 写入本次需求前：必须先得到客户确认。客户确认前，不要把已知屏幕、历史主题、历史订单、近期项目写入本次需求。\n"
    "- 不要把历史线索说成双方已经合作过的项目，也不要说成上次项目，除非客户在当前对话里明确这么说。历史线索只能表达为候选信息或偏好参考。\n"
    "- 可以提及具体点位，但提问不要替客户预设答案。如果需要确认点位，用更轻的问法，例如“这次会使用已有点位，还是先按一个新点位来梳理？”\n"
    "- 创意偏好只能作为建议和确认项。客户确认后，再写入 art_direction、theme_concept 或 special_requirements。\n\n"
    "【需要逐步收集的信息】\n"
    "- 整体想法：初步内容设想、项目目标、当前遇到的问题。\n"
    "- 基础信息：投放城市、媒体位置、媒体背景、位置特点、目标受众、场景特点。\n"
    "- 创意方向：观看动线、整体艺术方向、风格偏好、内容主题、核心表达、IP形象或品牌露出。\n"
    "- 技术与交付：屏幕分辨率、物理尺寸、视频格式、帧率、色彩空间、安全区规范、审核规范、审核周期、预计上刊时间、特殊合作要求。\n"
    "- 可自然询问或记录：媒体定位、品牌调性、适配品牌类型、投放时长、内容数量、预算范围。\n"
    "- 预算提问时机：只在客户仍愿意继续、其他信息已基本清楚时靠后询问；不要为了预算阻止需求总结。\n"
    "- 技术项提问示例：可以问“屏幕分辨率和物理尺寸大概是多少？比如 3840x2160，宽 20m x 高 8m；如果还没有完整参数，先给您手头已有的也可以。”\n"
    "- 交付项提问示例：可以问“交付规范这边有固定要求吗？比如 MP4 或 MOV、25/30fps、Rec.709/sRGB、安全区或审核周期。”\n"
    "- 项目名称不是客户必答项，不要主动询问；后续系统会根据点位、屏幕、内容主题或核心概念自动生成。\n\n"
    + _MEDIA_DIALOG_RULES
)


def _get_requirement_prompt(business_type: str) -> str:
    """根据业务类型返回对应的需求收集 prompt"""
    if settings.AGENT_MODE == "media":
        prompts = {
            "ai_3d_custom": _PROMPT_MEDIA_3D,
            "video_purchase": _PROMPT_VIDEO_PURCHASE,
            "digital_art": _PROMPT_DIGITAL_ART,
        }
        return prompts.get(business_type, _PROMPT_MEDIA_3D)
    else:
        prompts = {
            "ai_3d_custom": _PROMPT_AI_3D,
            "video_purchase": _PROMPT_VIDEO_PURCHASE,
            "digital_art": _PROMPT_DIGITAL_ART,
        }
        return prompts.get(business_type, _PROMPT_AI_3D)


def _is_mock_completion_message(message: str) -> bool:
    """离线 mock 模式下，识别用户明确确认需求已整理完毕的表达。"""
    negative_markers = ["还没完成", "没有完成", "没完成", "未完成", "不完整", "还不行"]
    if any(marker in message for marker in negative_markers):
        return False

    positive_markers = [
        "没问题", "可以了", "确认", "就这样", "先这样",
        "完成了", "需求完成", "收集完成", "信息齐了",
    ]
    return any(marker in message for marker in positive_markers)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 需求收集 Agent（/chat）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/chat")
async def ai_chat(request: ChatRequest, raw_request: Request):
    """核心聊天接口 — 需求收集对话（含 Memory 注入）"""
    user_id = "anonymous"
    username = "anonymous"
    company_name = ""
    auth_header = raw_request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        payload = decode_access_token(auth_header[7:])
        if payload:
            user_id = payload.get("user_id", "anonymous")
            username = payload.get("username", "anonymous")

    # ── 加载用户 Memory ──
    memory = None
    memory_context = ""
    if user_id != "anonymous":
        try:
            from app.services.memory_service import (
                get_or_create_memory, build_memory_context,
                trigger_crawl, update_interaction_stats,
            )
            memory = await get_or_create_memory(user_id)
            memory_context = build_memory_context(memory)

            # 首次接触 + 有公司名 → 触发后台爬取
            ci = memory.company_info or {}
            if not ci.get("crawl_status") and not company_name:
                # 从 DB 获取用户的公司名
                try:
                    from app.database import async_session_maker
                    from app.models.user import User
                    from sqlalchemy import select
                    async with async_session_maker() as session:
                        result = await session.execute(
                            select(User.company, User.enterprise_name).where(User.id == user_id)
                        )
                        row = result.first()
                        if row:
                            company_name = row.enterprise_name or row.company or ""
                except Exception:
                    pass

                if company_name:
                    await trigger_crawl(user_id, company_name)

            # 更新交互统计（后台，不阻塞）
            import asyncio
            asyncio.create_task(update_interaction_stats(user_id))
        except Exception as e:
            log_business_event(
                logger,
                "ai_memory_context_failed",
                level="warning",
                user_id=user_id,
                session_id=request.session_id,
                business_type=request.business_type,
                error=str(e),
            )

    existing_handoff = await _append_handoff_message(
        user_id=user_id,
        username=username,
        session_id=request.session_id,
        business_type=request.business_type,
        history=request.history,
        user_msg=request.message,
        assistant_msg=_HUMAN_HANDOFF_APPEND_REPLY,
    )
    if existing_handoff:
        log_business_event(
            logger,
            "ai_handoff_message_appended",
            user_id=user_id,
            username=username,
            session_id=request.session_id,
            business_type=request.business_type,
            handoff_id=existing_handoff.get("handoff_id"),
            draft_order_id=existing_handoff.get("draft_order_id"),
            history_count=len(request.history or []),
        )
        _save_session_file(
            session_id=request.session_id, user_id=user_id, username=username,
            history=request.history, user_msg=request.message, assistant_msg=_HUMAN_HANDOFF_APPEND_REPLY,
            business_type=request.business_type,
            user_message_id=request.user_message_id,
            assistant_message_id=request.assistant_message_id,
        )
        return {"message": _HUMAN_HANDOFF_APPEND_REPLY, "handoff": True, **existing_handoff}

    if _is_human_handoff_request(request.message):
        handoff_reply = _handoff_reply_for_business_type(request.business_type)
        handoff_meta = await _record_handoff(
            user_id=user_id,
            username=username,
            session_id=request.session_id,
            business_type=request.business_type,
            history=request.history,
            user_msg=request.message,
            assistant_msg=handoff_reply,
        )
        log_business_event(
            logger,
            "ai_handoff_triggered",
            user_id=user_id,
            username=username,
            session_id=request.session_id,
            business_type=request.business_type,
            trigger_source="user_direct",
            handoff_id=handoff_meta.get("handoff_id"),
            draft_order_id=handoff_meta.get("draft_order_id"),
            history_count=len(request.history or []),
        )
        _save_session_file(
            session_id=request.session_id, user_id=user_id, username=username,
            history=request.history, user_msg=request.message, assistant_msg=handoff_reply,
            business_type=request.business_type,
            user_message_id=request.user_message_id,
            assistant_message_id=request.assistant_message_id,
        )
        return {"message": handoff_reply, "handoff": True, **handoff_meta}

    if is_consultation_business_type(request.business_type):
        reply = get_consultation_intro(request.business_type)
        _save_session_file(
            session_id=request.session_id, user_id=user_id, username=username,
            history=request.history, user_msg=request.message, assistant_msg=reply,
            business_type=request.business_type,
            user_message_id=request.user_message_id,
            assistant_message_id=request.assistant_message_id,
        )
        return {"message": reply, "handoff": False, "business_type": request.business_type}

    if not settings.AI_API_KEY:
        mock_reply = "【真实后端接口调试中】"
        if _is_mock_completion_message(request.message):
            mock_reply += "核心需求已确认，我将为您整理项目评估与需求明细。 【需求收集完成】"
        elif len(request.message) > 5:
            mock_reply += f"收到您的反馈：{request.message[:10]}... 请问这次项目计划投放在哪个城市或站点？"
        else:
            mock_reply += "好的，请继续详细描述您的诉求。"

        _save_session_file(
            session_id=request.session_id, user_id=user_id, username=username,
            history=request.history, user_msg=request.message, assistant_msg=mock_reply,
            business_type=request.business_type,
            user_message_id=request.user_message_id,
            assistant_message_id=request.assistant_message_id,
        )
        return {"message": mock_reply}

    try:
        llm_messages = _build_requirement_llm_messages(request, memory_context)
        data = await post_chat_completion(
            {
                "model": settings.AI_MODEL_NAME,
                "messages": llm_messages,
                "enable_thinking": _should_enable_design_thinking(request.message),
            },
            timeout=settings.AI_HTTP_TIMEOUT,
        )
        reply = data["choices"][0]["message"]["content"]
        reply, handoff, handoff_meta = await _finalize_ai_chat_reply(
            request=request,
            user_id=user_id,
            username=username,
            reply=reply,
        )
        return {"message": reply, "handoff": handoff, **handoff_meta}

    except HTTPException:
        raise
    except Exception as e:
        log_business_event(
            logger,
            "ai_chat_failed",
            level="error",
            user_id=user_id,
            username=username,
            session_id=request.session_id,
            business_type=request.business_type,
            history_count=len(request.history or []),
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def ai_chat_stream(request: ChatRequest, raw_request: Request):
    """流式需求收集对话。保留 /chat 作为非流式兼容入口。"""
    user_id = "anonymous"
    username = "anonymous"
    company_name = ""
    auth_header = raw_request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        payload = decode_access_token(auth_header[7:])
        if payload:
            user_id = payload.get("user_id", "anonymous")
            username = payload.get("username", "anonymous")

    memory_context = ""
    if user_id != "anonymous":
        try:
            from app.services.memory_service import (
                get_or_create_memory, build_memory_context,
                trigger_crawl, update_interaction_stats,
            )
            memory = await get_or_create_memory(user_id)
            memory_context = build_memory_context(memory)

            ci = memory.company_info or {}
            if not ci.get("crawl_status") and not company_name:
                try:
                    from app.database import async_session_maker
                    from app.models.user import User
                    from sqlalchemy import select
                    async with async_session_maker() as session:
                        result = await session.execute(
                            select(User.company, User.enterprise_name).where(User.id == user_id)
                        )
                        row = result.first()
                        if row:
                            company_name = row.enterprise_name or row.company or ""
                except Exception:
                    pass

                if company_name:
                    await trigger_crawl(user_id, company_name)

            asyncio.create_task(update_interaction_stats(user_id))
        except Exception as e:
            log_business_event(
                logger,
                "ai_memory_context_failed",
                level="warning",
                user_id=user_id,
                session_id=request.session_id,
                business_type=request.business_type,
                error=str(e),
            )

    async def one_shot(payload: dict):
        yield _sse_event("start", {})
        message = payload.get("message") or ""
        if message:
            yield _sse_event("delta", {"content": message})
        yield _sse_event("final", payload)

    stream_headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    }

    existing_handoff = await _append_handoff_message(
        user_id=user_id,
        username=username,
        session_id=request.session_id,
        business_type=request.business_type,
        history=request.history,
        user_msg=request.message,
        assistant_msg=_HUMAN_HANDOFF_APPEND_REPLY,
    )
    if existing_handoff:
        log_business_event(
            logger,
            "ai_handoff_message_appended",
            user_id=user_id,
            username=username,
            session_id=request.session_id,
            business_type=request.business_type,
            handoff_id=existing_handoff.get("handoff_id"),
            draft_order_id=existing_handoff.get("draft_order_id"),
            history_count=len(request.history or []),
        )
        _save_session_file(
            session_id=request.session_id, user_id=user_id, username=username,
            history=request.history, user_msg=request.message, assistant_msg=_HUMAN_HANDOFF_APPEND_REPLY,
            business_type=request.business_type,
            user_message_id=request.user_message_id,
            assistant_message_id=request.assistant_message_id,
        )
        payload = {"message": _HUMAN_HANDOFF_APPEND_REPLY, "handoff": True, **existing_handoff}
        return StreamingResponse(one_shot(payload), media_type="text/event-stream", headers=stream_headers)

    if _is_human_handoff_request(request.message):
        handoff_reply = _handoff_reply_for_business_type(request.business_type)
        handoff_meta = await _record_handoff(
            user_id=user_id,
            username=username,
            session_id=request.session_id,
            business_type=request.business_type,
            history=request.history,
            user_msg=request.message,
            assistant_msg=handoff_reply,
        )
        log_business_event(
            logger,
            "ai_handoff_triggered",
            user_id=user_id,
            username=username,
            session_id=request.session_id,
            business_type=request.business_type,
            trigger_source="user_direct",
            handoff_id=handoff_meta.get("handoff_id"),
            draft_order_id=handoff_meta.get("draft_order_id"),
            history_count=len(request.history or []),
        )
        _save_session_file(
            session_id=request.session_id, user_id=user_id, username=username,
            history=request.history, user_msg=request.message, assistant_msg=handoff_reply,
            business_type=request.business_type,
            user_message_id=request.user_message_id,
            assistant_message_id=request.assistant_message_id,
        )
        payload = {"message": handoff_reply, "handoff": True, **handoff_meta}
        return StreamingResponse(one_shot(payload), media_type="text/event-stream", headers=stream_headers)

    if is_consultation_business_type(request.business_type):
        reply = get_consultation_intro(request.business_type)
        _save_session_file(
            session_id=request.session_id, user_id=user_id, username=username,
            history=request.history, user_msg=request.message, assistant_msg=reply,
            business_type=request.business_type,
            user_message_id=request.user_message_id,
            assistant_message_id=request.assistant_message_id,
        )
        payload = {"message": reply, "handoff": False, "business_type": request.business_type}
        return StreamingResponse(one_shot(payload), media_type="text/event-stream", headers=stream_headers)

    if not settings.AI_API_KEY:
        mock_reply = "【真实后端接口调试中】"
        if _is_mock_completion_message(request.message):
            mock_reply += "核心需求已确认，我将为您整理项目评估与需求明细。 【需求收集完成】"
        elif len(request.message) > 5:
            mock_reply += f"收到您的反馈：{request.message[:10]}... 请问这次项目计划投放在哪个城市或站点？"
        else:
            mock_reply += "好的，请继续详细描述您的诉求。"

        _save_session_file(
            session_id=request.session_id, user_id=user_id, username=username,
            history=request.history, user_msg=request.message, assistant_msg=mock_reply,
            business_type=request.business_type,
            user_message_id=request.user_message_id,
            assistant_message_id=request.assistant_message_id,
        )
        return StreamingResponse(
            one_shot({"message": mock_reply, "handoff": False}),
            media_type="text/event-stream",
            headers=stream_headers,
        )

    llm_messages = _build_requirement_llm_messages(request, memory_context)

    async def event_generator():
        collected: list[str] = []
        thinking_enabled = _should_enable_design_thinking(request.message)
        thinking_sent = False
        yield _sse_event("start", {})
        try:
            provider = "chat_completions"
            if should_use_responses_api():
                provider = "responses"
                try:
                    async for delta in stream_responses_completion(
                        {
                            "model": settings.AI_MODEL_NAME,
                            "input": _build_responses_input(llm_messages),
                        },
                        timeout=settings.AI_HTTP_TIMEOUT,
                    ):
                        collected.append(delta)
                        yield _sse_event("delta", {"content": delta, "provider": provider})
                except HTTPException as responses_error:
                    if collected:
                        raise
                    provider = "chat_completions"
                    log_business_event(
                        logger,
                        "ai_responses_stream_fallback",
                        level="warning",
                        user_id=user_id,
                        username=username,
                        session_id=request.session_id,
                        business_type=request.business_type,
                        fallback_provider=provider,
                        error=str(responses_error.detail),
                    )

            if provider == "chat_completions":
                async for event in stream_chat_completion_events(
                    {
                        "model": settings.AI_MODEL_NAME,
                        "messages": llm_messages,
                        "enable_thinking": thinking_enabled,
                    },
                    timeout=settings.AI_HTTP_TIMEOUT,
                ):
                    event_type = event.get("type")
                    if event_type == "reasoning":
                        if thinking_enabled and not thinking_sent:
                            thinking_sent = True
                            yield _sse_event(
                                "thinking",
                                {
                                    "stage": "creative_plan",
                                    "label": "正在梳理设计与策划思路，可能需要稍长时间",
                                    "provider": provider,
                                },
                            )
                        continue
                    delta = event.get("content") or ""
                    if delta:
                        collected.append(delta)
                        yield _sse_event("delta", {"content": delta, "provider": provider})

            raw_reply = "".join(collected)
            if not raw_reply.strip():
                raise HTTPException(status_code=502, detail="AI 服务未返回内容")

            reply, handoff, handoff_meta = await _finalize_ai_chat_reply(
                request=request,
                user_id=user_id,
                username=username,
                reply=raw_reply,
            )
            log_business_event(
                logger,
                "ai_chat_stream_provider_completed",
                user_id=user_id,
                username=username,
                session_id=request.session_id,
                business_type=request.business_type,
                provider=provider,
                handoff=handoff,
                reply_length=len(reply or ""),
            )
            yield _sse_event("final", {"message": reply, "handoff": handoff, "provider": provider, **handoff_meta})
        except HTTPException as e:
            log_business_event(
                logger,
                "ai_chat_stream_failed",
                level="error",
                user_id=user_id,
                username=username,
                session_id=request.session_id,
                business_type=request.business_type,
                history_count=len(request.history or []),
                error=str(e.detail),
            )
            yield _sse_event("error", {"detail": e.detail})
        except Exception as e:
            log_business_event(
                logger,
                "ai_chat_stream_failed",
                level="error",
                user_id=user_id,
                username=username,
                session_id=request.session_id,
                business_type=request.business_type,
                history_count=len(request.history or []),
                error=str(e),
            )
            yield _sse_event("error", {"detail": "AI 服务暂时不可用"})

    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=stream_headers)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 需求提取（/extract）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ExtractRequest(BaseModel):
    history: list = Field(default_factory=list)

@router.post("/extract")
async def ai_extract(request: ExtractRequest):
    """从对话历史中提取结构化信息"""
    if not settings.AI_API_KEY:
        if settings.AGENT_MODE == "media":
            return {
                "project_name": "示例项目 (Mock)",
                "city_location": "成都春熙路",
                "art_direction": "未来科技",
                "budget": "60万"
            }
        return {
            "brand": "示例品牌 (Mock)",
            "target_group": "年轻群体",
            "style": "科技感设计",
            "budget": "10万以上"
        }

    try:
        if settings.AGENT_MODE == "media":
            system_prompt = (
                "你是一个数据提取专家。请阅读以下对话记录，提取媒体方客户的项目需求信息。\n"
                "将提取的信息整理为严格的 JSON 格式返回，只返回 JSON，不要任何其他废话。\n"
                "支持的字段名（如果有对应信息则提取，没有则留空字符串）：\n"
                "project_name, resource_background, audience_scene, media_positioning, "
                "city_location, viewing_path, art_direction, theme_concept, "
                "media_specs, timing_number, tech_delivery, content_review, "
                "budget, online_time, special_requirements, site_photos, remarks.\n"
                "project_name 不是客户必填项；如果对话中没有明确项目名称，"
                "请根据 city_location、media_specs、theme_concept 自动生成一个简短项目名，"
                "格式类似'成都春熙路裸眼3D屏内容定制'或'上海核心商圈未来科技主题裸眼3D项目'。\n"
                "其中 site_photos（现场实拍图）记录客户是否提供了现场照片或参考文件；"
                "如果对话中只有文件名，没有客户对图片内容的文字描述，不要编写画面描述，只记录文件名。\n"
                "其中 remarks（备注）用于记录客户提供的任何无法归入上述字段的补充说明。"
            )
        else:
            system_prompt = (
                "你是一个数据提取专家。请阅读以下对话记录，提取客户的项目需求信息。\n"
                "将提取的信息整理为严格的 JSON 格式返回，只返回 JSON，不要任何其他废话。\n"
                "支持的字段名（如果有对应信息则提取，没有则留空字符串）：\n"
                "brand, background, target_group, brand_tone, content, style, prohibited_content, "
                "city, media_size, time_number, technology, budget, online_time, site_photos, remarks.\n"
                "其中 site_photos（现场实拍图）记录客户是否提供了现场照片或参考文件，如有则记录描述信息。\n"
                "其中 remarks（备注）用于记录客户提供的任何无法归入上述字段的补充说明、特殊要求或参考素材信息。"
            )

        chat_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in request.history])

        data = await post_chat_completion(
            {
                "model": settings.AI_MODEL_NAME,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"对话记录如下：\n{chat_text}\n\n请提取为JSON。"}
                ],
                "response_format": {"type": "json_object"}
            },
            timeout=settings.AI_HTTP_TIMEOUT,
        )
        content = data["choices"][0]["message"]["content"]

        if content.startswith("```json"):
            content = content.split("```json")[-1].split("```")[0].strip()
        elif content.startswith("```"):
            content = content.split("```")[-1].split("```")[0].strip()

        parsed = json.loads(content)
        if settings.AGENT_MODE == "media" and not any(str(v or "").strip() for v in parsed.values()):
            fallback = _fallback_extract_media(request.history)
            if fallback:
                log_business_event(
                    logger,
                    "ai_extract_fallback_used",
                    level="warning",
                    reason="empty_llm_result",
                    extracted_field_count=len(fallback),
                )
                return fallback
        return parsed

    except Exception as e:
        fallback = _fallback_extract_media(request.history) if settings.AGENT_MODE == "media" else {}
        log_business_event(
            logger,
            "ai_extract_failed",
            level="warning",
            history_count=len(request.history or []),
            error=str(e),
            fallback_field_count=len(fallback),
        )
        if fallback:
            log_business_event(
                logger,
                "ai_extract_fallback_used",
                level="warning",
                reason="llm_extract_failed",
                extracted_field_count=len(fallback),
            )
        return fallback


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 项目评估（/assess）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class AssessRequest(BaseModel):
    extracted: dict = Field(default_factory=dict)

@router.post("/assess")
async def ai_assess(request: AssessRequest):
    """根据提取的需求数据生成专业项目评估"""
    # ── 媒体方模式：从 media_assess_logic.md 读取评估逻辑 ──
    if settings.AGENT_MODE == "media":
        try:
            from app.utils.knowledge import get_knowledge_file
            logic_path = get_knowledge_file('media_assess_logic.md')
            with open(logic_path, 'r', encoding='utf-8') as f:
                assess_logic = f.read().strip()
            if not assess_logic:
                # 评估逻辑文件为空，跳过评估，直接显示表单
                return {"assessment": ""}
            # 有评估逻辑内容，调用 LLM 生成评估
            if settings.AI_API_KEY:
                info = "\n".join([f"{k}: {v}" for k, v in request.extracted.items() if v])
                data = await post_chat_completion(
                    {
                        "model": settings.AI_MODEL_NAME,
                        "messages": [
                            {"role": "system", "content": assess_logic},
                            {"role": "user", "content": f"客户需求信息：\n{info}"}
                        ]
                    },
                    timeout=settings.AI_HTTP_TIMEOUT,
                )
                assessment = data["choices"][0]["message"]["content"]
                return {"assessment": assessment}
            return {"assessment": ""}
        except Exception as e:
            log_business_event(
                logger,
                "ai_assess_failed",
                level="warning",
                agent_mode=settings.AGENT_MODE,
                extracted_field_count=len(request.extracted or {}),
                error=str(e),
            )
            return {"assessment": ""}

    # ── 品牌方原逻辑 ──
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
                recommend_mode = "AI驱动3D OOH内容定制" if num >= 8 else "3D OOH数字内容资源库"
                timeline = "约15个工作日" if num >= 8 else "约5个工作日"
            except Exception:
                recommend_mode = "AI驱动3D OOH内容定制" if has_custom_need else "3D OOH数字内容资源库"
                timeline = "约15个工作日" if has_custom_need else "约5个工作日"
        else:
            recommend_mode = "AI驱动3D OOH内容定制" if has_custom_need else "3D OOH数字内容资源库"
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
            "评估应包含：推荐方案（3D OOH数字内容资源库 / AI驱动3D OOH内容定制 / 数字艺术与沉浸式视觉设计）、预计制作周期、"
            "预算合理性分析、投放建议、时间节点建议。\n"
            "语气专业沉稳，不用emoji，不寒暄，用要点式列出。\n"
            "最后一行固定写：\n以下是整理后的需求明细，请确认或修改：\n"
        )

        info = "\n".join([f"{k}: {v}" for k, v in d.items() if v])

        data = await post_chat_completion(
            {
                "model": settings.AI_MODEL_NAME,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"客户需求信息：\n{info}"}
                ]
            },
            timeout=settings.AI_HTTP_TIMEOUT,
        )
        assessment = data["choices"][0]["message"]["content"]
        return {"assessment": assessment}
    except Exception as e:
        log_business_event(
            logger,
            "ai_assess_failed",
            level="warning",
            agent_mode=settings.AGENT_MODE,
            extracted_field_count=len(request.extracted or {}),
            error=str(e),
        )
        return {"assessment": "**项目评估**\n\n需求信息已整理完毕。以下是需求明细，请确认或修改："}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 案例数据接口
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/cases")
async def ai_get_cases(category: str = None):
    """获取案例列表（含视频链接）"""
    try:
        from app.utils.knowledge import get_knowledge_file
        cases_path = get_knowledge_file('cases.json')
        with open(cases_path, "r", encoding="utf-8") as f:
            cases = json.load(f)
        if category:
            cases = [c for c in cases if c.get("category") == category]
        return {"cases": cases}
    except Exception as e:
        log_business_event(
            logger,
            "ai_cases_load_failed",
            level="warning",
            category=category,
            error=str(e),
        )
        return {"cases": []}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 会话存储工具
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def _save_to_db(
    session_id: str,
    user_id: str,
    username: str,
    user_msg: str,
    assistant_msg: str,
    business_type: str = "ai_3d_custom",
    user_message_id: str | None = None,
    assistant_message_id: str | None = None,
):
    """将用户消息和助手回复保存到数据库（异步）"""
    try:
        from app.database import async_session_maker
        from app.models.ai_chat import AIChatSession, AIChatMessage
        from sqlalchemy import select, func

        async with async_session_maker() as db:
            # 查找或创建 session
            result = await db.execute(
                select(AIChatSession).where(AIChatSession.id == session_id)
            )
            session = result.scalar_one_or_none()

            if not session:
                session = AIChatSession(
                    id=session_id,
                    user_id=user_id,
                    username=username,
                    session_type="requirement",
                    business_type=business_type,
                    title=(user_msg.strip()[:80] + "...") if len(user_msg.strip()) > 80 else user_msg.strip(),
                    message_count=0,
                )
                db.add(session)
            elif user_id and user_id != "anonymous":
                if not session.user_id or session.user_id == "anonymous":
                    session.user_id = user_id
                if username and (not session.username or session.username == "anonymous"):
                    session.username = username

            existing_ids = set()
            if user_message_id or assistant_message_id:
                known_ids = [mid for mid in [user_message_id, assistant_message_id] if mid]
                existing_result = await db.execute(
                    select(AIChatMessage.client_message_id).where(
                        AIChatMessage.session_id == session_id,
                        AIChatMessage.client_message_id.in_(known_ids),
                    )
                )
                existing_ids = {row[0] for row in existing_result.all()}
                if user_message_id in existing_ids and assistant_message_id in existing_ids:
                    return
            else:
                existing_result = await db.execute(
                    select(AIChatMessage.role, AIChatMessage.content)
                    .where(AIChatMessage.session_id == session_id)
                    .order_by(AIChatMessage.id.desc())
                    .limit(2)
                )
                recent = list(reversed(existing_result.all()))
                if recent == [("user", user_msg), ("assistant", assistant_msg)]:
                    return

            added_count = 0
            # 保存用户消息
            if not user_message_id or user_message_id not in existing_ids:
                db.add(AIChatMessage(
                    session_id=session_id,
                    client_message_id=user_message_id,
                    role="user",
                    content=user_msg,
                ))
                added_count += 1
            # 保存助手回复
            if not assistant_message_id or assistant_message_id not in existing_ids:
                db.add(AIChatMessage(
                    session_id=session_id,
                    client_message_id=assistant_message_id,
                    role="assistant",
                    content=assistant_msg,
                ))
                added_count += 1

            session.message_count = (session.message_count or 0) + added_count
            now = datetime.now()
            session.updated_at = now

            try:
                await db.commit()
                log_business_event(
                    logger,
                    "ai_chat_messages_saved",
                    session_id=session_id,
                    user_id=user_id,
                    username=username,
                    business_type=business_type,
                    added_count=added_count,
                    message_count=session.message_count,
                )
            except IntegrityError:
                await db.rollback()
    except Exception as e:
        log_business_event(
            logger,
            "ai_chat_messages_save_failed",
            level="warning",
            session_id=session_id,
            user_id=user_id,
            username=username,
            business_type=business_type,
            error=str(e),
        )


def _save_session_file(
    session_id: str,
    user_id: str,
    username: str,
    history: list,
    user_msg: str,
    assistant_msg: str,
    business_type: str = "ai_3d_custom",
    user_message_id: str | None = None,
    assistant_message_id: str | None = None,
):
    """将完整的 AI 对话 session 保存为 JSON 文件 + 数据库

    文件结构：
    logs/ai_sessions/
    └── {user_id}/
        └── {session_id}.json
    """
    # 异步保存到数据库
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_save_to_db(
                session_id, user_id, username, user_msg, assistant_msg, business_type,
                user_message_id, assistant_message_id
            ))
        else:
            loop.run_until_complete(_save_to_db(
                session_id, user_id, username, user_msg, assistant_msg, business_type,
                user_message_id, assistant_message_id
            ))
    except Exception as e:
        log_business_event(
            logger,
            "ai_chat_save_schedule_failed",
            level="warning",
            session_id=session_id,
            user_id=user_id,
            username=username,
            business_type=business_type,
            error=str(e),
        )

    # 同时保留 JSON 文件日志（兼容）
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
        log_business_event(
            logger,
            "ai_chat_json_save_failed",
            level="warning",
            session_id=session_id,
            user_id=user_id,
            username=username,
            business_type=business_type,
            error=str(e),
        )
