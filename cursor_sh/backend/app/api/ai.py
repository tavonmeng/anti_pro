"""
AI 智能体 — 主路由入口
保留：需求收集（/chat, /extract, /assess）、初始欢迎（/start）、
      案例数据（/cases）、会话存储工具函数。
其余 Agent 拆分为独立模块并通过 include_router 引入。
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
import httpx
import asyncio
import json
import os
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from app.config import settings
from app.services.ai_client import post_chat_completion
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
    history: list = Field(default_factory=list)
    business_type: str = "ai_3d_custom"  # ai_3d_custom / video_purchase / digital_art
    user_message_id: str | None = None
    assistant_message_id: str | None = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 初始欢迎
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/start")
async def ai_start(session_id: str):
    """获取对话的初始欢迎语"""
    if settings.AGENT_MODE == "media":
        reply = """您好，我是 Unique Video AI 的项目顾问。

我们是国内裸眼3D视觉内容与数字艺术创意领域的头部服务商，核心团队深耕行业多年，已为众多媒体方客户提供过高品质的裸眼3D视觉内容解决方案。

您可以通过以下方式开始：

**咨询下单** — 描述您的媒体资源与项目需求，由我协助梳理并生成完整需求单
**查看订单** — 查询您名下的订单进展与状态
**了解业务** — 了解我们的服务体系与过往案例

请直接告知您的需求，或通过下方快捷入口进入对应流程。"""
    else:
        reply = """您好，我是 Unique Video AI 的项目顾问。

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

    "2. 【触发完成的严格条件】在输出【需求收集完成】之前，"
    "逐项检查核心必问项的收集情况。"
    "只有当至少5项有了客户的实质性回答后，才可以输出【需求收集完成】标记。"
    "不足5项时必须继续追问。\n\n"

    "3. 满足条件后，简要总结已收集的信息，"
    "在回复的最末尾加上标记：【需求收集完成】。\n\n"

    "4. 【被动结束情况】只有当客户明确表达不想继续时（比如'算了''就这样吧''先这样''回头再说''直接填表吧'），"
    "才可以提前结束。此时总结已收集的信息，指出哪些重要项还缺失，然后加上【需求收集完成】标记。"
    "客户正常回答问题时，不要主动结束。\n\n"

    "5. 保持专业节奏，语言干练精准，不要寒暄客套。\n\n"

    "6. 【上传环节放在最后】文件上传（现场实拍图/参考文件）是需求收集的最后一步。"
    "在核心必问项（1-6项）都已收集之后，再主动询问客户是否有现场实拍图或参考文件需要上传。"
    "告知客户：'核心需求信息已基本收集完毕。最后一步——如果您有现场实拍图、屏幕照片或其他参考素材，"
    "可以通过输入框左侧的上传按钮直接上传。如果暂时没有，我们就可以整理信息了。'\n\n"

    "7. 【文件上传确认】当客户上传了文件（消息中包含'已上传文件'或'已上传'字样）时，"
    "先确认收到文件，然后询问是否还有其他文件需要上传。"
    "如果客户表示没有更多文件了，直接总结所有已收集的信息并输出【需求收集完成】标记。"
    "示例回复：'已收到您上传的文件。请问还有其他参考素材需要上传吗？没有的话，我来为您整理需求信息。'\n\n"

    "8. 如果客户提供的补充内容无法归入上述任何结构化字段，将其完整记录，"
    "在最终提取时归入'备注'字段，确保不遗漏任何客户诉求。"
)

