"""认证服务"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, LoginResponse, ChangePasswordRequest
from app.schemas.user import UserResponse
from app.utils.security import verify_password, get_password_hash, create_access_token
from app.utils.validators import generate_id


async def login(db: AsyncSession, login_data: LoginRequest) -> LoginResponse:
    """用户登录"""
    # 查询用户
    result = await db.execute(
        select(User).where(
            User.username == login_data.username,
            User.role == login_data.role
        )
    )
    user = result.scalar_one_or_none()
    
    # 验证用户和密码
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
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
    
    # 构造响应
    user_response = UserResponse.model_validate(user)
    
    return LoginResponse(token=token, user=user_response)


async def register(db: AsyncSession, register_data: RegisterRequest) -> dict:
    """用户注册"""
    try:
        # 检查用户名是否已存在
        result = await db.execute(
            select(User).where(User.username == register_data.username)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="用户名已存在"
            )
        
        # 创建新用户
        new_user = User(
            id=generate_id("user"),
            username=register_data.username,
            email=register_data.email,
            password_hash=get_password_hash(register_data.password),
            role=register_data.role,
            is_active=True
        )
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)  # 刷新以获取数据库生成的值
        
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        print(f"注册服务错误: {error_detail}")  # 打印到控制台
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"注册失败: {str(e)}"
        )


async def change_password(
    db: AsyncSession,
    user: User,
    password_data: ChangePasswordRequest
) -> dict:
    """修改密码"""
    # 验证旧密码
    if not verify_password(password_data.oldPassword, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码错误"
        )
    
    # 更新密码
    user.password_hash = get_password_hash(password_data.newPassword)
    await db.commit()
    await db.refresh(user)
    
    return {"success": True, "message": "密码修改成功"}

