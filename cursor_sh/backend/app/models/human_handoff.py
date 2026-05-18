"""转人工客户记录模型。"""

from sqlalchemy import Column, String, Integer, Text, DateTime, JSON, UniqueConstraint
from sqlalchemy.sql import func

from app.database import Base
from app.utils.validators import generate_id


HANDOFF_STATUSES = {"pending", "followed"}


class HumanHandoff(Base):
    """用户触发转人工后的 CRM 队列记录。"""

    __tablename__ = "human_handoffs"
    __table_args__ = (
        UniqueConstraint("session_id", name="uq_human_handoff_session"),
    )

    id = Column(String(50), primary_key=True, default=lambda: generate_id("handoff"))
    user_id = Column(String(50), nullable=False, index=True)
    username = Column(String(100), nullable=True)
    session_id = Column(String(50), nullable=False, index=True)
    draft_order_id = Column(String(50), nullable=True, index=True)
    business_type = Column(String(30), default="ai_3d_custom", nullable=False)
    status = Column(String(20), default="pending", nullable=False, index=True)
    trigger_message = Column(Text, nullable=False)
    chat_snapshot = Column(JSON, nullable=False, default=list)
    extracted_data = Column(JSON, nullable=True)
    message_count = Column(Integer, default=0, nullable=False)
    followed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
