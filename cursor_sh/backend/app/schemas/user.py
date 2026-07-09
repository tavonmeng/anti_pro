"""用户相关 Schema"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Any, Optional
from datetime import datetime
from app.models.user import UserRole


def _normalize_optional_email(value: Any) -> Any:
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
    return value


class UserBase(BaseModel):
    """用户基础模型"""
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    role: UserRole

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: Any) -> Any:
        return _normalize_optional_email(value)


class UserCreate(BaseModel):
    """用户创建模型"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    realName: Optional[str] = Field(None, alias="realName")
    role: str = "staff"  # admin 或 staff
    isActive: Optional[bool] = Field(True, alias="isActive")

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: Any) -> Any:
        return _normalize_optional_email(value)
    
    class Config:
        populate_by_name = True


class UserUpdate(BaseModel):
    """用户更新模型"""
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    realName: Optional[str] = Field(None, alias="realName")
    role: Optional[str] = None  # admin 或 staff
    isActive: Optional[bool] = Field(None, alias="isActive")
    avatar: Optional[str] = None

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: Any) -> Any:
        return _normalize_optional_email(value)
    
    class Config:
        populate_by_name = True


class UserResponse(BaseModel):
    """用户响应模型"""
    id: str
    username: str
    role: UserRole
    email: Optional[str] = None
    phone: Optional[str] = None
    real_name: Optional[str] = None
    avatar: Optional[str] = None
    is_active: bool
    enterprise_status: Optional[str] = "none"
    enterprise_name: Optional[str] = None
    enterprise_reject_reason: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
