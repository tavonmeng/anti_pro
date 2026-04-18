"""
消息通知模型
"""
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from enum import Enum
from app.database import Base
from app.utils.validators import generate_id


class NotificationType(str, Enum):
    """消息类型枚举"""
    ORDER_STATUS_CHANGED = "order_status_changed"  # 订单状态变更
    ORDER_ASSIGNED = "order_assigned"  # 订单分配
    ORDER_REASSIGNED = "order_reassigned"  # 订单重新分配
    NEW_FEEDBACK = "new_feedback"  # 新反馈
    PREVIEW_READY = "preview_ready"  # 预览文件就绪
    ORDER_COMPLETED = "order_completed"  # 订单完成
    ORDER_CANCELLED = "order_cancelled"  # 订单取消
    REVISION_NEEDED = "revision_needed"  # 需要修改
    PREVIEW_REVIEW_REQUIRED = "preview_review_required"  # 预览待审核
    PREVIEW_REVIEW_APPROVED = "preview_review_approved"  # 预览审核通过
    PREVIEW_REVIEW_REJECTED = "preview_review_rejected"  # 预览审核拒绝


class Notification(Base):
    """消息通知模型"""
    __tablename__ = "notifications"

    id = Column(String(50), primary_key=True, default=lambda: generate_id("notif"))
    user_id = Column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id = Column(String(50), ForeignKey("orders.id", ondelete="CASCADE"), nullable=True, index=True)
    type = Column(SQLEnum(NotificationType), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    read_at = Column(DateTime, nullable=True)

    # 关系
    user = relationship("User", back_populates="notifications", lazy="selectin")
    order = relationship("Order", back_populates="notifications", lazy="selectin")

    def __repr__(self):
        return f"<Notification {self.id} - {self.type.value} - User {self.user_id}>"

