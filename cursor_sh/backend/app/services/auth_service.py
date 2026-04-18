"""认证服务"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.user import User
from app.schemas.auth import (
    LoginRequest, RegisterRequest, LoginResponse, 
    ChangePasswordRequest, ResetPasswordRequest
)
from app.schemas.user import UserResponse
from app.utils.security import verify_password, get_password_hash, create_access_token
from app.utils.validators import generate_id
from app.services.sms_service import verify_sms_code


async def login(db: AsyncSession, login_data: LoginRequest) -> LoginResponse:
    """
    用户登录
    支持两种方式:
    1. 手机号 + 密码
    2. 手机号 + 短信验证码
    """
    # 通过手机号查找用户
    result = await db.execute(
        select(User).where(
            User.phone == login_data.phone,
            User.role == login_data.role
        )
    )
    user = result.scalar_one_or_none()
    
    if login_data.sms_code:
        # ---- 手机号 + 验证码登录 ----
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="该手机号尚未注册"
            )
        is_valid = await verify_sms_code(login_data.phone, login_data.sms_code)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="验证码错误或已过期"
            )
    elif login_data.password:
        # ---- 手机号 + 密码登录 ----
        if not user or not verify_password(login_data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="手机号或密码错误"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请提供密码或验证码"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    
    # 生成 JWT token
    token_data = {
        "user_id": user.id,
        "username": user.username,
        "role": user.role.value
    }
    token = create_access_token(token_data)
    user_response = UserResponse.model_validate(user)
    
    return LoginResponse(token=token, user=user_response)


async def register(db: AsyncSession, register_data: RegisterRequest) -> dict:
    """用户注册（手机号+验证码+用户名+密码+邮箱）"""
    try:
        # 1. 校验短信验证码
        is_valid = await verify_sms_code(register_data.phone, register_data.sms_code)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="验证码错误或已过期"
            )
        
        # 2. 检查手机号是否已注册
        result = await db.execute(
            select(User).where(User.phone == register_data.phone)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="该手机号已注册"
            )
        
        # 3. 检查用户名是否已存在
        result = await db.execute(
            select(User).where(User.username == register_data.username)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="用户名已存在"
            )
        
        # 4. 检查邮箱是否已使用
        result = await db.execute(
            select(User).where(User.email == register_data.email)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="该邮箱已被使用"
            )
        
        # 5. 创建新用户
        new_user = User(
            id=generate_id("user"),
            username=register_data.username,
            email=register_data.email,
            phone=register_data.phone,
            password_hash=get_password_hash(register_data.password),
            role=register_data.role,
            is_active=True
        )
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        print(f"注册服务错误: {error_detail}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"注册失败: {str(e)}"
        )


async def reset_password(db: AsyncSession, data: ResetPasswordRequest) -> dict:
    """忘记密码 - 通过短信验证码重置密码"""
    # 1. 校验短信验证码
    is_valid = await verify_sms_code(data.phone, data.sms_code)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误或已过期"
        )
    
    # 2. 查找用户
    result = await db.execute(
        select(User).where(User.phone == data.phone)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="该手机号尚未注册"
        )
    
    # 3. 更新密码
    user.password_hash = get_password_hash(data.new_password)
    await db.commit()
    await db.refresh(user)
    
    print(f"✅ 用户 {user.username} (手机号 {data.phone[:3]}****{data.phone[7:]}) 密码重置成功")
    return {"success": True, "message": "密码重置成功"}


async def change_password(
    db: AsyncSession,
    user: User,
    password_data: ChangePasswordRequest
) -> dict:
    """修改密码"""
    if not verify_password(password_data.oldPassword, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码错误"
        )
    
    user.password_hash = get_password_hash(password_data.newPassword)
    await db.commit()
    await db.refresh(user)
    
    return {"success": True, "message": "密码修改成功"}
