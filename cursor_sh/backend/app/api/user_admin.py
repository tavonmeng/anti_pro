"""管理员管理用户邀请 API 路由"""

from datetime import timedelta
from typing import Optional
import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.user_invitation import UserInvitation
from app.models.user_memory import UserMemory
from app.schemas.response import ApiResponse
from app.utils.business_log import log_business_event
from app.utils.dependencies import AnyUser, require_admin
from app.utils.log_setup import get_module_logger
from app.utils.timezone import beijing_iso, beijing_now, ensure_beijing
from app.utils.validators import generate_id

router = APIRouter(prefix="/user-admin", tags=["用户管理（管理端）"])
logger = get_module_logger("auth")


def _user_site_base_url() -> str:
    return (settings.USER_SITE_BASE_URL or "https://www.uniquevisionx.com").rstrip("/")


def _user_invite_url(token: str) -> str:
    return f"{_user_site_base_url()}/?invite={token}"


class UserInvitationCreate(BaseModel):
    company_name: Optional[str] = None
    memory_user_id: Optional[str] = None
    note: Optional[str] = None
    expires_days: int = 7


@router.post("/invitations")
async def create_user_invitation(
    data: UserInvitationCreate,
    current_user: AnyUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """生成普通用户邀请链接"""
    try:
        memory_user_id = (data.memory_user_id or "").strip() or None
        if memory_user_id:
            result = await db.execute(select(UserMemory).where(UserMemory.user_id == memory_user_id))
            if not result.scalar_one_or_none():
                raise HTTPException(status_code=404, detail="选择的用户 Memory 不存在")

        token = secrets.token_urlsafe(32)
        invitation = UserInvitation(
            id=generate_id("invite"),
            token=token,
            created_by=current_user.id,
            company_name=(data.company_name or "").strip() or None,
            memory_user_id=memory_user_id,
            note=(data.note or "").strip() or None,
            expires_at=beijing_now() + timedelta(days=7),
            is_used=False,
        )
        db.add(invitation)
        await db.commit()
        await db.refresh(invitation)

        log_business_event(
            logger,
            "user_invitation_created",
            admin_id=current_user.id,
            invitation_id=invitation.id,
            expires_at=beijing_iso(invitation.expires_at),
            has_memory=bool(memory_user_id),
            has_company=bool(invitation.company_name),
        )

        return ApiResponse(code=201, message="邀请链接生成成功", data={
            "id": invitation.id,
            "token": token,
            "inviteUrl": _user_invite_url(token),
            "companyName": invitation.company_name,
            "memoryUserId": invitation.memory_user_id,
            "note": invitation.note,
            "expiresAt": beijing_iso(invitation.expires_at),
            "isUsed": False,
            "createdAt": beijing_iso(invitation.created_at),
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试") from e


@router.get("/invitations")
async def get_user_invitations(
    current_user: AnyUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取普通用户邀请链接列表"""
    try:
        result = await db.execute(select(UserInvitation).order_by(UserInvitation.created_at.desc()))
        invitations = result.scalars().all()

        items = []
        for inv in invitations:
            used_by_name = None
            if inv.used_by:
                user_result = await db.execute(select(User).where(User.id == inv.used_by))
                user = user_result.scalar_one_or_none()
                if user:
                    used_by_name = user.username

            memory_label = None
            if inv.memory_user_id:
                memory_result = await db.execute(select(UserMemory).where(UserMemory.user_id == inv.memory_user_id))
                memory = memory_result.scalar_one_or_none()
                if memory:
                    ci = memory.company_info or {}
                    memory_label = ci.get("contact_name") or ci.get("name") or inv.memory_user_id

            expires_at = ensure_beijing(inv.expires_at)
            is_expired = expires_at < beijing_now() if expires_at else False
            items.append({
                "id": inv.id,
                "token": inv.token,
                "inviteUrl": _user_invite_url(inv.token),
                "companyName": inv.company_name,
                "memoryUserId": inv.memory_user_id,
                "memoryLabel": memory_label,
                "note": inv.note,
                "isUsed": inv.is_used,
                "isExpired": is_expired,
                "usedBy": inv.used_by,
                "usedByName": used_by_name,
                "expiresAt": beijing_iso(inv.expires_at),
                "createdAt": beijing_iso(inv.created_at),
            })

        return ApiResponse(code=200, message="获取成功", data=items)
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试") from e


@router.delete("/invitations/{invitation_id}")
async def revoke_user_invitation(
    invitation_id: str,
    current_user: AnyUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """撤销未使用的普通用户邀请链接"""
    try:
        result = await db.execute(select(UserInvitation).where(UserInvitation.id == invitation_id))
        invitation = result.scalar_one_or_none()
        if not invitation:
            raise HTTPException(status_code=404, detail="邀请链接不存在")
        if invitation.is_used:
            raise HTTPException(status_code=400, detail="该邀请链接已被使用，无法撤销")

        await db.delete(invitation)
        await db.commit()
        return ApiResponse(code=200, message="邀请链接已撤销", data=None)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试") from e
