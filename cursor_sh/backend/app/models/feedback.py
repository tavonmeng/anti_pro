"""反馈模型"""

from sqlalchemy import Column, String, Text, DateTime, Enum, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class FeedbackType(str, enum.Enum):
    """反馈类型枚举"""
    APPROVAL = "approval"      # 确认通过
    REVISION = "revision"      # 需要修改


class Feedback(Base):
    """反馈模型"""
    __tablename__ = "feedbacks"
    
    id = Column(String(50), primary_key=True, index=True)
    order_id = Column(String(50), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    type = Column(Enum(FeedbackType), nullable=False)
    created_by = Column(String(50), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系（使用 selectin 加载策略，兼容异步上下文）
    order = relationship("Order", back_populates="feedbacks", lazy="selectin")
    
    def __repr__(self):
        return f"<Feedback(id={self.id}, order_id={self.order_id}, type={self.type})>"

