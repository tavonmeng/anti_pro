"""订单-承包商派单记录模型"""

from sqlalchemy import Column, String, DateTime, Enum, Text, JSON, ForeignKey
from sqlalchemy.sql import func
import enum
from app.database import Base


class AssignmentStatus(str, enum.Enum):
    """派单状态枚举"""
    PENDING = "pending"              # 待接单
    ACCEPTED = "accepted"            # 已接单
    REJECTED = "rejected"            # 已拒绝
    IN_PROGRESS = "in_progress"      # 进行中（已接单并开始工作）
    COMPLETED = "completed"          # 已完成（所有环节完成）
    CANCELLED = "cancelled"          # 已取消（管理员撤回）


class ContractorAssignment(Base):
    """订单-承包商派单记录

    管理员给承包商派单后创建一条记录。承包商可以接单或拒绝。
    拒绝后管理员可重新派单（给同一人或不同人）。
    当前设计一个订单同时只派给一个承包商。
    """
    __tablename__ = "contractor_assignments"

    id = Column(String(50), primary_key=True, index=True)
    order_id = Column(String(50), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    contractor_id = Column(String(50), nullable=False, index=True)   # 引用 contractors 表
    assigned_by = Column(String(50), nullable=False)                  # 管理员 ID
    status = Column(Enum(AssignmentStatus), nullable=False, default=AssignmentStatus.PENDING)
    reject_reason = Column(Text, nullable=True)                       # 拒绝理由

    # 排期数据（JSON，派单时根据 WorkflowStageConfig 自动生成各环节截止日）
    # 格式: [
    #   {"stage_config_id": "wf_xxx", "name": "方案", "days": 2, "deadline": "2026-05-05", "status": "pending"},
    #   {"stage_config_id": "wf_xxx", "name": "原画", "days": 3, "deadline": "2026-05-08", "status": "pending"},
    #   ...
    # ]
    schedule = Column(JSON, nullable=True)

    # 当前活跃环节序号（管理员手动推进时 +1）
    current_stage_order = Column(String(10), nullable=True, default="1")

    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    responded_at = Column(DateTime(timezone=True), nullable=True)     # 接单/拒绝时间
    completed_at = Column(DateTime(timezone=True), nullable=True)     # 全部完成时间

    def __repr__(self):
        return f"<ContractorAssignment(id={self.id}, order={self.order_id}, status={self.status})>"
