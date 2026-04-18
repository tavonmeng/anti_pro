"""反馈相关 Schema"""

from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from app.models.feedback import FeedbackType


class FeedbackCreate(BaseModel):
    """反馈创建模型"""
    type: FeedbackType
    content: str


class FeedbackResponse(BaseModel):
    """反馈响应模型"""
    id: str
    orderId: str
    content: str
    type: FeedbackType
    createdAt: datetime
    createdBy: str
    createdByName: Optional[str] = None
    
    class Config:
        from_attributes = True


from typing import Optional

