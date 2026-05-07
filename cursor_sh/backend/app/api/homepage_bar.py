"""Homepage marketing bar API."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.schemas.response import ApiResponse
from app.schemas.homepage_bar import HomepageBarResponse, HomepageBarUpdate
from app.services.homepage_bar_service import HomepageBarService
from app.utils.dependencies import require_admin, AnyUser

router = APIRouter(prefix="/homepage-bar", tags=["官网运营条"])


@router.get("/public", response_model=ApiResponse[Optional[HomepageBarResponse]])
async def get_public_homepage_bar(db: AsyncSession = Depends(get_db)):
    """Public homepage reads the active marketing bar."""
    bar = await HomepageBarService.get_public(db)
    return ApiResponse(code=200, message="获取成功", data=bar)


@router.get("", response_model=ApiResponse[HomepageBarResponse])
async def get_homepage_bar(
    current_user: AnyUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin reads the editable marketing bar config."""
    bar = await HomepageBarService.get_or_create(db, current_user.id)
    return ApiResponse(code=200, message="获取成功", data=bar)


@router.put("", response_model=ApiResponse[HomepageBarResponse])
async def update_homepage_bar(
    data: HomepageBarUpdate,
    current_user: AnyUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin updates the homepage marketing bar config."""
    bar = await HomepageBarService.update(db, data, current_user.id)
    return ApiResponse(code=200, message="更新成功", data=bar)
