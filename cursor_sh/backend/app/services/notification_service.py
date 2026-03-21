"""
消息通知服务
"""
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from fastapi import HTTPException, status

from app.models.notification import Notification, NotificationType
from app.models.user import User
from app.schemas.notification import NotificationCreate, NotificationResponse


class NotificationService:
    """消息通知服务类"""

    @staticmethod
    async def create_notification(
        db: AsyncSession,
        user_id: str,
        notification_type: NotificationType,
        title: str,
        content: str,
        order_id: Optional[str] = None
    ) -> Notification:
        """
        创建消息通知
        
        Args:
            db: 数据库会话
            user_id: 接收用户ID
            notification_type: 消息类型
            title: 消息标题
            content: 消息内容
            order_id: 关联订单ID（可选）
            
        Returns:
            Notification: 创建的消息通知对象
        """
        notification = Notification(
            user_id=user_id,
            order_id=order_id,
            type=notification_type,
            title=title,
            content=content,
            is_read=False
        )
        
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        
        return notification

    @staticmethod
    async def create_notification_for_multiple_users(
        db: AsyncSession,
        user_ids: List[str],
        notification_type: NotificationType,
        title: str,
        content: str,
        order_id: Optional[str] = None
    ) -> List[Notification]:
        """
        为多个用户创建消息通知
        
        Args:
            db: 数据库会话
            user_ids: 接收用户ID列表
            notification_type: 消息类型
            title: 消息标题
            content: 消息内容
            order_id: 关联订单ID（可选）
            
        Returns:
            List[Notification]: 创建的消息通知对象列表
        """
        notifications = []
        for user_id in user_ids:
            notification = Notification(
                user_id=user_id,
                order_id=order_id,
                type=notification_type,
                title=title,
                content=content,
                is_read=False
            )
            notifications.append(notification)
            db.add(notification)
        
        await db.commit()
        for notification in notifications:
            await db.refresh(notification)
        
        return notifications

    @staticmethod
    async def get_user_notifications(
        db: AsyncSession,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
        unread_only: bool = False
    ) -> tuple[List[Notification], int]:
        """
        获取用户的消息列表
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            skip: 跳过的记录数
            limit: 返回的记录数
            unread_only: 是否只返回未读消息
            
        Returns:
            tuple: (消息列表, 总数)
        """
        # 构建查询条件
        conditions = [Notification.user_id == user_id]
        if unread_only:
            conditions.append(Notification.is_read == False)
        
        # 查询消息列表
        query = select(Notification).where(
            and_(*conditions)
        ).order_by(Notification.created_at.desc()).offset(skip).limit(limit)
        
        result = await db.execute(query)
        notifications = result.scalars().all()
        
        # 查询总数
        count_query = select(func.count(Notification.id)).where(and_(*conditions))
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0
        
        return list(notifications), total

    @staticmethod
    async def get_unread_count(db: AsyncSession, user_id: str) -> int:
        """
        获取用户的未读消息数量
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            
        Returns:
            int: 未读消息数量
        """
        query = select(func.count(Notification.id)).where(
            and_(
                Notification.user_id == user_id,
                Notification.is_read == False
            )
        )
        result = await db.execute(query)
        count = result.scalar() or 0
        return count

    @staticmethod
    async def mark_as_read(
        db: AsyncSession,
        notification_id: str,
        user_id: str
    ) -> Notification:
        """
        标记消息为已读
        
        Args:
            db: 数据库会话
            notification_id: 消息ID
            user_id: 用户ID（用于权限验证）
            
        Returns:
            Notification: 更新后的消息通知对象
        """
        query = select(Notification).where(Notification.id == notification_id)
        result = await db.execute(query)
        notification = result.scalar_one_or_none()
        
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="消息不存在"
            )
        
        # 验证权限
        if notification.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此消息"
            )
        
        # 更新为已读
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(notification)
        
        return notification

    @staticmethod
    async def mark_all_as_read(db: AsyncSession, user_id: str) -> int:
        """
        标记所有消息为已读
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            
        Returns:
            int: 更新的消息数量
        """
        from sqlalchemy import update
        
        stmt = update(Notification).where(
            and_(
                Notification.user_id == user_id,
                Notification.is_read == False
            )
        ).values(
            is_read=True,
            read_at=datetime.now(timezone.utc)
        )
        
        result = await db.execute(stmt)
        await db.commit()
        
        return result.rowcount

    @staticmethod
    async def delete_notification(
        db: AsyncSession,
        notification_id: str,
        user_id: str
    ) -> None:
        """
        删除消息
        
        Args:
            db: 数据库会话
            notification_id: 消息ID
            user_id: 用户ID（用于权限验证）
        """
        query = select(Notification).where(Notification.id == notification_id)
        result = await db.execute(query)
        notification = result.scalar_one_or_none()
        
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="消息不存在"
            )
        
        # 验证权限
        if notification.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此消息"
            )
        
        await db.delete(notification)
        await db.commit()

