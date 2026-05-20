"""Platform service metadata shared by AI routing and handoff flows."""

from __future__ import annotations


ORDERABLE_BUSINESS_TYPES = {"video_purchase", "ai_3d_custom", "digital_art"}
CONSULTATION_BUSINESS_TYPES = {"motion_content", "media_post_production", "campaign_analytics"}
VALID_BUSINESS_TYPES = ORDERABLE_BUSINESS_TYPES | CONSULTATION_BUSINESS_TYPES

BUSINESS_TYPE_LABELS = {
    "video_purchase": "3D OOH数字内容资源库",
    "ai_3d_custom": "AI驱动3D OOH内容定制",
    "digital_art": "数字艺术与沉浸式视觉设计",
    "motion_content": "广告视觉与动态影像制作",
    "media_post_production": "户外媒体后期制作服务",
    "campaign_analytics": "广告投放分析与效果报告",
}

BUSINESS_TYPE_DESCRIPTIONS = {
    "video_purchase": "Ready-to-Deploy 3D DOOH Assets：即用型裸眼3D数字内容资产；Screen-Adaptive Content Packages：多屏适配内容方案；Global Landmark Screen Formats：全球地标大屏内容规格适配。",
    "ai_3d_custom": "AI-Based Creative Development：AI创意内容开发；Site-Specific 3D Screen Adaptation：场景化裸眼3D空间适配；Real-World Playback Simulation：真实环境播放模拟；End-to-End DOOH Content Production：一站式DOOH内容制作。",
    "digital_art": "Art Direction & Visual Design：艺术指导与视觉设计；Virtual Installation Art：虚拟装置艺术；Immersive Spatial Visuals：沉浸式空间视觉；Experimental Digital Art Content：实验性数字艺术内容。",
    "motion_content": "Static Advertising Visuals：平面广告视觉设计；TVC Production：TVC广告影片制作；FOOH Campaign Content：FOOH数字传播内容；VJ Visual Performance Content：VJ视觉演出内容；Motion Graphic Design：动态视觉设计。",
    "media_post_production": "High-End Retouching：高端精修图像处理；Cinematic Video Finishing：电影级视频精修；CGI Enhancement：CGI视觉增强；Commercial Photography & Filming：商业摄影与视频拍摄；Drone Cinematography：航拍影像制作。",
    "campaign_analytics": "DOOH Campaign Analytics：DOOH广告投放数据分析；Audience Performance Reports：受众效果分析报告；Visual Impact Assessment：视觉传播效果评估；Downloadable Data Reports：可下载数据报告系统。",
}


def is_consultation_business_type(business_type: str) -> bool:
    return business_type in CONSULTATION_BUSINESS_TYPES


def is_orderable_business_type(business_type: str) -> bool:
    return business_type in ORDERABLE_BUSINESS_TYPES


def get_business_type_label(business_type: str) -> str:
    return BUSINESS_TYPE_LABELS.get(business_type, business_type or "未知业务")


def get_consultation_intro(business_type: str) -> str:
    label = get_business_type_label(business_type)
    description = BUSINESS_TYPE_DESCRIPTIONS.get(business_type, "这个业务需要由项目顾问结合具体场景评估。")
    return (
        f"您咨询的是「{label}」。\n\n"
        f"{description}\n\n"
        "这个板块目前建议由项目顾问结合具体场景进一步确认需求、报价与排期。"
        "如果您愿意，我可以把当前聊天记录同步给后台顾问，由人工继续跟进。"
        "您回复“转人工”或“联系顾问”即可。"
    )
