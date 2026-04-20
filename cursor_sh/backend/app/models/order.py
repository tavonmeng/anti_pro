"""订单模型"""

from sqlalchemy import Column, String, Integer, DateTime, Enum, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class OrderType(str, enum.Enum):
    """订单类型枚举"""
    VIDEO_PURCHASE = "video_purchase"
    AI_3D_CUSTOM = "ai_3d_custom"
    DIGITAL_ART = "digital_art"


class OrderStatus(str, enum.Enum):
    """订单状态枚举"""
    DRAFT = "draft"                        # 草稿
    PENDING_ASSIGN = "pending_assign"      # 待分配
    IN_PRODUCTION = "in_production"        # 制作中
    PENDING_REVIEW = "pending_review"      # 待审核
    PREVIEW_READY = "preview_ready"        # 初稿预览
    REVIEW_REJECTED = "review_rejected"    # 审核拒绝
    REVISION_NEEDED = "revision_needed"    # 需要修改
    FINAL_PREVIEW = "final_preview"        # 终稿预览
    COMPLETED = "completed"                # 已完成
    CANCELLED = "cancelled"                # 已取消


class OrderAssignee(Base):
    """订单-负责人关联模型
    
    assignee_id 引用 staff_members 表（设计师/负责人）。
    不使用 FK 约束以避免跨表依赖问题。
    """
    __tablename__ = "order_assignees"
    __table_args__ = (
        UniqueConstraint('order_id', 'assignee_id', name='uq_order_assignee'),
    )
    
    order_id = Column(String(50), ForeignKey("orders.id", ondelete="CASCADE"), primary_key=True)
    assignee_id = Column(String(50), primary_key=True)  # 引用 staff_members 表，不用 FK
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<OrderAssignee(order_id={self.order_id}, assignee_id={self.assignee_id})>"


class Order(Base):
    """订单模型"""
    __tablename__ = "orders"
    
    id = Column(String(50), primary_key=True, index=True)
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    order_type = Column(Enum(OrderType), nullable=False, index=True)
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING_ASSIGN, index=True)
    
    # 用户关联（客户 ID，引用 users 表，但不用 FK 以简化三表架构）
    user_id = Column(String(50), nullable=False, index=True)
    
    # 修改次数
    revision_count = Column(Integer, default=0)
    
    # 订单特定数据（JSON 存储不同类型订单的特定字段）
    order_data = Column(JSON, nullable=False)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 关系（保留文件和反馈的 ORM 关系，移除 user/assignee 的 ORM 关系）
    files = relationship("File", back_populates="order", cascade="all, delete-orphan", lazy="selectin")
    feedbacks = relationship("Feedback", back_populates="order", cascade="all, delete-orphan", lazy="selectin")
    
    def __repr__(self):
        return f"<Order(id={self.id}, order_number={self.order_number}, type={self.order_type}, status={self.status})>"
