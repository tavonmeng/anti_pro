"""认证相关 Schema"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from app.models.user import UserRole
from app.schemas.user import UserResponse


class LoginRequest(BaseModel):
    """登录请求模型（手机号+密码 或 手机号+验证码）"""
    phone: str = Field(..., min_length=11, max_length=11)
    password: Optional[str] = Field(None, min_length=6)
    sms_code: Optional[str] = None    # 短信验证码登录
    role: UserRole = UserRole.USER
    captcha: Optional[str] = None


class RegisterRequest(BaseModel):
    """注册请求模型（手机号+验证码+用户名+密码+邮箱）"""
    phone: str = Field(..., min_length=11, max_length=11)
    sms_code: str = Field(..., min_length=4, max_length=8)
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: UserRole = UserRole.USER


class SendSmsRequest(BaseModel):
    """发送短信验证码请求"""
    phone: str = Field(..., min_length=11, max_length=11)


class ResetPasswordRequest(BaseModel):
    """忘记密码 - 重置密码请求"""
    phone: str = Field(..., min_length=11, max_length=11)
    sms_code: str = Field(..., min_length=4, max_length=8)
    new_password: str = Field(..., min_length=6)


class LoginResponse(BaseModel):
    """登录响应模型"""
    token: str
    user: UserResponse


class TokenData(BaseModel):
    """Token 数据模型"""
    user_id: str
    username: str
    role: UserRole


class ChangePasswordRequest(BaseModel):
    """修改密码请求模型"""
    oldPassword: str = Field(..., min_length=6, alias="old_password")
    newPassword: str = Field(..., min_length=6, alias="new_password")
    
    class Config:
        populate_by_name = True
