"""管理员管理承包商 API 路由"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
import secrets

from app.database import get_db
from app.models.contractor import Contractor
from app.models.contractor_invitation import ContractorInvitation
from app.models.contractor_assignment import ContractorAssignment, AssignmentStatus
from app.models.contractor_deliverable import ContractorDeliverable, DeliverableStatus
from app.models.workflow import WorkflowStageConfig
from app.models.order import Order
from app.schemas.response import ApiResponse
from app.utils.dependencies import require_admin, AnyUser
from app.utils.validators import generate_id
from app.config import settings

router = APIRouter(prefix="/contractor-admin", tags=["承包商管理（管理端）"])


# ========== Schemas ==========

class InvitationCreate(BaseModel):
    note: Optional[str] = None
    expires_days: int = 7   # 默认 7 天有效

class AssignOrderRequest(BaseModel):
    order_id: str
    contractor_id: str
    schedule_adjustments: Optional[list[dict]] = None   # 可选的天数调整

class ReviewDeliverableRequest(BaseModel):
    approved: bool
    review_note: Optional[str] = None

class PublishDeliverableRequest(BaseModel):
    published_note: Optional[str] = None    # 管理员可修改备注后推送

class AdvanceStageRequest(BaseModel):
    """手动推进到下一环节"""
    pass


# ========== 邀请链接管理 ==========

@router.post("/invitations")
async def create_invitation(
    data: InvitationCreate,
    current_user: AnyUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """生成承包商邀请链接"""
    try:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=data.expires_days)
        
        invitation = ContractorInvitation(
            id=generate_id("invite"),
            token=token,
            created_by=current_user.id,
            note=data.note,
            expires_at=expires_at,
            is_used=False
        )
        
        db.add(invitation)
        await db.commit()
        await db.refresh(invitation)
        
        # 生成完整的邀请链接
        base_url = getattr(settings, 'CONTRACTOR_BASE_URL', '') or f"http://localhost:3000"
        invite_url = f"{base_url}/contractor/register?invite={token}"
        
        return ApiResponse(code=201, message="邀请链接生成成功", data={
            "id": invitation.id,
            "token": token,
            "inviteUrl": invite_url,
            "note": invitation.note,
            "expiresAt": invitation.expires_at.isoformat(),
            "isUsed": False,
            "createdAt": invitation.created_at.isoformat() if invitation.created_at else None,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/invitations")
async def get_invitations(
    current_user: AnyUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """获取所有邀请链接列表"""
    try:
        result = await db.execute(
            select(ContractorInvitation).order_by(ContractorInvitation.created_at.desc())
        )
        invitations = result.scalars().all()
        
        items = []
        for inv in invitations:
            # 查找使用者信息
            used_by_name = None
            if inv.used_by:
                c_result = await db.execute(
                    select(Contractor).where(Contractor.id == inv.used_by)
                )
                contractor = c_result.scalar_one_or_none()
                if contractor:
                    used_by_name = contractor.username
            
            now = datetime.now(timezone.utc)
            is_expired = inv.expires_at.replace(tzinfo=timezone.utc) < now if inv.expires_at else False
            
            items.append({
                "id": inv.id,
                "token": inv.token,
                "note": inv.note,
                "isUsed": inv.is_used,
                "isExpired": is_expired,
                "usedBy": inv.used_by,
                "usedByName": used_by_name,
                "expiresAt": inv.expires_at.isoformat() if inv.expires_at else None,
                "createdAt": inv.created_at.isoformat() if inv.created_at else None,
            })
        
        return ApiResponse(code=200, message="获取成功", data=items)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/invitations/{invitation_id}")
async def revoke_invitation(
    invitation_id: str,
    current_user: AnyUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """撤销未使用的邀请链接"""
    try:
        result = await db.execute(
            select(ContractorInvitation).where(ContractorInvitation.id == invitation_id)
        )
        invitation = result.scalar_one_or_none()
        
        if not invitation:
            raise HTTPException(status_code=404, detail="邀请链接不存在")
        
        if invitation.is_used:
            raise HTTPException(status_code=400, detail="该邀请链接已被使用，无法撤销")
        
        await db.delete(invitation)
        await db.commit()
        
        return ApiResponse(code=200, message="邀请链接已撤销", data=None)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 承包商列表管理 ==========

@router.get("/list")
async def get_contractor_list(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = Query(None),
    current_user: AnyUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """获取承包商列表"""
    try:
        query = select(Contractor)
        
        if keyword:
            from sqlalchemy import or_
            query = query.where(
                or_(
                    Contractor.username.ilike(f"%{keyword}%"),
                    Contractor.real_name.ilike(f"%{keyword}%"),
                    Contractor.company.ilike(f"%{keyword}%"),
                )
            )
        
        # 总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # 分页
        query = query.offset((page - 1) * pageSize).limit(pageSize)
        result = await db.execute(query)
        contractors = result.scalars().all()
        
        items = []
        for c in contractors:
            # 查询在手订单数
            assignment_count_query = select(func.count(ContractorAssignment.id)).where(
                ContractorAssignment.contractor_id == c.id,
                ContractorAssignment.status.in_([
                    AssignmentStatus.PENDING,
                    AssignmentStatus.ACCEPTED,
                    AssignmentStatus.IN_PROGRESS,
                ])
            )
            count_result = await db.execute(assignment_count_query)
            active_orders = count_result.scalar()
            
            items.append({
                "id": c.id,
                "username": c.username,
                "email": c.email,
                "phone": c.phone,
                "realName": c.real_name,
                "company": c.company,
                "specialty": c.specialty,
                "expertise": c.expertise,
                "isActive": c.is_active,
                "activeOrders": active_orders,
                "createdAt": c.created_at.isoformat() if c.created_at else None,
            })
        
        return ApiResponse(code=200, message="获取成功", data={"data": items, "total": total})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{contractor_id}")
async def update_contractor(
    contractor_id: str,
    data: dict,
    current_user: AnyUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """编辑承包商信息"""
    try:
        result = await db.execute(
            select(Contractor).where(Contractor.id == contractor_id)
        )
        contractor = result.scalar_one_or_none()
        
        if not contractor:
            raise HTTPException(status_code=404, detail="承包商不存在")
        
        if 'email' in data and data['email'] is not None:
            contractor.email = data['email']
        if 'realName' in data and data['realName'] is not None:
            contractor.real_name = data['realName']
        if 'company' in data and data['company'] is not None:
            contractor.company = data['company']
        if 'specialty' in data and data['specialty'] is not None:
            contractor.specialty = data['specialty']
        if 'expertise' in data and data['expertise'] is not None:
            contractor.expertise = data['expertise']
        if 'isActive' in data and data['isActive'] is not None:
            contractor.is_active = data['isActive']
        
        await db.commit()
        await db.refresh(contractor)
        
        return ApiResponse(code=200, message="更新成功", data={
            "id": contractor.id,
            "username": contractor.username,
            "isActive": contractor.is_active,
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 派单管理 ==========

@router.post("/assign")
async def assign_order_to_contractor(
    data: AssignOrderRequest,
    current_user: AnyUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """管理员给承包商派单"""
    try:
        # 1. 验证订单存在
        order_result = await db.execute(
            select(Order).where(Order.id == data.order_id)
        )
        order = order_result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")
        
        # 2. 验证承包商存在且活跃
        contractor_result = await db.execute(
            select(Contractor).where(Contractor.id == data.contractor_id)
        )
        contractor = contractor_result.scalar_one_or_none()
        if not contractor:
            raise HTTPException(status_code=404, detail="承包商不存在")
        if not contractor.is_active:
            raise HTTPException(status_code=400, detail="该承包商已被禁用")
        
        # 3. 检查是否已有进行中的派单（同一订单同一承包商）
        existing_result = await db.execute(
            select(ContractorAssignment).where(
                ContractorAssignment.order_id == data.order_id,
                ContractorAssignment.status.in_([
                    AssignmentStatus.PENDING,
                    AssignmentStatus.ACCEPTED,
                    AssignmentStatus.IN_PROGRESS,
                ])
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="该订单已有进行中的派单记录")
        
        # 4. 获取工作流环节配置，生成排期
        stages_result = await db.execute(
            select(WorkflowStageConfig)
            .where(WorkflowStageConfig.is_active == True)
            .order_by(WorkflowStageConfig.display_order)
        )
        stages = stages_result.scalars().all()
        
        if not stages:
            raise HTTPException(status_code=400, detail="尚未配置工作流环节，请先在工作流配置中添加环节")
        
        # 生成排期（从今天开始，逐个环节排列）
        schedule = []
        current_date = datetime.now(timezone.utc).date()
        adjustments = {adj['stage_config_id']: adj['days'] for adj in (data.schedule_adjustments or [])}
        
        for stage in stages:
            days = adjustments.get(stage.id, stage.default_days)
            deadline = current_date + timedelta(days=days)
            schedule.append({
                "stage_config_id": stage.id,
                "name": stage.name,
                "days": days,
                "deadline": deadline.isoformat(),
                "status": "pending",
                "display_order": stage.display_order,
            })
            current_date = deadline  # 下一个环节从上一个截止日开始
        
        # 5. 创建派单记录
        assignment = ContractorAssignment(
            id=generate_id("assign"),
            order_id=data.order_id,
            contractor_id=data.contractor_id,
            assigned_by=current_user.id,
            status=AssignmentStatus.PENDING,
            schedule=schedule,
            current_stage_order="1",
        )
        
        db.add(assignment)
        await db.commit()
        await db.refresh(assignment)
        
        return ApiResponse(code=201, message="派单成功", data={
            "id": assignment.id,
            "orderId": assignment.order_id,
            "contractorId": assignment.contractor_id,
            "contractorName": contractor.username,
            "status": assignment.status.value,
            "schedule": assignment.schedule,
            "assignedAt": assignment.assigned_at.isoformat() if assignment.assigned_at else None,
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/assignments")
async def get_all_assignments(
    order_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    current_user: AnyUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """查看所有派单记录"""
    try:
        query = select(ContractorAssignment)
        
        if order_id:
            query = query.where(ContractorAssignment.order_id == order_id)
        if status:
            query = query.where(ContractorAssignment.status == status)
        
        query = query.order_by(ContractorAssignment.assigned_at.desc())
        
        # 总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # 分页
        query = query.offset((page - 1) * pageSize).limit(pageSize)
        result = await db.execute(query)
        assignments = result.scalars().all()
        
        items = []
        for a in assignments:
            # 查承包商名称
            c_result = await db.execute(
                select(Contractor).where(Contractor.id == a.contractor_id)
            )
            contractor = c_result.scalar_one_or_none()
            
            # 查订单编号
            o_result = await db.execute(
                select(Order).where(Order.id == a.order_id)
            )
            order = o_result.scalar_one_or_none()
            
            items.append({
                "id": a.id,
                "orderId": a.order_id,
                "orderNumber": order.order_number if order else None,
                "contractorId": a.contractor_id,
                "contractorName": contractor.username if contractor else None,
                "status": a.status.value,
                "rejectReason": a.reject_reason,
                "schedule": a.schedule,
                "currentStageOrder": a.current_stage_order,
                "assignedAt": a.assigned_at.isoformat() if a.assigned_at else None,
                "respondedAt": a.responded_at.isoformat() if a.responded_at else None,
                "completedAt": a.completed_at.isoformat() if a.completed_at else None,
            })
        
        return ApiResponse(code=200, message="获取成功", data={"data": items, "total": total})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 交付物审核 ==========

@router.put("/deliverables/{deliverable_id}/review")
async def review_deliverable(
    deliverable_id: str,
    data: ReviewDeliverableRequest,
    current_user: AnyUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """管理员审核承包商提交的交付物"""
    try:
        result = await db.execute(
            select(ContractorDeliverable).where(ContractorDeliverable.id == deliverable_id)
        )
        deliverable = result.scalar_one_or_none()
        
        if not deliverable:
            raise HTTPException(status_code=404, detail="交付物不存在")
        
        if deliverable.status != DeliverableStatus.SUBMITTED:
            raise HTTPException(status_code=400, detail="该交付物当前状态不可审核")
        
        now = datetime.now(timezone.utc)
        
        if data.approved:
            deliverable.status = DeliverableStatus.ADMIN_APPROVED
        else:
            deliverable.status = DeliverableStatus.ADMIN_REJECTED
        
        deliverable.admin_review_note = data.review_note
        deliverable.admin_reviewed_by = current_user.id
        deliverable.admin_reviewed_at = now
        
        await db.commit()
        await db.refresh(deliverable)
        
        status_text = "审核通过" if data.approved else "审核驳回"
        return ApiResponse(code=200, message=f"交付物{status_text}", data={
            "id": deliverable.id,
            "status": deliverable.status.value,
            "adminReviewNote": deliverable.admin_review_note,
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/deliverables/{deliverable_id}/publish")
async def publish_deliverable_to_user(
    deliverable_id: str,
    data: PublishDeliverableRequest,
    current_user: AnyUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """管理员将审核通过的交付物推送给用户"""
    try:
        result = await db.execute(
            select(ContractorDeliverable).where(ContractorDeliverable.id == deliverable_id)
        )
        deliverable = result.scalar_one_or_none()
        
        if not deliverable:
            raise HTTPException(status_code=404, detail="交付物不存在")
        
        if deliverable.status != DeliverableStatus.ADMIN_APPROVED:
            raise HTTPException(status_code=400, detail="只有审核通过的交付物才能推送给用户")
        
        now = datetime.now(timezone.utc)
        deliverable.is_published_to_user = True
        deliverable.published_note = data.published_note
        deliverable.published_at = now
        deliverable.published_by = current_user.id
        
        await db.commit()
        await db.refresh(deliverable)
        
        # TODO: 触发用户通知（站内 + 邮件）
        
        return ApiResponse(code=200, message="交付物已推送给用户", data={
            "id": deliverable.id,
            "isPublishedToUser": True,
            "publishedNote": deliverable.published_note,
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/assignments/{assignment_id}/advance")
async def advance_to_next_stage(
    assignment_id: str,
    current_user: AnyUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """管理员手动推进到下一工作流环节"""
    try:
        result = await db.execute(
            select(ContractorAssignment).where(ContractorAssignment.id == assignment_id)
        )
        assignment = result.scalar_one_or_none()
        
        if not assignment:
            raise HTTPException(status_code=404, detail="派单记录不存在")
        
        if assignment.status not in [AssignmentStatus.ACCEPTED, AssignmentStatus.IN_PROGRESS]:
            raise HTTPException(status_code=400, detail="当前派单状态不可推进")
        
        # 解析排期，找到下一个环节
        schedule = assignment.schedule or []
        current_order = int(assignment.current_stage_order or "1")
        
        # 标记当前环节为完成
        for stage in schedule:
            if stage.get("display_order") == current_order:
                stage["status"] = "completed"
        
        next_order = current_order + 1
        has_next = any(s.get("display_order") == next_order for s in schedule)
        
        if has_next:
            # 推进到下一环节
            for stage in schedule:
                if stage.get("display_order") == next_order:
                    stage["status"] = "active"
            assignment.current_stage_order = str(next_order)
            assignment.status = AssignmentStatus.IN_PROGRESS
            message = f"已推进到第 {next_order} 环节"
        else:
            # 所有环节完成
            assignment.status = AssignmentStatus.COMPLETED
            assignment.completed_at = datetime.now(timezone.utc)
            message = "所有环节已完成"
        
        assignment.schedule = schedule  # 更新 JSON 字段
        
        await db.commit()
        await db.refresh(assignment)
        
        return ApiResponse(code=200, message=message, data={
            "id": assignment.id,
            "status": assignment.status.value,
            "currentStageOrder": assignment.current_stage_order,
            "schedule": assignment.schedule,
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
