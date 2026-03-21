"""
消息通知相关Schema
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.notification import NotificationType


class NotificationCreate(BaseModel):
    """创建消息通知"""
    user_id: str
    order_id: Optional[str] = None
    type: NotificationType
    title: str
    content: str


class NotificationResponse(BaseModel):
    """消息通知响应"""
    id: str
    user_id: str
    order_id: Optional[str] = None
    type: str
    title: str
    content: str
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NotificationList(BaseModel):
    """消息列表响应"""
    items: List[NotificationResponse]
    total: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    """未读消息数量响应"""
    unread_count: int

