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
    """消息通知模型
    
    user_id 不再使用外键约束，因为通知可能发给 admins/staff_members/users 三张表中的任意用户。
    通过 user_id 的前缀（admin-/staff-/user-）可判断所属表。
    """
    __tablename__ = "notifications"

    id = Column(String(50), primary_key=True, default=lambda: generate_id("notif"))
    user_id = Column(String(50), nullable=False, index=True)  # 不再有 FK，支持三表
    order_id = Column(String(50), nullable=True, index=True)
    type = Column(SQLEnum(NotificationType), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    read_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<Notification {self.id} - {self.type.value} - User {self.user_id}>"
