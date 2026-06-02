"""认证 API 路由"""

import os
import re
import uuid

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database import get_db
from app.models.user import User, EnterpriseStatus
from app.schemas.auth import (
    LoginRequest, RegisterRequest, LoginResponse, 
    ChangePasswordRequest, SendSmsRequest, ResetPasswordRequest
)
from app.schemas.response import ApiResponse
from app.services.auth_service import login, register, change_password, reset_password, validate_user_invitation
from app.services.sms_service import send_sms_verify_code, verify_sms_code
from app.utils.dependencies import get_current_user_for_public_deployment, AnyUser
from app.utils.business_log import log_business_event
from app.utils.log_setup import get_module_logger
from app.utils.timezone import beijing_now
from app.utils.timezone import beijing_iso
from pydantic import BaseModel, EmailStr

class VerifySmsRequest(BaseModel):
    phone: str
    code: str
from typing import Optional

class ProfileUpdate(BaseModel):
    email: Optional[EmailStr] = None
    realName: Optional[str] = None
    company: Optional[str] = None
    address: Optional[str] = None

class ChangePhoneRequest(BaseModel):
    new_phone: str
    old_phone_code: str

router = APIRouter(prefix="/auth", tags=["认证"])
logger = get_module_logger("auth")

UPLOAD_CHUNK_SIZE = 1024 * 1024
AVATAR_MAX_SIZE = 5 * 1024 * 1024


def _enterprise_status_value(user: AnyUser) -> str:
    raw = getattr(user, "enterprise_status", None)
    if raw is None:
        return "none"
    if hasattr(raw, "value"):
        return raw.value
    return str(raw).lower()


def _role_value(user: AnyUser) -> str:
    raw = getattr(user, "role", None)
    return raw.value if hasattr(raw, "value") else raw


def _profile_payload(user: AnyUser) -> dict:
    from app.services.oss_service import maybe_sign_url

    return {
        "id": user.id,
        "username": user.username,
        "email": getattr(user, "email", None),
        "phone": getattr(user, "phone", None),
        "role": _role_value(user),
        "realName": getattr(user, "real_name", None),
        "company": getattr(user, "company", None),
        "address": getattr(user, "address", None),
        "avatar": maybe_sign_url(getattr(user, "avatar", None) or "", expires=7 * 24 * 3600),
        "enterprise_status": _enterprise_status_value(user),
        "enterprise_name": getattr(user, "enterprise_name", None),
        "enterprise_reject_reason": getattr(user, "enterprise_reject_reason", None),
    }


