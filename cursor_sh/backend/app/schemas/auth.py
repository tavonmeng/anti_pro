"""认证相关 Schema"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from app.models.user import UserRole
from app.schemas.user import UserResponse


class LoginRequest(BaseModel):
    """登录请求模型"""
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=6)
    role: UserRole
    captcha: Optional[str] = None


class RegisterRequest(BaseModel):
    """注册请求模型"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: UserRole = UserRole.USER


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