_PROMPT_AI_3D = (
    "你是 Unique Video AI 的资深项目顾问，专注于AI裸眼3D视觉内容定制领域。"
    "你的任务是通过结构化的对话，高效地收集客户的裸眼3D项目需求信息。\n\n"
    + _TONE_RULES +
    "【你需要收集的字段清单】\n"
    "核心必问项（这6项务必逐一主动询问，缺一不可）：\n"
    "1. 品牌与产品关键词 — 客户的品牌名和要推广的产品\n"
    "2. 目标受众 — 这支内容是给谁看的\n"
    "3. 内容需求 — 客户想要什么样的裸眼3D创意画面和场景\n"
    "4. 投放城市或站点 — 在哪个城市/哪块屏投放\n"
    "5. 制作预算 — 预算范围（参考：十万级起步）\n"
    "6. 预计上刊时间 — 什么时候需要上线\n"
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
    "你是 Unique Video AI 的资深项目顾问，专注于裸眼3D成片购买适配服务。"
    "你的任务是通过结构化的对话，高效地收集客户的成片选购与适配需求。\n\n"
    "【业务背景】\n"
    "成片购买适配是从我们的精选模板库中挑选现成的裸眼3D视频，"
    "再根据客户的屏幕尺寸和品牌需求进行适配调整。交付周期约5个工作日，预算万元级。\n\n"
    + _TONE_RULES +
    "【你需要收集的字段清单】\n"
    "核心必问项（这6项务必逐一主动询问，缺一不可）：\n"
    "1. 品牌名称 — 客户的品牌，用于在成片上叠加品牌元素\n"
    "2. 内容偏好 — 客户喜欢什么风格/主题的成片（科技感、自然、动物、抽象等）\n"
    "3. 投放城市与屏幕位置 — 在哪个城市/哪块屏投放\n"
    "4. 屏幕尺寸与分辨率 — 具体的屏幕物理尺寸和分辨率（如 LED 大屏 16:9 等）\n"
    "5. 制作预算 — 预算范围（参考：万元级）\n"
    "6. 预计上刊时间 — 什么时候需要投放\n"
    "7. 现场实拍图 — 主动询问客户是否有现场实拍图或参考文件（如屏幕实景照片等），告知可以通过输入框左侧的上传按钮上传。此项选填，可跳过。\n\n"
    "自然追问项（对话中自然涉及就记录）：\n"
    "8. 投放时长 — 每条视频多少秒\n"
    "9. 购买数量 — 需要几条不同的成片\n"
    "10. 品牌定制需求 — 是否需要在成片上叠加 logo、slogan、产品画面等\n"
    "11. 投放场景 — 户外地标屏、商场内屏、交通枢纽等\n\n"
    + _DIALOG_RULES
)

_PROMPT_DIGITAL_ART = (
    "你是 Unique Video AI 的资深项目顾问，专注于数字艺术内容定制领域。"
    "你的任务是通过结构化的对话，高效地收集客户的数字艺术项目需求信息。\n\n"
    "【业务背景】\n"
    "数字艺术内容定制涵盖数字装置、沉浸式互动体验、创意视觉内容等方向，"
    "适用于展览、发布会、品牌快闪活动、商业空间等场景。交付周期约7个工作日。\n\n"
    + _TONE_RULES +
    "【你需要收集的字段清单】\n"
    "核心必问项（这6项务必逐一主动询问，缺一不可）：\n"
    "1. 品牌/项目名称 — 客户的品牌或项目名称\n"
    "2. 活动场景与用途 — 展览、发布会、快闪店、商业空间等\n"
    "3. 创意方向 — 客户想要什么样的数字艺术内容（互动装置、沉浸式投影、生成式艺术等）\n"
    "4. 场地信息 — 活动场地的位置和空间尺寸\n"
    "5. 制作预算 — 预算范围\n"
    "6. 活动时间 — 什么时候需要交付/布展\n"
    "7. 现场实拍图 — 主动询问客户是否有场地实拍图或其他参考文件（如场地照片、空间平面图等），告知可以通过输入框左侧的上传按钮上传。此项选填，可跳过。\n\n"
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
    "【语气要求】\n"
    "- 专业且有温度，像一位经验丰富且真诚的行业顾问在与客户面对面沟通\n"
    "- 不使用emoji表情符号\n"
    "- 用行业术语体现专业度，但不堆砌术语\n"
    "- 允许使用简短的正面回应（如'好的''明白''了解'），但不要每句话都回应，"
    "大约每2-3轮自然地回应一次即可，避免机械感\n"
    "- 避免过度客套（如'非常感谢您的配合''您太棒了'等），保持自然\n"
    "- 过渡要自然：根据客户上一轮回答的内容自然引出下一个问题，"
    "而不是机械地按列表顺序逐项询问\n\n"
)

