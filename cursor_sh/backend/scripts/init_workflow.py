"""工作流环节默认配置种子数据（启动时幂等写入）"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.workflow import WorkflowStageConfig
from app.utils.validators import generate_id


# 默认工作流环节配置
DEFAULT_STAGES = [
    {
        "name": "方案",
        "default_days": 2,
        "display_order": 1,
        "review_items": ["内容安全合规性", "风格与品牌调性一致", "技术规格达标", "无版权/商标侵权风险"]
    },
    {
        "name": "原画",
        "default_days": 3,
        "display_order": 2,
        "review_items": ["内容安全合规性", "风格与品牌调性一致", "技术规格达标", "无版权/商标侵权风险"]
    },
    {
        "name": "模型",
        "default_days": 4,
        "display_order": 3,
        "review_items": ["内容安全合规性", "风格与品牌调性一致", "技术规格达标", "无版权/商标侵权风险"]
    },
    {
        "name": "渲染",
        "default_days": 3,
        "display_order": 4,
        "review_items": ["内容安全合规性", "风格与品牌调性一致", "技术规格达标", "无版权/商标侵权风险"]
    },
    {
        "name": "成片",
        "default_days": 3,
        "display_order": 5,
        "review_items": ["内容安全合规性", "风格与品牌调性一致", "技术规格达标", "无版权/商标侵权风险"]
    },
]


async def ensure_workflow_stages(db: AsyncSession):
    """确保默认工作流环节存在（幂等操作，仅在表为空时写入）"""
    result = await db.execute(
        select(WorkflowStageConfig).limit(1)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        # 已有配置，不覆盖
        return
    
    for stage_data in DEFAULT_STAGES:
        stage = WorkflowStageConfig(
            id=generate_id("wf"),
            name=stage_data["name"],
            default_days=stage_data["default_days"],
            display_order=stage_data["display_order"],
            review_items=stage_data["review_items"],
            is_active=True
        )
        db.add(stage)
    
    await db.commit()
    print("✅ 默认工作流环节配置已初始化（方案/原画/模型/渲染/成片）")
