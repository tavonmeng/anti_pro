"""工作流环节全局配置模型"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from app.database import Base


class WorkflowStageConfig(Base):
    """工作流环节全局配置（管理员可编辑名称、天数、审核项）

    默认环节：方案(2天) → 原画(3天) → 模型(4天) → 渲染(3天) → 成片(3天)
    管理员可以新增、删除、修改各环节的名称和天数，也可以调整排列顺序。
    """
    __tablename__ = "workflow_stage_configs"

    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(50), nullable=False)               # 环节名称，如"方案"、"原画"
    default_days = Column(Integer, nullable=False)            # 默认工作日天数
    display_order = Column(Integer, nullable=False)           # 排列顺序（1, 2, 3 ...）
    # 审核项列表，如: ["内容安全合规性","风格与品牌调性一致","技术规格达标","无版权/商标侵权风险"]
    review_items = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<WorkflowStageConfig(id={self.id}, name={self.name}, days={self.default_days})>"