_MEDIA_DIALOG_RULES = (
    "【对话规则 — 严格遵守！】\n"
    "1. 每次回复只问一个问题。不要一次性问两三个。"
    "客户回答包含多个信息时，先简要确认，再追问下一个缺失项。"
    "切勿重复问已经问过的问题。\n\n"

    "2. 【提问顺序灵活调整】不需要严格按照字段编号顺序提问。"
    "根据客户的回答自然衔接下一个相关问题。"
    "例如客户提到了城市位置，可以顺势问观看动线；"
    "客户聊到内容主题，可以接着聊艺术方向。"
    "让对话像自然交流，而不是填表。\n\n"

    "3. 【预算放在最后】项目制作预算是敏感话题，"
    "尽量在其他核心信息都已收集之后再询问。"
    "询问时语气要自然委婉，例如：'关于项目预算这块，目前有一个大致的范围吗？"
    "这样我可以帮您匹配最合适的制作方案。'\n\n"

    "4. 【客户可以跳过】如果客户表示某个问题暂时不清楚或不方便回答，"
    "不要追问，自然跳过并进入下一个话题。\n\n"

    "5. 【阶段过渡】对话分为三个阶段，每进入新阶段时用一句话自然过渡：\n"
    "   - 基础信息阶段（项目名称、背景、位置、受众等）\n"
    "   - 创意方向阶段（艺术风格、内容主题、观看动线等）\n"
    "   - 技术与交付阶段（媒体规格、技术需求、审核规范、上刊时间等）\n"
    "过渡示例：'基础信息差不多了，接下来我们聊聊创意方向。'\n\n"

    "6. 【触发完成的严格条件】在输出【需求收集完成】之前，"
    "逐项检查核心必问项的收集情况。"
    "只有当至少8项有了客户的实质性回答后，才可以输出【需求收集完成】标记。"
    "不足8项时必须继续追问。\n\n"

    "7. 满足条件后，简要总结已收集的信息，"
    "在回复的最末尾加上标记：【需求收集完成】。\n\n"

    "8. 【被动结束情况】只有当客户明确表达不想继续时（比如'算了''就这样吧''先这样''回头再说''直接填表吧'），"
    "才可以提前结束。此时总结已收集的信息，指出哪些重要项还缺失，然后加上【需求收集完成】标记。"
    "客户正常回答问题时，不要主动结束。\n\n"

    "9. 【上传环节放在最后】文件上传（现场实拍图/参考文件）是需求收集的最后一步。"
    "在核心必问项都已收集之后，再主动询问客户是否有现场实拍图或参考素材需要上传。"
    "告知客户：'核心需求信息已基本收集完毕。最后——如果您有现场实拍图、屏幕照片或其他参考素材，"
    "可以通过输入框左侧的上传按钮直接上传，我会一并整理到需求文档中。如果暂时没有，我们就可以整理信息了。'\n\n"

    "10. 【文件上传确认】当客户上传了文件（消息中包含'已上传文件'或'已上传'字样）时，"
    "先确认收到文件，然后询问是否还有其他文件需要上传。"
    "如果客户表示没有更多文件了，直接总结所有已收集的信息并输出【需求收集完成】标记。"
    "示例回复：'已收到您上传的文件。请问还有其他参考素材需要上传吗？没有的话，我来为您整理需求信息。'\n\n"

    "如果客户提供的补充内容无法归入任何结构化字段，将其完整记录到'备注'字段。"
)

