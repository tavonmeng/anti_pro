"""认证 API 路由"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, LoginResponse, ChangePasswordRequest
from app.schemas.response import ApiResponse
from app.services.auth_service import login, register, change_password
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=ApiResponse[LoginResponse])
async def api_login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """用户登录"""
    try:
        result = await login(db, login_data)
        return ApiResponse(code=200, message="登录成功", data=result)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/register", response_model=ApiResponse[dict])
async def api_register(
    register_data: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """用户注册"""
    try:
        result = await register(db, register_data)
        return ApiResponse(code=200, message="注册成功", data=result)
    except HTTPException as e:
        raise e
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        print(f"注册接口错误: {error_detail}")  # 打印到控制台
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
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

