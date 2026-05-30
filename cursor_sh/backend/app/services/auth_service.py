"""认证服务"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.user import User, UserRole
from app.models.admin import Admin
from app.models.staff_member import StaffMember
from app.models.contractor import Contractor
from app.models.contractor_invitation import ContractorInvitation
from app.models.security_event import SecurityEvent, SecurityEventType
from app.config import settings
from app.schemas.auth import (
    LoginRequest, RegisterRequest, LoginResponse, 
    ChangePasswordRequest, ResetPasswordRequest
)
from app.schemas.user import UserResponse
from app.utils.security import verify_password, get_password_hash, create_access_token
from app.utils.validators import generate_id
from app.services.sms_service import verify_sms_code
from app.services.oss_service import maybe_sign_url
from app.utils.business_log import log_business_event
from app.utils.log_setup import get_module_logger


logger = get_module_logger("auth")


def _role_value(role) -> str:
    return role.value if hasattr(role, "value") else str(role)


def _ensure_role_allowed_for_deployment(role: UserRole) -> None:
    """External deployment is customer-facing and must not expose internal auth."""
    role_value = _role_value(role)
    deploy_mode = (settings.DEPLOYMENT_MODE or "").strip().lower()
    if deploy_mode == "external" and role_value != UserRole.USER.value:
        log_business_event(
            logger,
            "internal_role_auth_blocked_on_external",
            level="warning",
            role=role_value,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="接口不存在",
        )


def _password_reset_models():
    deploy_mode = (settings.DEPLOYMENT_MODE or "").strip().lower()
    if deploy_mode == "external":
        return [User]
    return [User, Admin, StaffMember, Contractor]


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
    _ensure_role_allowed_for_deployment(login_data.role)
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
            log_business_event(
                logger,
                "login_failed",
                role=login_data.role,
                phone=login_data.phone,
                method="sms",
                reason="user_not_found",
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="尚未注册或角色不匹配"
            )
        is_valid = await verify_sms_code(login_data.phone, login_data.sms_code)
        if not is_valid:
            log_business_event(
                logger,
                "login_failed",
                user_id=user.id,
                username=user.username,
                role=login_data.role,
                phone=login_data.phone,
                method="sms",
                reason="invalid_sms_code",
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="验证码错误或已过期"
            )
    elif login_data.password:
        # ---- 手机号 + 密码登录 ----
        if not user or not verify_password(login_data.password, user.password_hash):
            log_business_event(
                logger,
                "login_failed",
                role=login_data.role,
                phone=login_data.phone,
                method="password",
                reason="invalid_credentials",
            )
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
        log_business_event(
            logger,
            "login_failed",
            user_id=user.id,
            username=user.username,
            role=login_data.role,
            phone=login_data.phone,
            method="sms" if login_data.sms_code else "password",
            reason="inactive",
        )
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
    log_business_event(
        logger,
        "login_success",
        user_id=user.id,
        username=user.username,
        role=role_value,
        phone=login_data.phone,
        method="sms" if login_data.sms_code else "password",
    )
    
    # 构造统一响应
    user_response = UserResponse(
        id=user.id,
        username=user.username,
        role=UserRole(role_value),
        email=getattr(user, 'email', None),
        phone=getattr(user, 'phone', None),
        real_name=getattr(user, 'real_name', None),
        avatar=maybe_sign_url(getattr(user, 'avatar', None) or "", expires=7 * 24 * 3600),
        is_active=user.is_active,
        enterprise_status=(lambda e: e.value if hasattr(e, 'value') else str(e or 'none').lower())(getattr(user, 'enterprise_status', None) or 'none'),
        enterprise_name=getattr(user, 'enterprise_name', None),
        enterprise_reject_reason=getattr(user, 'enterprise_reject_reason', None),
        created_at=user.created_at
    )
    
    return LoginResponse(token=token, user=user_response)


async def register(db: AsyncSession, register_data: RegisterRequest, client_ip: str = "", user_agent: str = "") -> dict:
    """用户注册（手机号+验证码+用户名+密码+邮箱）
    
    注册只允许 user 角色。admin 和 staff 由管理员后台创建。
    包含反注册机行为分析 + 安全事件审计。
    """
    # 构建行为数据快照（用于写入安全事件表）
    behavior = register_data.behavior
    behavior_snapshot = behavior.model_dump() if behavior else None
    if behavior_snapshot and behavior:
        behavior_snapshot["total_duration_sec"] = round(
            (behavior.submit_clicked_at - behavior.page_loaded_at) / 1000, 1
        )
    
    async def _log_event(event_type: SecurityEventType, user_id: str = None, block_reason: str = None, fail_reason: str = None):
        """写入安全事件（独立 try 确保不影响主流程）"""
        try:
            event = SecurityEvent(
                id=generate_id("sec"),
                event_type=event_type,
                user_id=user_id,
                phone=register_data.phone,
                username=register_data.username,
                client_ip=client_ip[:50] if client_ip else None,
                user_agent=user_agent[:500] if user_agent else None,
                behavior_data=behavior_snapshot,
                block_reason=block_reason,
                fail_reason=fail_reason,
            )
            db.add(event)
            await db.flush()  # 写入但不单独 commit，跟随主事务
        except Exception as e:
            log_business_event(
                logger,
                "security_event_write_failed",
                level="warning",
                event_type=event_type,
                user_id=user_id,
                phone=register_data.phone,
                error=str(e),
            )
    
    try:
        # ========== 反注册机检测 ==========
        
        # 0a. 蜜罐字段检查（前端隐藏，正常用户不会填写）
        if register_data.website:
            log_business_event(
                logger,
                "register_bot_blocked",
                phone=register_data.phone,
                username=register_data.username,
                client_ip=client_ip,
                reason="honeypot_filled",
            )
            await _log_event(SecurityEventType.REGISTER_BOT_BLOCKED, block_reason="honeypot_filled")
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="注册失败，请稍后重试"
            )
        
        # 0b. 行为时序分析
        if behavior:
            total_time_sec = (behavior.submit_clicked_at - behavior.page_loaded_at) / 1000
            
            # 规则1: 总操作时长 < 8 秒 → 极有可能是机器人
            if total_time_sec < 8:
                await _log_event(SecurityEventType.REGISTER_BOT_BLOCKED, block_reason=f"too_fast:{total_time_sec:.1f}s")
                await db.commit()
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="操作过快，请重新注册")
            
            # 规则2: 按键次数 < 15 → 不可能手动填完所有字段
            if behavior.key_press_count < 15:
                await _log_event(SecurityEventType.REGISTER_BOT_BLOCKED, block_reason=f"low_keypress:{behavior.key_press_count}")
                await db.commit()
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="操作异常，请重新注册")
            
            # 规则3: 字段聚焦次数 < 3 → 没有正常的 tab/click 操作
            if behavior.field_focus_count < 3:
                await _log_event(SecurityEventType.REGISTER_BOT_BLOCKED, block_reason=f"low_focus:{behavior.field_focus_count}")
                await db.commit()
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="操作异常，请重新注册")
            
            log_business_event(
                logger,
                "register_behavior_checked",
                phone=register_data.phone,
                username=register_data.username,
                client_ip=client_ip,
                total_duration_sec=round(total_time_sec, 1),
                key_press_count=behavior.key_press_count,
                field_focus_count=behavior.field_focus_count,
            )
        else:
            log_business_event(
                logger,
                "register_behavior_missing",
                level="warning",
                phone=register_data.phone,
                username=register_data.username,
                client_ip=client_ip,
            )
        
        # ========== 正常注册流程 ==========
        
        # 1. 校验短信验证码
        is_valid = await verify_sms_code(register_data.phone, register_data.sms_code, consume=True)
        if not is_valid:
            await _log_event(SecurityEventType.REGISTER_FAIL, fail_reason="invalid_sms_code")
            await db.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码错误或已过期")
        
        # 2. 检查手机号是否已注册
        result = await db.execute(select(User).where(User.phone == register_data.phone))
        if result.scalar_one_or_none():
            await _log_event(SecurityEventType.REGISTER_FAIL, fail_reason="phone_exists")
            await db.commit()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该手机号已注册")
        
        # 3. 检查用户名是否已存在（需查四张表）
        for Model in [User, Admin, StaffMember, Contractor]:
            result = await db.execute(select(Model).where(Model.username == register_data.username))
            if result.scalar_one_or_none():
                await _log_event(SecurityEventType.REGISTER_FAIL, fail_reason="username_exists")
                await db.commit()
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在")
        
        # 4. 检查邮箱是否已使用
        result = await db.execute(select(User).where(User.email == register_data.email))
        if result.scalar_one_or_none():
            await _log_event(SecurityEventType.REGISTER_FAIL, fail_reason="email_exists")
            await db.commit()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该邮箱已被使用")
        
        # 5. 创建新用户
        new_user = User(
            id=generate_id("user"),
            username=register_data.username,
            email=register_data.email,
            phone=register_data.phone,
            password_hash=get_password_hash(register_data.password),
            role=UserRole.USER,
            is_active=True,
            register_ip=client_ip[:50] if client_ip else None,
            register_user_agent=user_agent[:500] if user_agent else None,
        )
        
        db.add(new_user)
        
        # 6. 记录注册成功事件
        await _log_event(SecurityEventType.REGISTER_SUCCESS, user_id=new_user.id)
        
        await db.commit()
        await db.refresh(new_user)
        log_business_event(
            logger,
            "register_success",
            user_id=new_user.id,
            username=new_user.username,
            phone=new_user.phone,
            email=new_user.email,
            client_ip=client_ip,
        )
        
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        log_business_event(
            logger,
            "register_failed",
            level="error",
            phone=register_data.phone,
            username=register_data.username,
            client_ip=client_ip,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注册失败，请稍后重试"
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
    
    # 2. 在用户表中查找。External 部署只允许普通客户找回密码；
    #    内部角色只能在 internal/all 部署入口操作。
    user = None
    for Model in _password_reset_models():
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
    
    log_business_event(
        logger,
        "password_reset",
        user_id=user.id,
        username=user.username,
        role=getattr(user, "role", ""),
        phone=data.phone,
    )
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
    from app.utils.timezone import beijing_now, ensure_beijing
    
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
        
        now = beijing_now()
        expires_at = ensure_beijing(invitation.expires_at)
        if expires_at and expires_at < now:
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
        
        # 4. 用户名：未提供则自动生成
        username = register_data.get('username')
        if not username:
            username = f"contractor_{phone[-4:]}"
            # 确保自动生成的用户名唯一
            suffix = 1
            base_username = username
            while True:
                dup = await db.execute(select(Contractor).where(Contractor.username == username))
                if not dup.scalar_one_or_none():
                    break
                username = f"{base_username}_{suffix}"
                suffix += 1
        
        # 检查用户名唯一性（查四张表）
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
        log_business_event(
            logger,
            "contractor_register_success",
            contractor_id=new_contractor.id,
            username=new_contractor.username,
            phone=new_contractor.phone,
            email=new_contractor.email,
            invitation_id=invitation.id,
        )
        
        return {"success": True, "contractor_id": new_contractor.id}
    
    except HTTPException:
        raise
    except Exception as e:
        log_business_event(
            logger,
            "contractor_register_failed",
            level="error",
            phone=register_data.get("phone"),
            invite_token=register_data.get("invite_token"),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注册失败，请稍后重试"
        )
