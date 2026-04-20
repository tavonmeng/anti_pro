"""消息通知 API 路由"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database import get_db
from app.schemas.notification import NotificationResponse, NotificationList, UnreadCountResponse
from app.schemas.response import ApiResponse
from app.services.notification_service import NotificationService
from app.utils.dependencies import get_current_user, AnyUser

router = APIRouter(prefix="/notifications", tags=["消息通知"])


@router.get("", response_model=ApiResponse[NotificationList])
async def get_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    current_user: AnyUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取当前用户的消息列表"""
    notifications, total = await NotificationService.get_user_notifications(
        db, current_user.id, skip, limit, unread_only
    )
    
    unread_count = await NotificationService.get_unread_count(db, current_user.id)
    
    notification_responses = [
        NotificationResponse.model_validate(notification)
        for notification in notifications
    ]
    
    result = NotificationList(
        items=notification_responses,
        total=total,
        unread_count=unread_count
    )
    
    return ApiResponse(code=200, message="获取成功", data=result)


@router.get("/unread-count", response_model=ApiResponse[UnreadCountResponse])
async def get_unread_count(
    current_user: AnyUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取未读消息数量"""
    unread_count = await NotificationService.get_unread_count(db, current_user.id)
    result = UnreadCountResponse(unread_count=unread_count)
    return ApiResponse(code=200, message="获取成功", data=result)


@router.put("/{notification_id}/read", response_model=ApiResponse[NotificationResponse])
async def mark_notification_as_read(
    notification_id: str,
    current_user: AnyUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """标记消息为已读"""
    notification = await NotificationService.mark_as_read(
        db, notification_id, current_user.id
    )
    return ApiResponse(
        code=200,
        message="标记成功",
        data=NotificationResponse.model_validate(notification)
    )


@router.put("/read-all", response_model=ApiResponse[dict])
async def mark_all_as_read(
    current_user: AnyUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """标记所有消息为已读"""
    count = await NotificationService.mark_all_as_read(db, current_user.id)
    return ApiResponse(
        code=200,
        message=f"已标记{count}条消息为已读",
        data={"count": count}
    )


@router.delete("/{notification_id}", response_model=ApiResponse[None])
async def delete_notification(
    notification_id: str,
    current_user: AnyUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除消息"""
    await NotificationService.delete_notification(db, notification_id, current_user.id)
    return ApiResponse(code=200, message="删除成功", data=None)

