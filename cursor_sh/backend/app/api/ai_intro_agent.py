"""
业务介绍 Agent — 独立模块
负责向客户介绍公司业务、服务模式，并在客户索要案例时引导咨询顾问。

线上 Agent 不再展示案例，不返回案例卡片，也不触发案例推荐流程。
"""

import re
from typing import Tuple
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.config import settings
from app.services.ai_client import post_chat_completion
from app.services.platform_service_catalog import get_consultation_intro
from app.utils.business_log import log_business_event
from app.utils.log_setup import get_module_logger

intro_router = APIRouter()
logger = get_module_logger("ai")


def _detect_consultation_business_type(message: str) -> str | None:
    text = (message or "").strip()
    if re.search(r"tvc|fooh|vj|动态影像|动态视觉|广告视觉|广告影片|平面广告|motion", text, re.I):
        return "motion_content"
    if re.search(r"后期|精修|修图|视频精修|cgi|商业摄影|拍摄|航拍|drone|retouch", text, re.I):
        return "media_post_production"
    if re.search(r"投放分析|效果报告|数据报告|受众分析|传播效果|campaign|analytics|report", text, re.I):
        return "campaign_analytics"
    return None


ORDERABLE_BUSINESS_LABELS = {
    "ai_3d_custom": "AI驱动3D OOH内容定制",
    "video_purchase": "3D OOH数字内容资源库",
    "digital_art": "数字艺术与沉浸式视觉设计",
}


_CASE_CONSULTANT_REPLY = (
    "线上暂不展示公开案例。由于过往项目涉及客户授权、投放场景和保密范围，"
    "相关资料需要由咨询顾问结合您的行业、屏幕场景和项目方向进行匹配说明。\n\n"
    "您可以先告诉我项目类型、投放城市或希望参考的内容方向，我会协助梳理并衔接顾问继续跟进。"
)


def _is_case_consultant_request(message: str) -> bool:
    text = (message or "").strip()
    if not text:
        return False
    return bool(re.search(r"案例|作品|成功项目|过往项目|看看你们做过|之前做过|展示一下", text))


def _build_case_consultant_reply() -> str:
    return _CASE_CONSULTANT_REPLY


def _detect_orderable_business_type(message: str) -> str | None:
    text = (message or "").strip()
    if re.search(r"ai.*3d.*定制|3d.*定制|裸眼3d.*定制|ai驱动|ooh.*定制", text, re.I):
        return "ai_3d_custom"
    if re.search(r"资源库|素材库|数字内容资源|直接调用|买.*素材|采购.*素材|video_purchase", text, re.I):
        return "video_purchase"
    if re.search(r"数字艺术|沉浸式|装置艺术|空间视觉|digital_art", text, re.I):
        return "digital_art"
    return None


def _is_order_start_intent(message: str) -> bool:
    text = (message or "").strip()
    return bool(re.search(r"下单|开始|立项|创建订单|需求梳理|推进|怎么做|怎么开始|报价|周期|合同|付款", text))


def _has_order_context(history: list) -> bool:
    recent = " ".join(
        str(h.get("content") or "")
        for h in (history or [])[-6:]
        if h.get("role") in ["user", "assistant"]
    )
    return bool(re.search(r"下单|需求梳理|创建订单|项目构想|开始流程|推进|立项", recent))


def _build_order_entry_reply(business_type: str, requirement_summary: str = "") -> str:
    label = ORDERABLE_BUSINESS_LABELS.get(business_type, ORDERABLE_BUSINESS_LABELS["ai_3d_custom"])
    summary_line = f"\n\n已记录的信息：{requirement_summary.strip()}" if requirement_summary else ""
    if business_type == "ai_3d_custom":
        return (
            f"好的，已为您匹配「{label}」。"
            f"{summary_line}\n\n"
            "接下来我会从基础信息、创意方向、技术与交付几方面帮助您梳理。"
            "您可以先简单说说，这次大概想做什么样的内容？"
        )
    return (
        f"好的，已为您匹配「{label}」。"
        f"{summary_line}\n\n"
        "接下来我会帮您逐步补齐项目基础信息、创意方向、投放场景和技术交付要求。"
        "您可以先简单说说，这次项目大概想做什么样的内容或体验？"
    )


def _build_order_choice_reply() -> str:
    return (
        "可以，我来协助您进入需求梳理流程。\n\n"
        "请先选择本次项目更接近的业务类型：AI驱动3D OOH内容定制、3D OOH数字内容资源库，"
        "或数字艺术与沉浸式视觉设计。确认后我会按对应流程继续追问关键需求。"
    )


class BusinessIntroRequest(BaseModel):
    message: str
    history: list = Field(default_factory=list)


# ───────────────────────────────────────────────────────
# 数据加载
# ───────────────────────────────────────────────────────