_PROMPT_MEDIA_3D = (
    "你是 Unique Video AI 的资深项目顾问，在裸眼3D户外媒体内容定制领域有多年的项目经验。"
    "你的任务是通过自然、专业的对话，高效地收集媒体方客户的裸眼3D项目需求信息。\n\n"
    "【业务背景】\n"
    "媒体方客户通常拥有户外大屏、交通枢纽屏幕等媒体资源，需要我们为其定制裸眼3D视觉内容，"
    "以吸引品牌方投放或提升媒体自身的视觉影响力。\n\n"
    + _MEDIA_TONE_RULES +
    "【你需要收集的字段清单】\n"
    "以下字段按三个阶段组织，但实际提问顺序应根据客户回答灵活调整：\n\n"
    "■ 基础信息阶段：\n"
    "1. 项目名称 — 本次项目的名称\n"
    "2. 项目背景 & 媒体简介 — 媒体资源的背景介绍，位置特点、日均客流、目标客群等\n"
    "3. 目标受众 & 场景特点 — 媒体所在场景的受众画像和场景特征\n"
    "4. 投放城市 & 媒体具体位置 — 城市、区域、具体位置，是否位于核心地标/交通枢纽/商圈\n\n"
    "■ 创意方向阶段：\n"
    "5. 观看动线说明 — 观众主要视角、人流方向、最佳观看点\n"
    "6. 整体艺术方向 & 风格偏好 — 未来科技/自然生态/城市文化/抽象艺术/萌系治愈等\n"
    "7. 内容主题 & 核心表达 — 核心概念、内容主题，是否有需要展示的IP形象和品牌露出等\n\n"
    "■ 技术与交付阶段：\n"
    "8. 媒体尺寸 & 物理规格 — 屏幕分辨率、物理尺寸\n"
    "9. 技术需求 — 分辨率最低要求、格式（MP4/无压缩MOV）、帧率/色彩空间/安全区规范\n"
    "10. 素材内容审核规范 & 周期 — 是否有需要规避的内容、是否需提前提交样片审核、审核周期\n"
    "11. 预计上刊时间 — 以项目上刊媒体的最迟提交报审时间为准\n"
    "12. 其他特殊合作要求 — 如需特殊裸眼3D定制效果，需额外沟通制作规范等\n\n"
    "■ 自然追问项（对话中涉及就记录，不必刻意追问）：\n"
    "13. 媒体定位 & 品牌调性 — 高端商圈媒体/交通干线枢纽媒体，适配的品牌类型\n"
    "14. 投放时长 & 数量 — 几支内容、每支多少秒\n"
    "15. 项目制作预算 — 预算范围（放在最后询问）\n\n"
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
            print(f"[AI Chat] Memory 加载失败（不影响对话）: {e}")

    if not settings.AI_API_KEY:
        mock_reply = "【真实后端接口调试中】"
        if _is_mock_completion_message(request.message):
            mock_reply += "核心需求已确认，我将为您整理项目评估与需求明细。 【需求收集完成】"
        elif len(request.message) > 5:
            mock_reply += f"收到您的反馈：{request.message[:10]}... 请问这支内容的投放渠道和大概预算是多少？"
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
        system_prompt = _get_requirement_prompt(request.business_type)

        # 将 Memory 上下文追加到 system prompt
        if memory_context:
            system_prompt += memory_context

        llm_messages = [{"role": "system", "content": system_prompt}]
        for h in request.history:
            if h.get("role") in ["user", "assistant"] and h.get("content"):
                llm_messages.append({"role": h["role"], "content": h["content"]})
        llm_messages.append({"role": "user", "content": request.message})

        data = await post_chat_completion(
            {"model": settings.AI_MODEL_NAME, "messages": llm_messages},
            timeout=30.0,
        )
        reply = data["choices"][0]["message"]["content"]

        _save_session_file(
            session_id=request.session_id, user_id=user_id, username=username,
            history=request.history, user_msg=request.message, assistant_msg=reply,
            user_message_id=request.user_message_id,
            assistant_message_id=request.assistant_message_id,
        )

        # 后台对话学习 — 从对话中提取偏好写回 Memory
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

        return {"message": reply}

    except HTTPException:
        raise
    except Exception as e:
        print(f"大模型调用失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
                "其中 site_photos（现场实拍图）记录客户是否提供了现场照片或参考文件，如有则记录描述信息。\n"
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
            timeout=30.0,
        )
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
                    timeout=30.0,
                )
                assessment = data["choices"][0]["message"]["content"]
                return {"assessment": assessment}
            return {"assessment": ""}
        except Exception as e:
            print(f"媒体方项目评估失败: {e}")
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

        data = await post_chat_completion(
            {
                "model": settings.AI_MODEL_NAME,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"客户需求信息：\n{info}"}
                ]
            },
            timeout=30.0,
        )
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
        from app.utils.knowledge import get_knowledge_file
        cases_path = get_knowledge_file('cases.json')
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
            except IntegrityError:
                await db.rollback()
    except Exception as e:
        print(f"[AI Chat] 数据库保存失败（不影响对话）: {e}")


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
        print(f"[AI Chat] 数据库保存调度失败: {e}")

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
        print(f"AI 会话 JSON 保存失败: {e}")
