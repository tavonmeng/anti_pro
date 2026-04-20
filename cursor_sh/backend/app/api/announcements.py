from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database import get_db
from app.schemas.response import ApiResponse
from app.schemas.announcement import AnnouncementCreate, AnnouncementUpdate, AnnouncementResponse
from app.services.announcement_service import AnnouncementService
from app.utils.dependencies import get_current_user, require_admin, AnyUser
from app.models.user import UserRole

router = APIRouter(prefix="/announcements", tags=["公告"])

@router.get("", response_model=ApiResponse[List[AnnouncementResponse]])
async def get_announcements(
    active_only: bool = Query(True, description="是否仅获取激活的公告（普通用户应为True，管理员可为False）"),
    current_user: AnyUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取公告列表"""
    # 只有管理员可以查看所有公告（包括非激活的）
    if not active_only and current_user.role != UserRole.ADMIN:
        active_only = True
        
    try:
        announcements = await AnnouncementService.get_all_announcements(db, active_only)
        return ApiResponse(code=200, message="获取成功", data=announcements)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("", response_model=ApiResponse[AnnouncementResponse])
async def create_announcement(
    data: AnnouncementCreate,
    current_user: AnyUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """创建公告（仅管理员）"""
    try:
        announcement = await AnnouncementService.create_announcement(db, data, current_user.id)
        return ApiResponse(code=201, message="创建成功", data=announcement)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{announcement_id}", response_model=ApiResponse[AnnouncementResponse])
async def update_announcement(
    announcement_id: str,
    data: AnnouncementUpdate,
    current_user: AnyUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """更新公告（仅管理员）"""
    try:
        announcement = await AnnouncementService.update_announcement(db, announcement_id, data)
        return ApiResponse(code=200, message="更新成功", data=announcement)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{announcement_id}", response_model=ApiResponse[dict])
async def delete_announcement(
    announcement_id: str,
    current_user: AnyUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """删除公告（仅管理员）"""
    try:
        await AnnouncementService.delete_announcement(db, announcement_id)
        return ApiResponse(code=200, message="删除成功", data={"id": announcement_id})
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
