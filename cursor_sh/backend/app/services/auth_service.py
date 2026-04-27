"""认证服务"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.user import User, UserRole
from app.models.admin import Admin
from app.models.staff_member import StaffMember
from app.models.contractor import Contractor
from app.models.contractor_invitation import ContractorInvitation
from app.schemas.auth import (
    LoginRequest, RegisterRequest, LoginResponse, 
    ChangePasswordRequest, ResetPasswordRequest
)
from app.schemas.user import UserResponse
from app.utils.security import verify_password, get_password_hash, create_access_token
from app.utils.validators import generate_id
from app.services.sms_service import verify_sms_code


def _get_model_for_role(role: UserRole):
    """根据角色获取对应的数据库模型"""
    if role == UserRole.ADMIN:
        return Admin
    elif role == UserRole.STAFF:
        return StaffMember
    elif role == UserRole.CONTRACTOR:
        return Contractor
    else:
        return User


async def login(db: AsyncSession, login_data: LoginRequest) -> LoginResponse:
    """
    用户登录（支持三种角色，各查各的表）
    
    支持方式:
    1. 手机号 + 密码
    2. 手机号 + 短信验证码
    """
    Model = _get_model_for_role(login_data.role)
    
    if not login_data.phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请提供手机号"
        )
    
    # 通过手机号在对应表中查找
    result = await db.execute(
        select(Model).where(Model.phone == login_data.phone)
    )
    user = result.scalar_one_or_none()
    
    if login_data.sms_code:
        # ---- 手机号 + 验证码登录 ----
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="尚未注册或角色不匹配"
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
    
    # 获取角色值（Admin/StaffMember 用 property，User 用 column）
    role_value = user.role.value if hasattr(user.role, 'value') else user.role
    
    # 生成 JWT token
    token_data = {
        "user_id": user.id,
        "username": user.username,
        "role": role_value
    }
    token = create_access_token(token_data)
    
    # 构造统一响应
    user_response = UserResponse(
        id=user.id,
        username=user.username,
        role=UserRole(role_value),
        email=getattr(user, 'email', None),
        phone=getattr(user, 'phone', None),
        real_name=getattr(user, 'real_name', None),
        avatar=getattr(user, 'avatar', None),
        is_active=user.is_active,
        enterprise_status=(lambda e: e.value if hasattr(e, 'value') else str(e or 'none').lower())(getattr(user, 'enterprise_status', None) or 'none'),
        enterprise_name=getattr(user, 'enterprise_name', None),
        enterprise_reject_reason=getattr(user, 'enterprise_reject_reason', None),
        created_at=user.created_at
    )
    
    return LoginResponse(token=token, user=user_response)


async def register(db: AsyncSession, register_data: RegisterRequest) -> dict:
    """用户注册（手机号+验证码+用户名+密码+邮箱）
    
    注册只允许 user 角色。admin 和 staff 由管理员后台创建。
    """
    try:
        # 1. 校验短信验证码（立即消耗，每次提交都需要新的验证码）
        is_valid = await verify_sms_code(register_data.phone, register_data.sms_code, consume=True)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="验证码错误或已过期"
            )
        
        # 2. 检查手机号是否已注册（只查 users 表）
        result = await db.execute(
            select(User).where(User.phone == register_data.phone)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="该手机号已注册"
            )
        
        # 3. 检查用户名是否已存在（需查四张表）
        for Model in [User, Admin, StaffMember, Contractor]:
            result = await db.execute(
                select(Model).where(Model.username == register_data.username)
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
        
        # 5. 创建新用户（只在 users 表）
        new_user = User(
            id=generate_id("user"),
            username=register_data.username,
            email=register_data.email,
            phone=register_data.phone,
            password_hash=get_password_hash(register_data.password),
            role=UserRole.USER,
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
    """忘记密码 - 通过短信验证码重置密码（所有角色通用）"""
    # 1. 校验短信验证码
    is_valid = await verify_sms_code(data.phone, data.sms_code)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误或已过期"
        )
    
    # 2. 在四张表中查找用户
    user = None
    for Model in [User, Admin, StaffMember, Contractor]:
        result = await db.execute(
            select(Model).where(Model.phone == data.phone)
        )
        user = result.scalar_one_or_none()
        if user:
            break
    
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
    user,  # 可以是 User, Admin, 或 StaffMember
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


async def register_contractor(db: AsyncSession, register_data: dict) -> dict:
    """承包商通过邀请链接注册
    
    Args:
        register_data: 包含以下字段:
            - invite_token: 邀请 token
            - phone: 手机号
            - sms_code: 短信验证码
            - username: 用户名
            - password: 密码
            - email: 邮箱
            - company: 公司名称（选填）
            - address: 地址（选填）
            - specialty: 专业方向（选填）
            - expertise: 擅长领域（选填）
    """
    from datetime import datetime, timezone
    
    try:
        # 1. 验证邀请 token
        invite_token = register_data.get('invite_token')
        if not invite_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="缺少邀请 token"
            )
        
        result = await db.execute(
            select(ContractorInvitation).where(
                ContractorInvitation.token == invite_token
            )
        )
        invitation = result.scalar_one_or_none()
        
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邀请链接无效"
            )
        
        if invitation.is_used:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邀请链接已被使用"
            )
        
        now = datetime.now(timezone.utc)
        if invitation.expires_at and invitation.expires_at.replace(tzinfo=timezone.utc) < now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邀请链接已过期"
            )
        
        # 2. 验证短信验证码
        phone = register_data.get('phone')
        sms_code = register_data.get('sms_code')
        if not phone or not sms_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请提供手机号和验证码"
            )
        
        is_valid = await verify_sms_code(phone, sms_code, consume=True)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="验证码错误或已过期"
            )
        
        # 3. 检查手机号是否已注册
        result = await db.execute(
            select(Contractor).where(Contractor.phone == phone)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="该手机号已注册"
            )
        
        # 4. 检查用户名唯一性（查四张表）
        username = register_data.get('username')
        for Model in [User, Admin, StaffMember, Contractor]:
            result = await db.execute(
                select(Model).where(Model.username == username)
            )
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="用户名已存在"
                )
        
        # 5. 创建承包商账户
        new_contractor = Contractor(
            id=generate_id("contractor"),
            username=username,
            email=register_data.get('email', ''),
            phone=phone,
            password_hash=get_password_hash(register_data.get('password', '')),
            real_name=register_data.get('real_name'),
            company=register_data.get('company'),
            address=register_data.get('address'),
            specialty=register_data.get('specialty'),
            expertise=register_data.get('expertise'),
            is_active=True
        )
        
        db.add(new_contractor)
        
        # 6. 标记邀请链接已使用
        invitation.is_used = True
        invitation.used_by = new_contractor.id
        
        await db.commit()
        await db.refresh(new_contractor)
        
        return {"success": True, "contractor_id": new_contractor.id}
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        print(f"承包商注册错误: {error_detail}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"注册失败: {str(e)}"
        )
