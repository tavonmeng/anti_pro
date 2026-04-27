"""承包商交付物模型"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Enum, Text, JSON, ForeignKey
from sqlalchemy.sql import func
import enum
from app.database import Base


class DeliverableStatus(str, enum.Enum):
    """交付物状态枚举"""
    DRAFT = "draft"                          # 草稿（contractor 暂存未提交）
    SUBMITTED = "submitted"                  # 已提交待管理员审核
    ADMIN_APPROVED = "admin_approved"        # 管理员审核通过
    ADMIN_REJECTED = "admin_rejected"        # 管理员审核拒绝（需重新上传）


class ContractorDeliverable(Base):
    """承包商交付物（每个工作流环节可有多条记录，支持版本历史）

    Contractor 在每个环节上传文件和文字说明，逐项勾选自审核检查项后提交。
    管理员审核通过后，可选择将该交付物推送给用户（添加备注）。
    如果驳回，contractor 需重新上传（新版本），旧版本保留在历史中。
    """
    __tablename__ = "contractor_deliverables"

    id = Column(String(50), primary_key=True, index=True)
    assignment_id = Column(String(50), ForeignKey("contractor_assignments.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    stage_config_id = Column(String(50), nullable=False)        # 引用 workflow_stage_configs.id
    stage_name = Column(String(50), nullable=False)              # 冗余存储环节名称（防止配置修改后丢失）
    stage_order = Column(Integer, nullable=False)                 # 冗余存储排列顺序

    # 版本管理
    version = Column(Integer, nullable=False, default=1)          # 版本号（1, 2, 3...）
    parent_id = Column(String(50), nullable=True)                  # 指向上一版本（被退回的交付物 ID）

    # 交付内容
    # 文件列表: [{"name": "方案V2.pdf", "url": "/uploads/xxx", "size": 1234, "mime_type": "application/pdf"}]
    files = Column(JSON, nullable=True)
    description = Column(Text, nullable=True)                      # 文字说明

    # Contractor 自审核检查项（逐项勾选，全部通过才能提交）
    # {"内容安全合规性": true, "风格与品牌调性一致": true, "技术规格达标": false, ...}
    self_review_checks = Column(JSON, nullable=True)

    status = Column(Enum(DeliverableStatus), nullable=False, default=DeliverableStatus.DRAFT)

    # 管理员审核
    admin_review_note = Column(Text, nullable=True)               # 管理员审核备注/驳回理由
    admin_reviewed_by = Column(String(50), nullable=True)         # 审核的管理员 ID
    admin_reviewed_at = Column(DateTime(timezone=True), nullable=True)

    # 发布给用户（管理员审核通过后手动决定是否推送）
    is_published_to_user = Column(Boolean, default=False)
    published_note = Column(Text, nullable=True)                   # 管理员可修改备注后发给用户
    published_at = Column(DateTime(timezone=True), nullable=True)
    published_by = Column(String(50), nullable=True)               # 执行推送的管理员 ID

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<ContractorDeliverable(id={self.id}, stage={self.stage_name}, v{self.version}, status={self.status})>"
