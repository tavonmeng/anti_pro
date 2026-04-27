"""依赖注入"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Union

from app.database import get_db
from app.models.user import User, UserRole
from app.models.admin import Admin
from app.models.staff_member import StaffMember
from app.models.contractor import Contractor
from app.utils.security import decode_access_token

# HTTP Bearer 认证
security = HTTPBearer()

# 所有角色的联合类型
AnyUser = Union[Admin, StaffMember, User, Contractor]


def _get_model_for_role(role_str: str):
    """根据角色字符串获取对应的数据库模型"""
    if role_str == "admin":
        return Admin
    elif role_str == "staff":
        return StaffMember
    elif role_str == "contractor":
        return Contractor
    else:
        return User


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> AnyUser:
    """获取当前登录用户（自动路由到正确的表）"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="未授权，请先登录",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if payload is None:
        raise credentials_exception
    
    user_id: str = payload.get("user_id")
    role: str = payload.get("role")
    if user_id is None or role is None:
        raise credentials_exception
    
    # 根据 JWT 中的 role 查询对应的表
    Model = _get_model_for_role(role)
    result = await db.execute(select(Model).where(Model.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None or not user.is_active:
        raise credentials_exception
    
    return user


async def get_current_active_user(
    current_user: AnyUser = Depends(get_current_user)
) -> AnyUser:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="用户已被禁用")
    return current_user


async def require_admin(
    current_user: AnyUser = Depends(get_current_user)
) -> Admin:
    """要求管理员权限"""
    role = current_user.role
    role_value = role.value if hasattr(role, 'value') else role
    if role_value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，只有管理员可以执行此操作"
        )
    return current_user


async def require_admin_or_staff(
    current_user: AnyUser = Depends(get_current_user)
) -> AnyUser:
    """要求管理员或负责人权限"""
    role = current_user.role
    role_value = role.value if hasattr(role, 'value') else role
    if role_value not in ["admin", "staff"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )
    return current_user


async def require_contractor(
    current_user: AnyUser = Depends(get_current_user)
) -> Contractor:
    """要求承包商权限"""
    role = current_user.role
    role_value = role.value if hasattr(role, 'value') else role
    if role_value != "contractor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，仅承包商可执行此操作"
        )
    return current_user


async def require_internal_user(
    current_user: AnyUser = Depends(get_current_user)
) -> AnyUser:
    """要求内部用户权限（管理员/设计师/承包商）"""
    role = current_user.role
    role_value = role.value if hasattr(role, 'value') else role
    if role_value not in ["admin", "staff", "contractor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，仅内部用户可执行此操作"
        )
    return current_user