async def _stream_upload_to_temp(file: UploadFile, max_size: int, limit_message: str) -> tuple[str, int]:
    tmp_dir = os.path.join(settings.UPLOAD_DIR, ".tmp")
    os.makedirs(tmp_dir, exist_ok=True)

    ext = os.path.splitext(file.filename or "")[1].lower()
    tmp_path = os.path.join(tmp_dir, "%s%s.part" % (uuid.uuid4().hex, ext))
    size = 0

    try:
        async with aiofiles.open(tmp_path, "wb") as out:
            while True:
                chunk = await file.read(UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_size:
                    raise HTTPException(status_code=413, detail=limit_message)
                await out.write(chunk)
        return tmp_path, size
    except Exception:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise


def _cleanup_temp_file(tmp_path: str):
    if not tmp_path:
        return
    try:
        os.remove(tmp_path)
    except OSError:
        pass


@router.post("/login", response_model=ApiResponse[LoginResponse])
async def api_login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """用户登录（支持用户名+密码 或 手机号+验证码）"""
    try:
        result = await login(db, login_data)
        return ApiResponse(code=200, message="登录成功", data=result)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试") from e


@router.post("/send-sms", response_model=ApiResponse[dict])
async def api_send_sms(
    sms_data: SendSmsRequest,
):
    """发送短信验证码"""
    try:
        result = await send_sms_verify_code(sms_data.phone)
        return ApiResponse(code=200, message="验证码已发送", data=result)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试") from e



@router.post("/verify-sms", response_model=ApiResponse[bool])
async def api_verify_sms(data: VerifySmsRequest):
    """验证短信验证码（消耗验证码）"""
    is_valid = await verify_sms_code(data.phone, data.code, consume=True)
    if not is_valid:
        raise HTTPException(status_code=400, detail="验证码错误或已过期")
    return ApiResponse(code=200, message="验证成功", data=True)

@router.post("/pre-verify-sms", response_model=ApiResponse[bool])
async def api_pre_verify_sms(data: VerifySmsRequest):
    """预校验短信验证码（不消耗，用于注册表单实时反馈）"""
    is_valid = await verify_sms_code(data.phone, data.code, consume=False)
    if not is_valid:
        raise HTTPException(status_code=400, detail="验证码错误或已过期")
    return ApiResponse(code=200, message="验证码正确", data=True)


@router.get("/validate-invite/{token}", response_model=ApiResponse[dict])
async def api_validate_user_invite(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """验证普通用户邀请链接是否有效（公开接口，无需登录）"""
    try:
        data = await validate_user_invitation(db, token)
        return ApiResponse(code=200, message="邀请链接有效", data={
            **data,
            "expiresAt": beijing_iso(data.get("expiresAt")),
        })
    except HTTPException as e:
        reason = "invalid"
        if "已被使用" in str(e.detail):
            reason = "used"
        elif "已过期" in str(e.detail):
            reason = "expired"
        return ApiResponse(code=400, message=str(e.detail), data={"valid": False, "reason": reason})

@router.post("/register", response_model=ApiResponse[dict])
async def api_register(
    register_data: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """用户注册（手机号+验证码+用户名+密码+邮箱）"""
    try:
        # 提取客户端 IP 和 User-Agent（用于安全审计）
        client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or request.client.host if request.client else ""
        user_agent = request.headers.get("User-Agent", "")
        
        result = await register(db, register_data, client_ip=client_ip, user_agent=user_agent)
        return ApiResponse(code=200, message="注册成功", data=result)
    except HTTPException as e:
        raise e
    except Exception as e:
        log_business_event(
            logger,
            "register_api_failed",
            level="error",
            phone=register_data.phone,
            username=register_data.username,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试") from e


@router.post("/reset-password", response_model=ApiResponse[dict])
async def api_reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """忘记密码 - 通过短信验证码重置密码"""
    try:
        result = await reset_password(db, data)
        return ApiResponse(code=200, message="密码重置成功", data=result)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试") from e


@router.post("/logout", response_model=ApiResponse[None])
async def api_logout():
    """用户登出"""
    # JWT 是无状态的，登出由前端处理（删除 token）
    return ApiResponse(code=200, message="登出成功", data=None)


@router.get("/me", response_model=ApiResponse[dict])
async def api_get_current_profile(
    current_user: AnyUser = Depends(get_current_user_for_public_deployment),
):
    """获取当前登录用户资料，用于刷新前端缓存和头像签名 URL。"""
    return ApiResponse(code=200, message="获取成功", data=_profile_payload(current_user))


@router.put("/change-password", response_model=ApiResponse[dict])
async def api_change_password(
    password_data: ChangePasswordRequest,
    current_user: AnyUser = Depends(get_current_user_for_public_deployment),
    db: AsyncSession = Depends(get_db)
):
    """修改密码"""
    try:
        result = await change_password(db, current_user, password_data)
        return ApiResponse(code=200, message="密码修改成功", data=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试") from e

@router.put("/profile", response_model=ApiResponse[dict])
async def update_profile_api(
    profile_data: ProfileUpdate,
    current_user: AnyUser = Depends(get_current_user_for_public_deployment),
    db: AsyncSession = Depends(get_db)
):
    """更新当前用户个人资料"""
    try:
        if profile_data.email is not None:
            current_user.email = profile_data.email
        if profile_data.realName is not None:
            current_user.real_name = profile_data.realName
        if profile_data.company is not None and hasattr(current_user, 'company'):
            current_user.company = profile_data.company
        if profile_data.address is not None and hasattr(current_user, 'address'):
            current_user.address = profile_data.address
            
        await db.commit()
        await db.refresh(current_user)
        
        return ApiResponse(code=200, message="资料更新成功", data=_profile_payload(current_user))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试") from e


@router.post("/avatar", response_model=ApiResponse[dict])
async def upload_avatar_api(
    avatar: UploadFile = File(...),
    current_user: AnyUser = Depends(get_current_user_for_public_deployment),
    db: AsyncSession = Depends(get_db)
):
    """企业认证通过后上传头像。"""
    if not isinstance(current_user, User):
        raise HTTPException(status_code=403, detail="仅普通用户可以上传头像")
    if _enterprise_status_value(current_user) != EnterpriseStatus.APPROVED.value:
        raise HTTPException(status_code=403, detail="企业认证通过后才可以更换头像")

    allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
    if avatar.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="头像仅支持 JPG/PNG/WEBP 格式")

    file_ext = os.path.splitext(os.path.basename(avatar.filename or ""))[1].lower() or ".jpg"
    file_name = "avatar_%d%s" % (int(beijing_now().timestamp()), file_ext)
    tmp_path, _size = await _stream_upload_to_temp(avatar, AVATAR_MAX_SIZE, "头像图片不能超过5MB")

    try:
        if settings.OSS_ENABLED:
            from app.services.oss_service import upload_file_and_sign
            result = upload_file_and_sign(
                file_path=tmp_path,
                prefix="avatars",
                user_id=current_user.id,
                filename=file_name,
                content_type=avatar.content_type or "",
            )
            avatar_url = result["object_key"]
        else:
            upload_dir = os.path.join(settings.UPLOAD_DIR, "avatars", current_user.id)
            os.makedirs(upload_dir, exist_ok=True)
            file_path = os.path.join(upload_dir, file_name)
            os.replace(tmp_path, file_path)
            tmp_path = ""
            avatar_url = "/uploads/avatars/%s/%s" % (current_user.id, file_name)
    finally:
        _cleanup_temp_file(tmp_path)

    current_user.avatar = avatar_url
    await db.commit()
    await db.refresh(current_user)

    return ApiResponse(code=200, message="头像更新成功", data=_profile_payload(current_user))


@router.post("/change-phone", response_model=ApiResponse[dict])
async def change_phone_api(
    data: ChangePhoneRequest,
    current_user: AnyUser = Depends(get_current_user_for_public_deployment),
    db: AsyncSession = Depends(get_db)
):
    """更换手机号：用旧手机号验证码确认身份后修改。"""
    old_phone = getattr(current_user, "phone", None)
    if not old_phone:
        raise HTTPException(status_code=400, detail="当前账号未绑定手机号")

    if not re.match(r"^1[3-9]\d{9}$", data.new_phone or ""):
        raise HTTPException(status_code=400, detail="请输入有效的11位手机号")
    if data.new_phone == old_phone:
        raise HTTPException(status_code=400, detail="新手机号不能与当前手机号相同")

    Model = type(current_user)
    result = await db.execute(select(Model).where(Model.phone == data.new_phone, Model.id != current_user.id))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="该手机号已被使用")

    is_valid = await verify_sms_code(old_phone, data.old_phone_code, consume=True)
    if not is_valid:
        raise HTTPException(status_code=400, detail="旧手机号验证码错误或已过期")

    current_user.phone = data.new_phone
    await db.commit()
    await db.refresh(current_user)

    return ApiResponse(code=200, message="手机号修改成功", data=_profile_payload(current_user))
