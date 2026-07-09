"""内部负责人制作任务模型"""

import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, JSON, String

from app.database import Base
from app.utils.timezone import beijing_now


class StaffAssignmentStatus(str, enum.Enum):
    """内部负责人制作任务状态。"""

    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class StaffAssignment(Base):
    """订单-内部负责人制作任务。

    内部负责人由管理员直接分配，不存在接单/拒单流程。
    """

    __tablename__ = "staff_assignments"

    id = Column(String(50), primary_key=True, index=True)
    order_id = Column(String(50), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    staff_id = Column(String(50), nullable=False, index=True)
    assigned_by = Column(String(50), nullable=False)
    status = Column(Enum(StaffAssignmentStatus), nullable=False, default=StaffAssignmentStatus.IN_PROGRESS)
    schedule = Column(JSON, nullable=True)
    current_stage_order = Column(String(10), nullable=True, default="1")

    assigned_at = Column(DateTime(timezone=True), default=beijing_now)
    responded_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=beijing_now)
    updated_at = Column(DateTime(timezone=True), default=beijing_now, onupdate=beijing_now)

    def __repr__(self):
        return f"<StaffAssignment(id={self.id}, order={self.order_id}, staff={self.staff_id}, status={self.status})>"
