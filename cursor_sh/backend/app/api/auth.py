"""认证 API 路由"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest, RegisterRequest, LoginResponse, 
    ChangePasswordRequest, SendSmsRequest, ResetPasswordRequest
)
from app.schemas.response import ApiResponse
from app.services.auth_service import login, register, change_password, reset_password
from app.services.sms_service import send_sms_verify_code
from app.utils.dependencies import get_current_user
from pydantic import BaseModel, EmailStr
from typing import Optional

class ProfileUpdate(BaseModel):
    email: Optional[EmailStr] = None
    realName: Optional[str] = None
    company: Optional[str] = None
    address: Optional[str] = None

router = APIRouter(prefix="/auth", tags=["认证"])


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
        raise HTTPException(status_code=500, detail=str(e))


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
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/register", response_model=ApiResponse[dict])
async def api_register(
    register_data: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """用户注册（手机号+验证码+用户名+密码+邮箱）"""
    try:
        result = await register(db, register_data)
        return ApiResponse(code=200, message="注册成功", data=result)
    except HTTPException as e:
        raise e
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        print(f"注册接口错误: {error_detail}")
        raise HTTPException(status_code=500, detail=str(e))


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
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/logout", response_model=ApiResponse[None])
async def api_logout():
    """用户登出"""
    # JWT 是无状态的，登出由前端处理（删除 token）
    return ApiResponse(code=200, message="登出成功", data=None)


@router.put("/change-password", response_model=ApiResponse[dict])
async def api_change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """修改密码"""
    try:
        result = await change_password(db, current_user, password_data)
        return ApiResponse(code=200, message="密码修改成功", data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/profile", response_model=ApiResponse[dict])
async def update_profile_api(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新当前用户个人资料"""
    try:
        if profile_data.email is not None:
            current_user.email = profile_data.email
        if profile_data.realName is not None:
            current_user.real_name = profile_data.realName
        if profile_data.company is not None:
            current_user.company = profile_data.company
        if profile_data.address is not None:
            current_user.address = profile_data.address
            
        await db.commit()
        await db.refresh(current_user)
        
        return ApiResponse(code=200, message="资料更新成功", data={
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "role": current_user.role.value,
            "realName": current_user.real_name,
            "company": current_user.company,
            "address": current_user.address
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
