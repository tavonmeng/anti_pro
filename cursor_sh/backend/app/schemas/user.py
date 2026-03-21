"""用户相关 Schema"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from app.models.user import UserRole


class UserBase(BaseModel):
    """用户基础模型"""
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    role: UserRole


class UserCreate(BaseModel):
    """用户创建模型"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    email: Optional[EmailStr] = None
    realName: Optional[str] = Field(None, alias="realName")
    role: str = "staff"  # admin 或 staff
    isActive: Optional[bool] = Field(True, alias="isActive")
    
    class Config:
        populate_by_name = True


class UserUpdate(BaseModel):
    """用户更新模型"""
    email: Optional[EmailStr] = None
    realName: Optional[str] = Field(None, alias="realName")
    role: Optional[str] = None  # admin 或 staff
    isActive: Optional[bool] = Field(None, alias="isActive")
    avatar: Optional[str] = None
    
    class Config:
        populate_by_name = True


class UserResponse(BaseModel):
    """用户响应模型"""
    id: str
    username: str
    role: UserRole
    email: Optional[str] = None
    real_name: Optional[str] = None
    avatar: Optional[str] = None
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

