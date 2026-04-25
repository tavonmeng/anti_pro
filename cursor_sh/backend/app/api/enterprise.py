"""企业认证 API 路由"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import Optional, List

from app.database import get_db
from app.models.user import User, EnterpriseStatus
from app.schemas.response import ApiResponse
from app.utils.dependencies import get_current_user, require_admin, AnyUser
from app.services.notification_service import NotificationService
from app.models.notification import NotificationType

router = APIRouter(prefix="/enterprise", tags=["企业认证"])


def _get_status(user) -> str:
    """安全获取用户企业认证状态（始终返回小写字符串）"""
    raw = getattr(user, 'enterprise_status', None)
    if raw is None:
        return 'none'
    if hasattr(raw, 'value'):
        return raw.value  # EnterpriseStatus.NONE -> 'none'
    return str(raw).lower()  # 'NONE' -> 'none'


@router.get("/status", response_model=ApiResponse[dict])
async def get_enterprise_status(
    current_user: AnyUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取当前用户的企业认证状态"""
    if not isinstance(current_user, User):
        return ApiResponse(code=200, message="获取成功", data={
            "enterprise_status": "none",
            "enterprise_name": None,
            "business_license_url": None,
            "enterprise_reject_reason": None
        })
    
    status_val = _get_status(current_user)
    
    return ApiResponse(code=200, message="获取成功", data={
        "enterprise_status": status_val,
        "enterprise_name": current_user.enterprise_name,
        "business_license_url": current_user.business_license_url,
        "enterprise_reject_reason": current_user.enterprise_reject_reason,
        "enterprise_submitted_at": current_user.enterprise_submitted_at.isoformat() if current_user.enterprise_submitted_at else None,
        "enterprise_reviewed_at": current_user.enterprise_reviewed_at.isoformat() if current_user.enterprise_reviewed_at else None
    })


@router.post("/submit", response_model=ApiResponse[dict])
async def submit_enterprise_auth(
    enterprise_name: str = Form(...),
    business_license: Optional[UploadFile] = File(None),
    current_user: AnyUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """提交企业认证申请（企业名称 + 营业执照图片）"""
    if not isinstance(current_user, User):
        raise HTTPException(status_code=403, detail="仅普通用户可以提交企业认证")
    
    # 检查当前状态：已通过的不能重复提交
    status_val = _get_status(current_user)
    if status_val == 'approved':
        raise HTTPException(status_code=400, detail="您已通过企业认证，无需重复提交")
    if status_val == 'pending':
        raise HTTPException(status_code=400, detail="您已有待审核的认证申请，请耐心等待")
    
    # 首次提交必须有营业执照；重新提交时如果不上传新的，沿用已有的
    if business_license and business_license.filename:
        # 验证文件类型
        allowed_types = ['image/jpeg', 'image/png', 'image/jpg', 'image/webp']
        if business_license.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="营业执照仅支持 JPG/PNG/WEBP 格式")
        
        # 保存文件
        import os
        from app.config import settings
        upload_dir = os.path.join(settings.UPLOAD_DIR, "enterprise", current_user.id)
        os.makedirs(upload_dir, exist_ok=True)
        
        file_ext = os.path.splitext(business_license.filename)[1] or '.jpg'
        file_name = f"license_{int(datetime.utcnow().timestamp())}{file_ext}"
        file_path = os.path.join(upload_dir, file_name)
        
        import aiofiles
        content = await business_license.read()
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        file_url = f"/uploads/enterprise/{current_user.id}/{file_name}"
        current_user.business_license_url = file_url
    elif not current_user.business_license_url:
        # 首次提交且没上传文件
        raise HTTPException(status_code=400, detail="请上传营业执照")
    
    # 更新用户认证信息
    current_user.enterprise_name = enterprise_name
    current_user.enterprise_status = EnterpriseStatus.PENDING
    current_user.enterprise_reject_reason = None  # 清除之前的拒绝原因
    current_user.enterprise_submitted_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(current_user)
    
    return ApiResponse(code=200, message="企业认证申请已提交，请等待审核", data={
        "enterprise_status": "pending",
        "enterprise_name": enterprise_name
    })


