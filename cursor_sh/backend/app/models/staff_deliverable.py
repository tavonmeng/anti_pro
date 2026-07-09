"""内部负责人交付物模型"""

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, JSON, String, Text

from app.database import Base
from app.models.contractor_deliverable import DeliverableStatus
from app.utils.timezone import beijing_now


class StaffDeliverable(Base):
    """内部负责人交付物，字段与 contractor 交付物保持一致但物理表拆开。"""

    __tablename__ = "staff_deliverables"

    id = Column(String(50), primary_key=True, index=True)
    assignment_id = Column(
        String(50),
        ForeignKey("staff_assignments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage_config_id = Column(String(50), nullable=False)
    stage_name = Column(String(50), nullable=False)
    stage_order = Column(Integer, nullable=False)

    version = Column(Integer, nullable=False, default=1)
    parent_id = Column(String(50), nullable=True)

    files = Column(JSON, nullable=True)
    description = Column(Text, nullable=True)
    self_review_checks = Column(JSON, nullable=True)

    status = Column(Enum(DeliverableStatus), nullable=False, default=DeliverableStatus.DRAFT)

    admin_review_note = Column(Text, nullable=True)
    admin_reviewed_by = Column(String(50), nullable=True)
    admin_reviewed_at = Column(DateTime(timezone=True), nullable=True)

    is_published_to_user = Column(Boolean, default=False)
    published_note = Column(Text, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    published_by = Column(String(50), nullable=True)

    admin_comments = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), default=beijing_now)
    updated_at = Column(DateTime(timezone=True), default=beijing_now, onupdate=beijing_now)

    def __repr__(self):
        return f"<StaffDeliverable(id={self.id}, stage={self.stage_name}, v{self.version}, status={self.status})>"
