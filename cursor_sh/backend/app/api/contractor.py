"""承包商端 API 路由"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime, timezone

from app.database import get_db
from app.models.contractor import Contractor
from app.models.contractor_invitation import ContractorInvitation
from app.models.contractor_assignment import ContractorAssignment, AssignmentStatus
from app.models.contractor_deliverable import ContractorDeliverable, DeliverableStatus
from app.models.order import Order
from app.schemas.response import ApiResponse
from app.utils.dependencies import require_contractor, AnyUser
from app.utils.validators import generate_id
from app.services.auth_service import register_contractor

router = APIRouter(prefix="/contractor", tags=["承包商"])


# ========== Schemas ==========

class ContractorRegisterRequest(BaseModel):
    invite_token: str
    phone: str
    sms_code: str
    username: str
    password: str
    email: EmailStr
    real_name: Optional[str] = None
    company: Optional[str] = None
    address: Optional[str] = None
    specialty: Optional[str] = None
    expertise: Optional[str] = None

class RejectAssignmentRequest(BaseModel):
    reject_reason: Optional[str] = None

class DeliverableCreate(BaseModel):
    assignment_id: str
    stage_config_id: str
    stage_name: str
    stage_order: int
    description: Optional[str] = None
    files: Optional[list[dict]] = None
    self_review_checks: Optional[dict] = None

class DeliverableUpdate(BaseModel):
    description: Optional[str] = None
    files: Optional[list[dict]] = None
    self_review_checks: Optional[dict] = None

class ProfileUpdate(BaseModel):
    email: Optional[EmailStr] = None
    real_name: Optional[str] = None
    company: Optional[str] = None
    address: Optional[str] = None
    specialty: Optional[str] = None
    expertise: Optional[str] = None


# ========== 注册与邀请验证（公开接口） ==========

@router.get("/validate-invite/{token}")
async def validate_invite_token(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """验证邀请链接是否有效（公开接口，无需登录）"""
    try:
        result = await db.execute(
            select(ContractorInvitation).where(ContractorInvitation.token == token)
        )
        invitation = result.scalar_one_or_none()
        
        if not invitation:
            return ApiResponse(code=400, message="邀请链接无效", data={"valid": False, "reason": "invalid"})
        
        if invitation.is_used:
            return ApiResponse(code=400, message="邀请链接已被使用", data={"valid": False, "reason": "used"})
        
        now = datetime.now(timezone.utc)
        if invitation.expires_at and invitation.expires_at.replace(tzinfo=timezone.utc) < now:
            return ApiResponse(code=400, message="邀请链接已过期", data={"valid": False, "reason": "expired"})
        
        return ApiResponse(code=200, message="邀请链接有效", data={
            "valid": True,
            "note": invitation.note,
            "expiresAt": invitation.expires_at.isoformat() if invitation.expires_at else None,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/register")
async def register_contractor_api(
    data: ContractorRegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """承包商通过邀请链接注册（公开接口，需要邀请 token + 短信验证码）"""
    try:
        result = await register_contractor(db, data.model_dump())
        return ApiResponse(code=201, message="注册成功", data=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 我的派单 ==========

@router.get("/assignments")
async def get_my_assignments(
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: AnyUser = Depends(require_contractor),
    db: AsyncSession = Depends(get_db)
):
    """获取我的派单列表"""
    try:
        query = select(ContractorAssignment).where(
            ContractorAssignment.contractor_id == current_user.id
        )
        
        if status_filter:
            query = query.where(ContractorAssignment.status == status_filter)
        
        query = query.order_by(ContractorAssignment.assigned_at.desc())
        result = await db.execute(query)
        assignments = result.scalars().all()
        
        items = []
        for a in assignments:
            # 获取订单基本信息（脱敏）
            o_result = await db.execute(
                select(Order).where(Order.id == a.order_id)
            )
            order = o_result.scalar_one_or_none()
            
            order_info = None
            if order:
                order_data = order.order_data or {}
                order_info = {
                    "id": order.id,
                    "orderNumber": order.order_number,
                    "orderType": order.order_type.value if hasattr(order.order_type, 'value') else order.order_type,
                    "status": order.status.value if hasattr(order.status, 'value') else order.status,
                    # 脱敏：只展示需求相关字段，不展示用户个人信息
                    "brand": order_data.get("brand"),
                    "content": order_data.get("content"),
                    "style": order_data.get("style"),
                    "city": order_data.get("city"),
                    "media_size": order_data.get("media_size"),
                    "technology": order_data.get("technology"),
                    "budget": order_data.get("budget"),
                    "online_time": order_data.get("online_time"),
                    "target_group": order_data.get("target_group"),
                    "background": order_data.get("background"),
                    "createdAt": order.created_at.isoformat() if order.created_at else None,
                }
            
            items.append({
                "id": a.id,
                "orderId": a.order_id,
                "order": order_info,
                "status": a.status.value,
                "rejectReason": a.reject_reason,
                "schedule": a.schedule,
                "currentStageOrder": a.current_stage_order,
                "assignedAt": a.assigned_at.isoformat() if a.assigned_at else None,
                "respondedAt": a.responded_at.isoformat() if a.responded_at else None,
            })
        
        return ApiResponse(code=200, message="获取成功", data=items)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/assignments/{assignment_id}")
async def get_assignment_detail(
    assignment_id: str,
    current_user: AnyUser = Depends(require_contractor),
    db: AsyncSession = Depends(get_db)
):
    """获取派单详情（含订单信息和交付物列表）"""
    try:
        result = await db.execute(
            select(ContractorAssignment).where(
                ContractorAssignment.id == assignment_id,
                ContractorAssignment.contractor_id == current_user.id
            )
        )
        assignment = result.scalar_one_or_none()
        
        if not assignment:
            raise HTTPException(status_code=404, detail="派单不存在")
        
        # 获取订单信息（脱敏）
        o_result = await db.execute(
            select(Order).where(Order.id == assignment.order_id)
        )
        order = o_result.scalar_one_or_none()
        
        order_info = None
        if order:
            order_data = order.order_data or {}
            order_info = {
                "id": order.id,
                "orderNumber": order.order_number,
                "orderType": order.order_type.value if hasattr(order.order_type, 'value') else order.order_type,
                "status": order.status.value if hasattr(order.status, 'value') else order.status,
                "brand": order_data.get("brand"),
                "content": order_data.get("content"),
                "style": order_data.get("style"),
                "city": order_data.get("city"),
                "media_size": order_data.get("media_size"),
                "technology": order_data.get("technology"),
                "budget": order_data.get("budget"),
                "online_time": order_data.get("online_time"),
                "target_group": order_data.get("target_group"),
                "background": order_data.get("background"),
                "site_photos": order_data.get("site_photos"),
                "createdAt": order.created_at.isoformat() if order.created_at else None,
            }
        
        # 获取所有交付物
        d_result = await db.execute(
            select(ContractorDeliverable)
            .where(ContractorDeliverable.assignment_id == assignment_id)
            .order_by(ContractorDeliverable.stage_order, ContractorDeliverable.version)
        )
        deliverables = d_result.scalars().all()
        
        deliverables_data = [
            {
                "id": d.id,
                "stageConfigId": d.stage_config_id,
                "stageName": d.stage_name,
                "stageOrder": d.stage_order,
                "version": d.version,
                "parentId": d.parent_id,
                "files": d.files or [],
                "description": d.description,
                "selfReviewChecks": d.self_review_checks or {},
                "status": d.status.value,
                "adminReviewNote": d.admin_review_note,
                "adminReviewedAt": d.admin_reviewed_at.isoformat() if d.admin_reviewed_at else None,
                "createdAt": d.created_at.isoformat() if d.created_at else None,
            }
            for d in deliverables
        ]
        
        return ApiResponse(code=200, message="获取成功", data={
            "id": assignment.id,
            "orderId": assignment.order_id,
            "order": order_info,
            "status": assignment.status.value,
            "schedule": assignment.schedule,
            "currentStageOrder": assignment.current_stage_order,
            "deliverables": deliverables_data,
            "assignedAt": assignment.assigned_at.isoformat() if assignment.assigned_at else None,
            "respondedAt": assignment.responded_at.isoformat() if assignment.responded_at else None,
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/assignments/{assignment_id}/accept")
async def accept_assignment(
    assignment_id: str,
    current_user: AnyUser = Depends(require_contractor),
    db: AsyncSession = Depends(get_db)
):
    """承包商接单"""
    try:
        result = await db.execute(
            select(ContractorAssignment).where(
                ContractorAssignment.id == assignment_id,
                ContractorAssignment.contractor_id == current_user.id
            )
        )
        assignment = result.scalar_one_or_none()
        
        if not assignment:
            raise HTTPException(status_code=404, detail="派单不存在")
        
        if assignment.status != AssignmentStatus.PENDING:
            raise HTTPException(status_code=400, detail="当前状态不可接单")
        
        now = datetime.now(timezone.utc)
        assignment.status = AssignmentStatus.IN_PROGRESS
        assignment.responded_at = now
        
        # 激活第一个环节
        schedule = assignment.schedule or []
        if schedule:
            schedule[0]["status"] = "active"
            assignment.schedule = schedule
        
        await db.commit()
        await db.refresh(assignment)
        
        return ApiResponse(code=200, message="接单成功", data={
            "id": assignment.id,
            "status": assignment.status.value,
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/assignments/{assignment_id}/reject")
async def reject_assignment(
    assignment_id: str,
    data: RejectAssignmentRequest,
    current_user: AnyUser = Depends(require_contractor),
    db: AsyncSession = Depends(get_db)
):
    """承包商拒单"""
    try:
        result = await db.execute(
            select(ContractorAssignment).where(
                ContractorAssignment.id == assignment_id,
                ContractorAssignment.contractor_id == current_user.id
            )
        )
        assignment = result.scalar_one_or_none()
        
        if not assignment:
            raise HTTPException(status_code=404, detail="派单不存在")
        
        if assignment.status != AssignmentStatus.PENDING:
            raise HTTPException(status_code=400, detail="当前状态不可拒单")
        
        now = datetime.now(timezone.utc)
        assignment.status = AssignmentStatus.REJECTED
        assignment.reject_reason = data.reject_reason
        assignment.responded_at = now
        
        await db.commit()
        await db.refresh(assignment)
        
        return ApiResponse(code=200, message="已拒单", data={
            "id": assignment.id,
            "status": assignment.status.value,
            "rejectReason": assignment.reject_reason,
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 交付物管理 ==========

@router.post("/deliverables")
async def create_deliverable(
    data: DeliverableCreate,
    current_user: AnyUser = Depends(require_contractor),
    db: AsyncSession = Depends(get_db)
):
    """创建交付物（草稿状态）"""
    try:
        # 验证派单归属
        a_result = await db.execute(
            select(ContractorAssignment).where(
                ContractorAssignment.id == data.assignment_id,
                ContractorAssignment.contractor_id == current_user.id
            )
        )
        assignment = a_result.scalar_one_or_none()
        if not assignment:
            raise HTTPException(status_code=404, detail="派单不存在")
        
        if assignment.status not in [AssignmentStatus.ACCEPTED, AssignmentStatus.IN_PROGRESS]:
            raise HTTPException(status_code=400, detail="当前派单状态不可上传交付物")
        
        # 计算版本号（查找同一环节的历史交付物）
        v_result = await db.execute(
            select(ContractorDeliverable).where(
                ContractorDeliverable.assignment_id == data.assignment_id,
                ContractorDeliverable.stage_config_id == data.stage_config_id,
            ).order_by(ContractorDeliverable.version.desc())
        )
        latest = v_result.scalars().first()
        version = (latest.version + 1) if latest else 1
        parent_id = latest.id if latest and latest.status == DeliverableStatus.ADMIN_REJECTED else None
        
        deliverable = ContractorDeliverable(
            id=generate_id("dlv"),
            assignment_id=data.assignment_id,
            stage_config_id=data.stage_config_id,
            stage_name=data.stage_name,
            stage_order=data.stage_order,
            version=version,
            parent_id=parent_id,
            files=data.files or [],
            description=data.description,
            self_review_checks=data.self_review_checks or {},
            status=DeliverableStatus.DRAFT,
        )
        
        db.add(deliverable)
        await db.commit()
        await db.refresh(deliverable)
        
        return ApiResponse(code=201, message="交付物已创建", data={
            "id": deliverable.id,
            "version": deliverable.version,
            "status": deliverable.status.value,
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/deliverables/{deliverable_id}")
async def update_deliverable(
    deliverable_id: str,
    data: DeliverableUpdate,
    current_user: AnyUser = Depends(require_contractor),
    db: AsyncSession = Depends(get_db)
):
    """更新交付物（仅草稿状态可编辑）"""
    try:
        result = await db.execute(
            select(ContractorDeliverable).where(ContractorDeliverable.id == deliverable_id)
        )
        deliverable = result.scalar_one_or_none()
        
        if not deliverable:
            raise HTTPException(status_code=404, detail="交付物不存在")
        
        # 验证归属
        a_result = await db.execute(
            select(ContractorAssignment).where(
                ContractorAssignment.id == deliverable.assignment_id,
                ContractorAssignment.contractor_id == current_user.id
            )
        )
        if not a_result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="无权操作")
        
        if deliverable.status != DeliverableStatus.DRAFT:
            raise HTTPException(status_code=400, detail="只有草稿状态的交付物可以编辑")
        
        if data.description is not None:
            deliverable.description = data.description
        if data.files is not None:
            deliverable.files = data.files
        if data.self_review_checks is not None:
            deliverable.self_review_checks = data.self_review_checks
        
        await db.commit()
        await db.refresh(deliverable)
        
        return ApiResponse(code=200, message="更新成功", data={
            "id": deliverable.id,
            "status": deliverable.status.value,
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/deliverables/{deliverable_id}/submit")
async def submit_deliverable(
    deliverable_id: str,
    current_user: AnyUser = Depends(require_contractor),
    db: AsyncSession = Depends(get_db)
):
    """提交交付物审核（需完成所有自审核检查项）"""
    try:
        result = await db.execute(
            select(ContractorDeliverable).where(ContractorDeliverable.id == deliverable_id)
        )
        deliverable = result.scalar_one_or_none()
        
        if not deliverable:
            raise HTTPException(status_code=404, detail="交付物不存在")
        
        # 验证归属
        a_result = await db.execute(
            select(ContractorAssignment).where(
                ContractorAssignment.id == deliverable.assignment_id,
                ContractorAssignment.contractor_id == current_user.id
            )
        )
        if not a_result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="无权操作")
        
        if deliverable.status != DeliverableStatus.DRAFT:
            raise HTTPException(status_code=400, detail="只有草稿状态的交付物可以提交")
        
        # 检查自审核是否全部通过
        checks = deliverable.self_review_checks or {}
        if not checks:
            raise HTTPException(status_code=400, detail="请先完成所有审核检查项")
        
        unchecked = [k for k, v in checks.items() if not v]
        if unchecked:
            raise HTTPException(
                status_code=400,
                detail=f"以下审核项未通过：{', '.join(unchecked)}"
            )
        
        # 检查是否有文件
        if not deliverable.files:
            raise HTTPException(status_code=400, detail="请至少上传一个文件")
        
        deliverable.status = DeliverableStatus.SUBMITTED
        
        await db.commit()
        await db.refresh(deliverable)
        
        # TODO: 通知管理员有新交付物待审核
        
        return ApiResponse(code=200, message="交付物已提交审核", data={
            "id": deliverable.id,
            "status": deliverable.status.value,
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 个人信息 ==========

@router.get("/profile")
async def get_contractor_profile(
    current_user: AnyUser = Depends(require_contractor),
    db: AsyncSession = Depends(get_db)
):
    """获取承包商个人信息"""
    return ApiResponse(code=200, message="获取成功", data={
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "phone": current_user.phone,
        "realName": current_user.real_name,
        "company": current_user.company,
        "address": current_user.address,
        "specialty": current_user.specialty,
        "expertise": current_user.expertise,
        "createdAt": current_user.created_at.isoformat() if current_user.created_at else None,
    })


@router.put("/profile")
async def update_contractor_profile(
    data: ProfileUpdate,
    current_user: AnyUser = Depends(require_contractor),
    db: AsyncSession = Depends(get_db)
):
    """更新承包商个人信息"""
    try:
        if data.email is not None:
            current_user.email = data.email
        if data.real_name is not None:
            current_user.real_name = data.real_name
        if data.company is not None:
            current_user.company = data.company
        if data.address is not None:
            current_user.address = data.address
        if data.specialty is not None:
            current_user.specialty = data.specialty
        if data.expertise is not None:
            current_user.expertise = data.expertise
        
        await db.commit()
        await db.refresh(current_user)
        
        return ApiResponse(code=200, message="更新成功", data={
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