@router.get("/pending", response_model=ApiResponse[List[dict]])
async def get_pending_enterprise_auths(
    current_user: AnyUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """管理员获取所有待审核、已审核的企业认证列表"""
    result = await db.execute(
        select(User).where(User.enterprise_status != EnterpriseStatus.NONE).order_by(User.enterprise_submitted_at.desc())
    )
    users = result.scalars().all()
    
    items = []
    for u in users:
        status_val = _get_status(u)
        items.append({
            "user_id": u.id,
            "username": u.username,
            "phone": u.phone,
            "email": u.email,
            "enterprise_name": u.enterprise_name,
            "business_license_url": u.business_license_url,
            "enterprise_status": status_val,
            "enterprise_reject_reason": u.enterprise_reject_reason,
            "submitted_at": u.enterprise_submitted_at.isoformat() if u.enterprise_submitted_at else None,
            "reviewed_at": u.enterprise_reviewed_at.isoformat() if u.enterprise_reviewed_at else None
        })
    
    return ApiResponse(code=200, message="获取成功", data=items)


@router.post("/review/{user_id}", response_model=ApiResponse[dict])
async def review_enterprise_auth(
    user_id: str,
    action: str = Form(...),
    reject_reason: Optional[str] = Form(None),
    current_user: AnyUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """管理员审核企业认证：通过或拒绝"""
    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()
    
    if not target_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    status_val = _get_status(target_user)
    if status_val != 'pending':
        raise HTTPException(status_code=400, detail="该用户当前没有待审核的企业认证")
    
    if action == "approve":
        target_user.enterprise_status = EnterpriseStatus.APPROVED
        target_user.enterprise_reject_reason = None
        target_user.enterprise_reviewed_at = datetime.utcnow()
        # 认证通过后，用户名更新为企业名称
        target_user.username = target_user.enterprise_name
        target_user.company = target_user.enterprise_name
        
        await db.commit()
        await db.refresh(target_user)
        
        # 发送通知
        try:
            await NotificationService.create_notification(
                db, user_id=user_id, 
                notification_type=NotificationType.ORDER_STATUS_CHANGED,
                title="企业认证已通过",
                content=f"恭喜！您的企业「{target_user.enterprise_name}」已通过认证，现在可以使用全部功能。"
            )
        except Exception as e:
            print(f"[Enterprise] 发送通知失败: {e}")
        
        return ApiResponse(code=200, message="企业认证已通过", data={
            "enterprise_status": "approved",
            "username": target_user.username
        })
    
    elif action == "reject":
        if not reject_reason:
            raise HTTPException(status_code=400, detail="拒绝时必须填写拒绝原因")
        
        target_user.enterprise_status = EnterpriseStatus.REJECTED
        target_user.enterprise_reject_reason = reject_reason
        target_user.enterprise_reviewed_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(target_user)
        
        # 发送通知
        try:
            await NotificationService.create_notification(
                db, user_id=user_id,
                notification_type=NotificationType.ORDER_STATUS_CHANGED,
                title="企业认证未通过",
                content=f"您的企业认证申请未通过，原因：{reject_reason}。请修正后重新提交。"
            )
        except Exception as e:
            print(f"[Enterprise] 发送通知失败: {e}")
        
        return ApiResponse(code=200, message="已拒绝企业认证", data={
            "enterprise_status": "rejected",
            "reject_reason": reject_reason
        })
    
    else:
        raise HTTPException(status_code=400, detail="action 必须为 approve 或 reject")


@router.post("/update-username", response_model=ApiResponse[dict])
async def update_enterprise_username(
    username: str = Form(...),
    current_user: AnyUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """企业用户修改用户名（简称）"""
    if not isinstance(current_user, User):
        raise HTTPException(status_code=403, detail="仅普通用户可以修改")
    
    status_val = _get_status(current_user)
    if status_val != 'approved':
        raise HTTPException(status_code=403, detail="仅已认证的企业用户可以修改用户名")
    
    if len(username) < 2 or len(username) > 50:
        raise HTTPException(status_code=400, detail="用户名长度需在2-50个字符之间")
    
    # 检查用户名是否重复
    from app.models.admin import Admin
    from app.models.staff_member import StaffMember
    for Model in [User, Admin, StaffMember]:
        result = await db.execute(select(Model).where(Model.username == username, Model.id != current_user.id))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="该用户名已被使用")
    
    current_user.username = username
    await db.commit()
    await db.refresh(current_user)
    
    return ApiResponse(code=200, message="用户名修改成功", data={"username": username})