def _load_business_knowledge() -> Tuple[str, list]:
    """加载业务介绍文档。线上 Agent 不再加载或返回案例数据。"""
    from app.utils.knowledge import get_knowledge_file

    try:
        intro_path = get_knowledge_file('business_intro.md')

        with open(intro_path, "r", encoding="utf-8") as f:
            intro_text = f.read()

        return intro_text, []
    except Exception as e:
        log_business_event(logger, "business_knowledge_load_failed", level="warning", error=str(e))
        return "暂无法读取详细业务介绍", []


# ───────────────────────────────────────────────────────
# 主路由
# ───────────────────────────────────────────────────────

@intro_router.post("/business-intro")
async def ai_business_intro(request: BusinessIntroRequest):
    """业务介绍对话"""
    business_knowledge, _ = _load_business_knowledge()
    consultation_type = _detect_consultation_business_type(request.message)
    orderable_type = _detect_orderable_business_type(request.message)

    if _is_case_consultant_request(request.message):
        return {"message": _build_case_consultant_reply(), "cases": [], "guide": {}}

    if consultation_type:
        return {"message": get_consultation_intro(consultation_type), "cases": [], "business_type": consultation_type}

    if orderable_type and (_is_order_start_intent(request.message) or _has_order_context(request.history)):
        summary = f"意向{ORDERABLE_BUSINESS_LABELS.get(orderable_type, '相关服务')}"
        return {
            "message": _build_order_entry_reply(orderable_type, summary),
            "cases": [],
            "business_type": orderable_type,
            "guide": {
                "should_guide": True,
                "business_type": orderable_type,
                "requirement_summary": summary,
            },
        }

    if _is_order_start_intent(request.message) and _has_order_context(request.history):
        return {
            "message": _build_order_choice_reply(),
            "cases": [],
            "guide": {"should_guide": True},
        }

    if not settings.AI_API_KEY:
        msg = request.message.lower()
        if "案例" in msg or "作品" in msg:
            return {"message": _build_case_consultant_reply(), "cases": [], "guide": {}}
        elif "裸眼" in msg or "3d" in msg or "成片" in msg:
            reply = ("3D OOH是我们的核心服务方向，提供两种主要交付模式：\n\n"
                     "**3D OOH数字内容资源库**\n"
                     "Ready-to-Deploy 3D DOOH Assets：即用型裸眼3D数字内容资产\n"
                     "Screen-Adaptive Content Packages：多屏适配内容方案\n"
                     "Global Landmark Screen Formats：全球地标大屏内容规格适配\n\n"
                     "**AI驱动3D OOH内容定制**\n"
                     "AI-Based Creative Development：AI创意内容开发\n"
                     "Site-Specific 3D Screen Adaptation：场景化裸眼3D空间适配\n"
                     "Real-World Playback Simulation：真实环境播放模拟\n"
                     "End-to-End DOOH Content Production：一站式DOOH内容制作\n\n"
                     "请问您倾向于哪种模式？")
            return {"message": reply, "cases": []}
        elif "数字" in msg or "艺术" in msg:
            reply = ("数字艺术与沉浸式视觉设计包含：\n"
                     "Art Direction & Visual Design：艺术指导与视觉设计\n"
                     "Virtual Installation Art：虚拟装置艺术\n"
                     "Immersive Spatial Visuals：沉浸式空间视觉\n"
                     "Experimental Digital Art Content：实验性数字艺术内容\n\n"
                     "我们会根据空间、媒介、内容主题和交付规格评估制作方案。")
            return {"message": reply, "cases": []}
        else:
            reply = ("Unique Vision AI 提供六大平台服务：\n\n"
                     "**3D OOH数字内容资源库**\n"
                     "Ready-to-Deploy 3D DOOH Assets：即用型裸眼3D数字内容资产\n"
                     "Screen-Adaptive Content Packages：多屏适配内容方案\n"
                     "Global Landmark Screen Formats：全球地标大屏内容规格适配\n\n"
                     "**AI驱动3D OOH内容定制**\n"
                     "AI-Based Creative Development：AI创意内容开发\n"
                     "Site-Specific 3D Screen Adaptation：场景化裸眼3D空间适配\n"
                     "Real-World Playback Simulation：真实环境播放模拟\n"
                     "End-to-End DOOH Content Production：一站式DOOH内容制作\n\n"
                     "**数字艺术与沉浸式视觉设计**\n"
                     "Art Direction & Visual Design：艺术指导与视觉设计\n"
                     "Virtual Installation Art：虚拟装置艺术\n"
                     "Immersive Spatial Visuals：沉浸式空间视觉\n"
                     "Experimental Digital Art Content：实验性数字艺术内容\n\n"
                     "**广告视觉与动态影像制作**\n"
                     "Static Advertising Visuals：平面广告视觉设计\n"
                     "TVC Production：TVC广告影片制作\n"
                     "FOOH Campaign Content：FOOH数字传播内容\n"
                     "VJ Visual Performance Content：VJ视觉演出内容\n"
                     "Motion Graphic Design：动态视觉设计\n\n"
                     "**户外媒体后期制作服务**\n"
                     "High-End Retouching：高端精修图像处理\n"
                     "Cinematic Video Finishing：电影级视频精修\n"
                     "CGI Enhancement：CGI视觉增强\n"
                     "Commercial Photography & Filming：商业摄影与视频拍摄\n"
                     "Drone Cinematography：航拍影像制作\n\n"
                     "**广告投放分析与效果报告**\n"
                     "DOOH Campaign Analytics：DOOH广告投放数据分析\n"
                     "Audience Performance Reports：受众效果分析报告\n"
                     "Visual Impact Assessment：视觉传播效果评估\n"
                     "Downloadable Data Reports：可下载数据报告系统\n\n"
                     "如需了解某个板块的详细信息，或需要项目资料支持，我可以为您衔接咨询顾问。")
            return {"message": reply, "cases": []}

    try:
        system_prompt = (
            "你是 Unique Vision AI 公司的资深项目顾问。\n"
            "你代表公司向客户介绍业务，语气应专业、沉稳、自信，体现行业头部服务商的格调。\n"
            "不使用emoji表情，不使用'哦''呢''呀'等语气词，不过度寒暄客套。\n"
            "以下是公司的业务资料：\n\n"
            f"{business_knowledge}\n\n"

            "【线上案例展示规则 — 最高优先级】\n"
            "1. 线上 Agent 不展示案例、不推荐案例、不返回案例卡片。\n"
            "2. 不输出【展示案例】、【推荐案例】等任何案例控制标记。\n"
            "3. 客户索要案例、作品、成功项目或过往项目时，直接说明线上暂不展示公开案例，"
            "并引导客户咨询顾问，由顾问结合行业、屏幕场景和项目方向提供可披露资料。\n"
            "4. 不编写、描述、虚构任何具体案例标题、客户名称、投放数据或视频内容。\n\n"

            "【对话节奏规则】\n"
            "1. 当你完成业务板块介绍后，可询问客户是否需要咨询顾问进一步匹配方案或资料。\n"
            "2. 只介绍业务资料中列出的六个业务板块，不要编造不存在的服务。\n\n"

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
            "  - 客户只是索要案例或资料，尚未表达明确项目执行意向\n"
            "  - 客户只是简单回应'不错''挺好的''有意思'，但没有表达进一步意向\n"
            "  - 对话不足3轮（用户发言不足3次）\n"
            "  - 客户仍在问业务相关的问题（如'数字艺术是什么意思'）\n\n"

            "引导方式要自然、不生硬，像顾问做完介绍后的自然收尾。示例：\n"
            "  - '如果您已有初步的项目构想，我可以直接进入需求梳理环节，帮您快速推进。'\n"
            "  - '从您描述的场景来看，AI驱动3D OOH内容定制会是比较匹配的方案。我们可以进一步聊聊具体需求。'\n"
            "注意：引导语要融入回答的结尾，不要单独一行突兀地出现。标记放在全文最后即可。\n"
        )

        llm_messages = [{"role": "system", "content": system_prompt}]
        for h in request.history:
            if h.get("role") in ["user", "assistant"] and h.get("content"):
                llm_messages.append({"role": h["role"], "content": h["content"]})
        llm_messages.append({"role": "user", "content": request.message})

        data = await post_chat_completion(
            {"model": settings.AI_MODEL_NAME, "messages": llm_messages},
            timeout=60.0,
        )
        reply = data["choices"][0]["message"]["content"]

        if re.search(r'【展示案例(?::[^】]*)?】|【推荐案例:case_\w+】', reply):
            reply = re.sub(r'【展示案例(?::[^】]*)?】', _build_case_consultant_reply(), reply)
            reply = re.sub(r'【推荐案例:case_\w+】', '', reply).strip()

        # 处理引导下单
        user_turn_count = sum(1 for h in request.history if h.get("role") == "user") + 1
        guide_info = {}

        guide_match = re.search(r'【引导下单(?::([^:】]+):([^】]+))?】', reply)
        if guide_match:
            if user_turn_count < 3:
                reply = re.sub(r'【引导下单(?::[^】]+)?】', '', reply).strip()
            else:
                reply = re.sub(r'【引导下单(?::[^】]+)?】', '', reply).strip()
                guide_info["should_guide"] = True
                if guide_match.group(1) and guide_match.group(2):
                    guide_info["business_type"] = guide_match.group(1).strip()
                    guide_info["requirement_summary"] = guide_match.group(2).strip()
                    reply = _build_order_entry_reply(
                        guide_info["business_type"],
                        guide_info["requirement_summary"],
                    )
                else:
                    reply = _build_order_choice_reply()

        return {"message": reply, "cases": [], "guide": guide_info}
    except HTTPException:
        raise
    except Exception as e:
        log_business_event(
            logger,
            "ai_business_intro_failed",
            level="error",
            history_count=len(request.history or []),
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试") from e
