"""管理员管理承包商 API 路由"""

import copy
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm.attributes import flag_modified
from typing import Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
import secrets

from app.database import get_db
from app.models.contractor import Contractor
from app.models.contractor_invitation import ContractorInvitation
from app.models.contractor_assignment import ContractorAssignment, AssignmentStatus
from app.models.contractor_deliverable import ContractorDeliverable, DeliverableStatus
from app.models.staff_member import StaffMember
from app.models.staff_assignment import StaffAssignment, StaffAssignmentStatus
from app.models.staff_deliverable import StaffDeliverable
from app.models.workflow import WorkflowStageConfig
from app.models.order import Order, OrderStatus
from app.schemas.response import ApiResponse
from app.utils.dependencies import require_admin, AnyUser
from app.utils.validators import generate_id
from app.services.staff_creator_service import (
    serialize_staff_assignment_for_admin,
    serialize_staff_deliverable_for_admin,
)
from app.config import settings
from app.utils.business_log import log_business_event
from app.utils.log_setup import get_module_logger
from app.utils.timezone import beijing_iso, beijing_now, beijing_now_iso, ensure_beijing

router = APIRouter(prefix="/contractor-admin", tags=["承包商管理（管理端）"])
logger = get_module_logger("contractor")


def _contractor_base_url() -> str:
    return (settings.CONTRACTOR_BASE_URL or "https://contractor.uniquevisionx.com").rstrip("/")


def _contractor_invite_url(token: str) -> str:
    return f"{_contractor_base_url()}/contractor/register?invite={token}"


def _iso_beijing(dt: datetime | None) -> str | None:
    if not dt:
        return None
    return beijing_iso(dt)


def _normalize_admin_comments(comments: list | None) -> list:
    normalized = []
    for comment in comments or []:
        if not isinstance(comment, dict):
            continue
        item = {**comment}
        created_at = item.get("createdAt")
        if isinstance(created_at, str) and created_at and not created_at.endswith("Z") and "+" not in created_at[10:]:
            item["createdAt"] = f"{created_at.replace(' ', 'T')}+08:00"
        normalized.append(item)
    return normalized


def _sign_file_items(items: list | None) -> list:
    copied = copy.deepcopy(items or [])
    if settings.OSS_ENABLED and copied:
        from app.services.oss_service import sign_file_url_fields
        for item in copied:
            sign_file_url_fields(item)
    return copied


def _signed_design_plan(plan: dict | None) -> dict:
    signed = copy.deepcopy(plan or {})
    signed["files"] = _sign_file_items(signed.get("files"))
    return signed


def _status_value(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _serialize_contractor_deliverable_for_admin(d: ContractorDeliverable) -> dict:
    return {
        "id": d.id,
        "creatorType": "contractor",
        "assignmentId": d.assignment_id,
        "stageConfigId": d.stage_config_id,
        "stageName": d.stage_name,
        "stageOrder": d.stage_order,
        "version": d.version,
        "parentId": d.parent_id,
        "files": _sign_file_items(d.files),
        "description": d.description,
        "selfReviewChecks": d.self_review_checks or {},
        "status": d.status.value,
        "adminReviewNote": d.admin_review_note,
        "adminReviewedBy": d.admin_reviewed_by,
        "adminReviewedAt": _iso_beijing(d.admin_reviewed_at),
        "isPublishedToUser": d.is_published_to_user,
        "publishedNote": d.published_note,
        "publishedBy": d.published_by,
        "publishedAt": _iso_beijing(d.published_at),
        "adminComments": _normalize_admin_comments(d.admin_comments),
        "createdAt": _iso_beijing(d.created_at),
    }


def _serialize_staff_deliverable_for_admin_signed(d: StaffDeliverable) -> dict:
    item = serialize_staff_deliverable_for_admin(d)
    item["files"] = _sign_file_items(item.get("files"))
    item["adminComments"] = _normalize_admin_comments(item.get("adminComments"))
    return item


async def _get_admin_deliverable_context(db: AsyncSession, deliverable_id: str):
    result = await db.execute(
        select(ContractorDeliverable).where(ContractorDeliverable.id == deliverable_id)
    )
    deliverable = result.scalar_one_or_none()
    if deliverable:
        assignment_result = await db.execute(
            select(ContractorAssignment).where(ContractorAssignment.id == deliverable.assignment_id)
        )
        return "contractor", deliverable, assignment_result.scalar_one_or_none()

    result = await db.execute(
        select(StaffDeliverable).where(StaffDeliverable.id == deliverable_id)
    )
    deliverable = result.scalar_one_or_none()
    if deliverable:
        assignment_result = await db.execute(
            select(StaffAssignment).where(StaffAssignment.id == deliverable.assignment_id)
        )
        return "staff", deliverable, assignment_result.scalar_one_or_none()

    return None, None, None


# ========== Schemas ==========

class InvitationCreate(BaseModel):
    note: Optional[str] = None
    expires_days: int = 7   # 默认 7 天有效

class AssignOrderRequest(BaseModel):
    order_id: str
    contractor_id: str
    workflow_type: str = "traditional"  # "traditional" | "ai"
    schedule_adjustments: Optional[list[dict]] = None   # 传统流程的天数调整
    # AI流程专用
    demo_deadline: Optional[str] = None     # demo 上传期限 (ISO date)
    final_deadline: Optional[str] = None    # 最终稿上传期限 (ISO date)

class ReviewDeliverableRequest(BaseModel):
    approved: bool
    review_note: Optional[str] = None

class PublishDeliverableRequest(BaseModel):
    published_note: Optional[str] = None    # 管理员可修改备注后推送

class AdvanceStageRequest(BaseModel):
    """手动推进到下一环节"""
    pass

class DesignPlanUpdate(BaseModel):
    """AI方案设计更新"""
    content: Optional[str] = None
    files: Optional[list] = None
    status: Optional[str] = "draft"  # draft | completed


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
        expires_at = beijing_now() + timedelta(days=data.expires_days)
        
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
        log_business_event(
            logger,
            "contractor_invitation_created",
            admin_id=current_user.id,
            invitation_id=invitation.id,
            expires_at=beijing_iso(invitation.expires_at),
            has_note=bool(data.note),
        )
        
        return ApiResponse(code=201, message="邀请链接生成成功", data={
            "id": invitation.id,
            "token": token,
            "inviteUrl": _contractor_invite_url(token),
            "note": invitation.note,
            "expiresAt": beijing_iso(invitation.expires_at),
            "isUsed": False,
            "createdAt": beijing_iso(invitation.created_at),
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试") from e


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
            
            now = beijing_now()
            expires_at = ensure_beijing(inv.expires_at)
            is_expired = expires_at < now if expires_at else False
            
            items.append({
                "id": inv.id,
                "token": inv.token,
                "inviteUrl": _contractor_invite_url(inv.token),
                "note": inv.note,
                "isUsed": inv.is_used,
                "isExpired": is_expired,
                "usedBy": inv.used_by,
                "usedByName": used_by_name,
                "expiresAt": beijing_iso(inv.expires_at),
                "createdAt": beijing_iso(inv.created_at),
            })
        
        return ApiResponse(code=200, message="获取成功", data=items)
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试") from e


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
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试") from e


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
                "createdAt": beijing_iso(c.created_at),
            })
        
        return ApiResponse(code=200, message="获取成功", data={"data": items, "total": total})
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试") from e


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
            "updatedAt": beijing_now_iso(),
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试") from e

# ========== AI方案设计 ==========

@router.get("/orders/{order_id}/design-plan")
async def get_design_plan(
    order_id: str,
    current_user: AnyUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """获取订单的AI设计方案"""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return ApiResponse(code=200, message="获取成功", data=_signed_design_plan(order.design_plan))


@router.put("/orders/{order_id}/design-plan")
async def save_design_plan(
    order_id: str,
    data: DesignPlanUpdate,
    current_user: AnyUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """保存/更新订单的AI设计方案"""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    now = beijing_now_iso()
    plan = order.design_plan or {}
    if data.content is not None:
        plan["content"] = data.content
    if data.files is not None:
        plan["files"] = data.files
    if data.status is not None:
        plan["status"] = data.status
    plan["updatedAt"] = now
    if "createdAt" not in plan:
        plan["createdAt"] = now
    
    order.design_plan = plan
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(order, "design_plan")
    
    await db.commit()
    return ApiResponse(code=200, message="保存成功", data=_signed_design_plan(plan))


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
        assignable_statuses = {
            OrderStatus.IN_PRODUCTION,
            OrderStatus.PENDING_REVIEW,
            OrderStatus.PREVIEW_READY,
            OrderStatus.REVIEW_REJECTED,
            OrderStatus.REVISION_NEEDED,
            OrderStatus.FINAL_PREVIEW,
        }
        if order.status not in assignable_statuses:
            raise HTTPException(
                status_code=400,
                detail="订单进入「内容制作」后才可以派给承包商",
            )
        
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

        active_staff_result = await db.execute(
            select(StaffAssignment.id)
            .where(
                StaffAssignment.order_id == data.order_id,
                StaffAssignment.status == StaffAssignmentStatus.IN_PROGRESS,
            )
            .limit(1)
        )
        if active_staff_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="该订单已分配给内部负责人，不能再派给承包商")
        
        # 4. 根据工作流类型生成排期
        schedule = []
        
        if data.workflow_type == "ai":
            # AI制作流程：两个阶段（Demo + 终稿）
            today = beijing_now().date()
            
            if data.demo_deadline:
                demo_date = datetime.fromisoformat(data.demo_deadline).date() if isinstance(data.demo_deadline, str) else data.demo_deadline
            else:
                demo_date = today + timedelta(days=7)
            
            if data.final_deadline:
                final_date = datetime.fromisoformat(data.final_deadline).date() if isinstance(data.final_deadline, str) else data.final_deadline
            else:
                final_date = demo_date + timedelta(days=7)
            
            schedule = [
                {
                    "stage_config_id": "ai_demo",
                    "name": "Demo上传",
                    "days": (demo_date - today).days,
                    "deadline": demo_date.isoformat(),
                    "status": "pending",
                    "display_order": 1,
                },
                {
                    "stage_config_id": "ai_final",
                    "name": "最终稿交付",
                    "days": (final_date - demo_date).days,
                    "deadline": final_date.isoformat(),
                    "status": "pending",
                    "display_order": 2,
                },
            ]
        else:
            # 传统制作流程：从工作流配置中读取环节
            stages_result = await db.execute(
                select(WorkflowStageConfig)
                .where(WorkflowStageConfig.is_active == True)
                .order_by(WorkflowStageConfig.display_order)
            )
            stages = stages_result.scalars().all()
            
            if not stages:
                raise HTTPException(status_code=400, detail="尚未配置工作流环节，请先在工作流配置中添加环节")
            
            current_date = beijing_now().date()
            adjustments = {adj['stage_config_id']: adj for adj in (data.schedule_adjustments or [])}
            
            for stage in stages:
                adj = adjustments.get(stage.id, {})
                days = adj.get('days', stage.default_days)
                # 如果提供了具体截止日期
                if adj.get('deadline'):
                    deadline = datetime.fromisoformat(adj['deadline']).date()
                    days = (deadline - current_date).days
                else:
                    deadline = current_date + timedelta(days=days)
                
                schedule.append({
                    "stage_config_id": stage.id,
                    "name": stage.name,
                    "days": max(days, 1),
                    "deadline": deadline.isoformat(),
                    "status": "pending",
                    "display_order": stage.display_order,
                })
                current_date = deadline
        
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
        
        # 派单只建立制作者关系，不修改六阶段订单主状态。
        old_order_status = order.status
        
        await db.commit()
        await db.refresh(assignment)
        log_business_event(
            logger,
            "contractor_assignment_created",
            admin_id=current_user.id,
            assignment_id=assignment.id,
            order_id=order.id,
            order_number=order.order_number,
            contractor_id=contractor.id,
            workflow_type=data.workflow_type,
            stage_count=len(schedule),
            order_status_from=old_order_status,
            order_status_to=order.status,
        )
        
        # ====== 发送通知 ======
        notification_status = {"email": "skipped", "inApp": "sent"}
        
        # 1. 站内信
        from app.models.notification import Notification, NotificationType
        notification = Notification(
            user_id=contractor.id,
            order_id=data.order_id,
            type=NotificationType.CONTRACTOR_ASSIGNMENT,
            title=f"新派单通知 - {order.order_number}",
            content=f"您收到一个新的项目派单（订单 {order.order_number}），请尽快查看并确认接单。",
        )
        db.add(notification)
        await db.commit()
        
        # 2. 邮件通知
        if contractor.email:
            try:
                from app.services.email_service import EmailService
                design_summary = ""
                if order.design_plan and order.design_plan.get("content"):
                    design_summary = order.design_plan["content"]
                
                login_url = f"{_contractor_base_url()}/contractor/login"
                
                email_sent = await EmailService.send_assignment_notification(
                    contractor_email=contractor.email,
                    contractor_name=contractor.real_name or contractor.username,
                    order_number=order.order_number,
                    design_summary=design_summary,
                    login_url=login_url,
                )
                notification_status["email"] = "sent" if email_sent else "failed"
            except Exception as e:
                log_business_event(
                    logger,
                    "contractor_assignment_email_failed",
                    level="warning",
                    admin_id=current_user.id,
                    assignment_id=assignment.id,
                    order_id=order.id,
                    contractor_id=contractor.id,
                    email=contractor.email,
                    error=str(e),
                )
                notification_status["email"] = "failed"
        
        return ApiResponse(code=201, message="派单成功", data={
            "id": assignment.id,
            "orderId": assignment.order_id,
            "contractorId": assignment.contractor_id,
            "contractorName": contractor.username,
            "status": assignment.status.value,
            "schedule": assignment.schedule,
            "assignedAt": beijing_iso(assignment.assigned_at),
            "notificationStatus": notification_status,
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试") from e


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
        contractor_query = select(ContractorAssignment)
        
        if order_id:
            contractor_query = contractor_query.where(ContractorAssignment.order_id == order_id)
        if status:
            contractor_query = contractor_query.where(ContractorAssignment.status == status)
        
        contractor_query = contractor_query.order_by(ContractorAssignment.assigned_at.desc())
        result = await db.execute(contractor_query)
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
            
            # 查交付物统计
            dlv_result = await db.execute(
                select(ContractorDeliverable).where(ContractorDeliverable.assignment_id == a.id)
            )
            deliverables = dlv_result.scalars().all()
            pending_review = sum(1 for d in deliverables if d.status == DeliverableStatus.SUBMITTED)
            
            items.append({
                "id": a.id,
                "creatorType": "contractor",
                "creatorId": a.contractor_id,
                "creatorName": contractor.username if contractor else None,
                "orderId": a.order_id,
                "orderNumber": order.order_number if order else None,
                "contractorId": a.contractor_id,
                "contractorName": contractor.username if contractor else None,
                "status": a.status.value,
                "rejectReason": a.reject_reason,
                "schedule": a.schedule,
                "currentStageOrder": a.current_stage_order,
                "pendingReviewCount": pending_review,
                "totalDeliverables": len(deliverables),
                "assignedAt": beijing_iso(a.assigned_at),
                "respondedAt": beijing_iso(a.responded_at),
                "completedAt": beijing_iso(a.completed_at),
            })

        staff_query = select(StaffAssignment)
        include_staff = True
        if order_id:
            staff_query = staff_query.where(StaffAssignment.order_id == order_id)
        if status:
            try:
                staff_status = StaffAssignmentStatus(status)
            except ValueError:
                include_staff = False
            else:
                staff_query = staff_query.where(StaffAssignment.status == staff_status)

        if include_staff:
            staff_query = staff_query.order_by(StaffAssignment.assigned_at.desc())
            staff_result = await db.execute(staff_query)
            staff_assignments = staff_result.scalars().all()

            for a in staff_assignments:
                staff_result = await db.execute(
                    select(StaffMember).where(StaffMember.id == a.staff_id)
                )
                staff = staff_result.scalar_one_or_none()

                order_result = await db.execute(
                    select(Order).where(Order.id == a.order_id)
                )
                order = order_result.scalar_one_or_none()

                dlv_result = await db.execute(
                    select(StaffDeliverable).where(StaffDeliverable.assignment_id == a.id)
                )
                deliverables = dlv_result.scalars().all()
                pending_review = sum(1 for d in deliverables if d.status == DeliverableStatus.SUBMITTED)
                staff_name = (staff.real_name or staff.username) if staff else a.staff_id

                items.append(serialize_staff_assignment_for_admin(
                    a,
                    staff_name=staff_name,
                    order_number=order.order_number if order else None,
                    pending_review_count=pending_review,
                    total_deliverables=len(deliverables),
                ))

        items.sort(key=lambda item: item.get("assignedAt") or "", reverse=True)
        total = len(items)
        start = (page - 1) * pageSize
        items = items[start:start + pageSize]
        
        return ApiResponse(code=200, message="获取成功", data={"data": items, "total": total})
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试") from e


# ========== 交付物管理 ==========

@router.get("/assignments/{assignment_id}/deliverables")
async def get_assignment_deliverables(
    assignment_id: str,
    current_user: AnyUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """管理员获取某个派单的所有交付物"""
    try:
        staff_assignment_result = await db.execute(
            select(StaffAssignment).where(StaffAssignment.id == assignment_id)
        )
        staff_assignment = staff_assignment_result.scalar_one_or_none()
        if staff_assignment:
            result = await db.execute(
                select(StaffDeliverable)
                .where(StaffDeliverable.assignment_id == assignment_id)
                .order_by(StaffDeliverable.created_at.desc(), StaffDeliverable.stage_order.asc(), StaffDeliverable.version.desc())
            )
            items = [
                _serialize_staff_deliverable_for_admin_signed(d)
                for d in result.scalars().all()
            ]
            return ApiResponse(code=200, message="获取成功", data=items)

        result = await db.execute(
            select(ContractorDeliverable)
            .where(ContractorDeliverable.assignment_id == assignment_id)
            .order_by(ContractorDeliverable.created_at.desc(), ContractorDeliverable.stage_order.asc(), ContractorDeliverable.version.desc())
        )
        deliverables = result.scalars().all()
        
        items = [
            _serialize_contractor_deliverable_for_admin(d)
            for d in deliverables
        ]
        
        return ApiResponse(code=200, message="获取成功", data=items)
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试") from e


@router.put("/deliverables/{deliverable_id}/review")
async def review_deliverable(
    deliverable_id: str,
    data: ReviewDeliverableRequest,
    current_user: AnyUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """管理员审核承包商提交的交付物"""
    try:
        creator_type, deliverable, assignment = await _get_admin_deliverable_context(db, deliverable_id)
        
        if not deliverable:
            raise HTTPException(status_code=404, detail="交付物不存在")
        
        if deliverable.status != DeliverableStatus.SUBMITTED:
            raise HTTPException(status_code=400, detail="该交付物当前状态不可审核")
        
        now = beijing_now()
        
        if data.approved:
            deliverable.status = DeliverableStatus.ADMIN_APPROVED
        else:
            deliverable.status = DeliverableStatus.ADMIN_REJECTED
        
        deliverable.admin_review_note = data.review_note
        deliverable.admin_reviewed_by = current_user.id
        deliverable.admin_reviewed_at = now
        
        await db.commit()
        await db.refresh(deliverable)
        log_business_event(
            logger,
            f"{creator_type}_deliverable_reviewed",
            admin_id=current_user.id,
            deliverable_id=deliverable.id,
            assignment_id=deliverable.assignment_id,
            stage_name=deliverable.stage_name,
            version=deliverable.version,
            approved=data.approved,
            status=deliverable.status,
        )
        
        # 通知制作者审核结果
        try:
            from app.models.notification import Notification, NotificationType
            
            if assignment:
                order_result = await db.execute(
                    select(Order).where(Order.id == assignment.order_id)
                )
                order = order_result.scalar_one_or_none()
                order_number = order.order_number if order else "未知订单"
                
                # 创建通知
                stage_name = deliverable.stage_name or '未知环节'
                status_str = "已通过" if data.approved else "被驳回"
                notif_type = NotificationType.PREVIEW_REVIEW_APPROVED if data.approved else NotificationType.PREVIEW_REVIEW_REJECTED
                recipient_id = assignment.staff_id if creator_type == "staff" else assignment.contractor_id
                creator_label = "内部制作者" if creator_type == "staff" else "承包商"
                
                notif = Notification(
                    user_id=recipient_id,
                    order_id=assignment.order_id,
                    type=notif_type,
                    title=f"交付物审核{status_str} - {order_number}",
                    content=f"{creator_label}提交的「{stage_name}」环节交付物（V{deliverable.version}）审核{status_str}。{f'备注：{data.review_note}' if data.review_note else ''}"
                )
                db.add(notif)
                await db.commit()
        except Exception as notify_err:
            import logging
            logging.getLogger(__name__).warning(f"发送审核结果通知失败: {notify_err}")
        
        status_text = "审核通过" if data.approved else "审核驳回"
        return ApiResponse(code=200, message=f"交付物{status_text}", data={
            "id": deliverable.id,
            "status": deliverable.status.value,
            "adminReviewNote": deliverable.admin_review_note,
            "adminReviewedBy": current_user.id,
            "adminReviewedAt": _iso_beijing(deliverable.admin_reviewed_at) or now.isoformat(),
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试") from e


@router.put("/deliverables/{deliverable_id}/publish")
async def publish_deliverable_to_user(
    deliverable_id: str,
    data: PublishDeliverableRequest,
    current_user: AnyUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """管理员将审核通过的交付物推送给用户"""
    try:
        creator_type, deliverable, assignment = await _get_admin_deliverable_context(db, deliverable_id)
        
        if not deliverable:
            raise HTTPException(status_code=404, detail="交付物不存在")
        
        if deliverable.status != DeliverableStatus.ADMIN_APPROVED:
            raise HTTPException(status_code=400, detail="只有审核通过的交付物才能推送给用户")
        
        now = beijing_now()
        deliverable.is_published_to_user = True
        deliverable.published_note = data.published_note
        deliverable.published_at = now
        deliverable.published_by = current_user.id
        
        await db.commit()
        await db.refresh(deliverable)
        log_business_event(
            logger,
            f"{creator_type}_deliverable_published",
            admin_id=current_user.id,
            deliverable_id=deliverable.id,
            assignment_id=deliverable.assignment_id,
            stage_name=deliverable.stage_name,
            version=deliverable.version,
            status=deliverable.status,
            has_published_note=bool(data.published_note),
        )
        
        # 站内信和邮件分别发送：任一渠道失败都不影响交付物已经发布的结果。
        order = None
        if assignment:
            try:
                order_result = await db.execute(
                    select(Order).where(Order.id == assignment.order_id)
                )
                order = order_result.scalar_one_or_none()
            except Exception as order_err:
                logger.warning("查询交付物所属订单失败: %s", order_err)

        if order:
            order_number = order.order_number
            stage_name = deliverable.stage_name or "未知环节"

            try:
                from app.models.notification import Notification, NotificationType

                notif = Notification(
                    user_id=order.user_id,
                    order_id=order.id,
                    type=NotificationType.PREVIEW_READY,
                    title=f"新交付物 - {order_number}",
                    content=f"您的订单 {order_number}「{stage_name}」环节的交付物已发布，请查看。",
                )
                db.add(notif)
                await db.commit()
            except Exception as notification_err:
                await db.rollback()
                logger.warning("发送交付物站内通知失败: %s", notification_err)

            try:
                from app.models.user import User
                from app.services.email_service import EmailService

                user_result = await db.execute(
                    select(User).where(User.id == order.user_id)
                )
                user = user_result.scalar_one_or_none()
                if user and user.email:
                    email_sent = await EmailService.send_deliverable_published_notification(
                        user.email,
                        order_number,
                        stage_name,
                        data.published_note,
                    )
                    log_business_event(
                        logger,
                        "deliverable_publish_email_sent" if email_sent else "deliverable_publish_email_failed",
                        level="info" if email_sent else "warning",
                        admin_id=current_user.id,
                        user_id=order.user_id,
                        order_id=order.id,
                        deliverable_id=deliverable.id,
                        creator_type=creator_type,
                    )
                else:
                    log_business_event(
                        logger,
                        "deliverable_publish_email_skipped",
                        level="warning",
                        admin_id=current_user.id,
                        user_id=order.user_id,
                        order_id=order.id,
                        deliverable_id=deliverable.id,
                        reason="user_email_missing",
                    )
            except Exception as email_err:
                logger.warning("发送交付物邮件通知失败: %s", email_err)
        
        return ApiResponse(code=200, message="交付物已推送给用户", data={
            "id": deliverable.id,
            "isPublishedToUser": True,
            "publishedNote": deliverable.published_note,
            "publishedBy": current_user.id,
            "publishedAt": _iso_beijing(deliverable.published_at) or now.isoformat(),
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试") from e


async def _advance_staff_assignment_to_next_stage(
    assignment_id: str,
    current_user: AnyUser,
    db: AsyncSession,
) -> ApiResponse:
    result = await db.execute(
        select(StaffAssignment).where(StaffAssignment.id == assignment_id)
    )
    assignment = result.scalar_one_or_none()

    if not assignment:
        raise HTTPException(status_code=404, detail="派单记录不存在")

    if assignment.status != StaffAssignmentStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="当前派单状态不可推进")

    schedule = assignment.schedule or []
    if not schedule:
        raise HTTPException(status_code=400, detail="当前派单未配置工作流排期")

    try:
        current_order = int(assignment.current_stage_order or "1")
    except ValueError:
        raise HTTPException(status_code=400, detail="当前派单工作流状态异常")

    def _is_current_stage(stage: dict) -> bool:
        try:
            return int(stage.get("display_order")) == current_order
        except (TypeError, ValueError):
            return False

    current_stage = next((s for s in schedule if _is_current_stage(s)), None)
    if not current_stage:
        raise HTTPException(status_code=400, detail="当前工作流环节不存在")

    approved_result = await db.execute(
        select(func.count()).select_from(StaffDeliverable).where(
            StaffDeliverable.assignment_id == assignment.id,
            StaffDeliverable.stage_config_id == current_stage.get("stage_config_id"),
            StaffDeliverable.stage_order == current_order,
            StaffDeliverable.status == DeliverableStatus.ADMIN_APPROVED,
        )
    )
    if (approved_result.scalar() or 0) < 1:
        raise HTTPException(status_code=400, detail="当前环节需要至少一个已审核通过的交付物才能推进")

    for stage in schedule:
        if stage.get("display_order") == current_order:
            stage["status"] = "completed"

    next_order = current_order + 1
    has_next = any(s.get("display_order") == next_order for s in schedule)

    if has_next:
        for stage in schedule:
            if stage.get("display_order") == next_order:
                stage["status"] = "active"
        assignment.current_stage_order = str(next_order)
        message = f"已推进到第 {next_order} 环节"
    else:
        assignment.status = StaffAssignmentStatus.COMPLETED
        assignment.completed_at = beijing_now()
        message = "所有环节已完成"

        order_result = await db.execute(
            select(Order).where(Order.id == assignment.order_id)
        )
        order = order_result.scalar_one_or_none()
        from app.models.order import OrderStatus
        if order and order.status == OrderStatus.IN_PRODUCTION:
            order.status = OrderStatus.PREVIEW_READY
            message += "，订单已推进到「初稿交付」"

    assignment.schedule = schedule
    flag_modified(assignment, "schedule")

    await db.commit()
    await db.refresh(assignment)
    log_business_event(
        logger,
        "staff_assignment_advanced",
        admin_id=current_user.id,
        assignment_id=assignment.id,
        order_id=assignment.order_id,
        staff_id=assignment.staff_id,
        stage_from=current_order,
        stage_to=next_order if has_next else None,
        has_next=has_next,
        assignment_status=assignment.status,
    )

    try:
        from app.models.notification import Notification, NotificationType

        order_result = await db.execute(
            select(Order).where(Order.id == assignment.order_id)
        )
        order = order_result.scalar_one_or_none()
        order_number = order.order_number if order else "未知订单"

        if has_next:
            next_stage_name = next((s.get("name", "") for s in schedule if s.get("display_order") == next_order), "")
            notif = Notification(
                user_id=assignment.staff_id,
                order_id=assignment.order_id,
                type=NotificationType.CONTRACTOR_ASSIGNMENT,
                title=f"环节推进 - {order_number}",
                content=f"订单 {order_number} 已推进到下一环节「{next_stage_name}」，请继续完成交付。",
            )
        else:
            notif = Notification(
                user_id=assignment.staff_id,
                order_id=assignment.order_id,
                type=NotificationType.ORDER_COMPLETED,
                title=f"制作任务完成 - {order_number}",
                content=f"订单 {order_number} 的所有工作环节已完成，感谢您的工作。",
            )
        db.add(notif)
        await db.commit()
    except Exception as notify_err:
        import logging
        logging.getLogger(__name__).warning(f"发送内部制作者环节推进通知失败: {notify_err}")

    return ApiResponse(code=200, message=message, data={
        "id": assignment.id,
        "status": assignment.status.value,
        "currentStageOrder": assignment.current_stage_order,
        "schedule": assignment.schedule,
        "advancedAt": beijing_now_iso(),
        "completedAt": _iso_beijing(assignment.completed_at),
    })


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
            return await _advance_staff_assignment_to_next_stage(assignment_id, current_user, db)
        
        if assignment.status not in [AssignmentStatus.ACCEPTED, AssignmentStatus.IN_PROGRESS]:
            raise HTTPException(status_code=400, detail="当前派单状态不可推进")
        
        # 解析排期，找到当前和下一个环节
        schedule = assignment.schedule or []
        if not schedule:
            raise HTTPException(status_code=400, detail="当前派单未配置工作流排期")

        try:
            current_order = int(assignment.current_stage_order or "1")
        except ValueError:
            raise HTTPException(status_code=400, detail="当前派单工作流状态异常")

        def _is_current_stage(stage: dict) -> bool:
            try:
                return int(stage.get("display_order")) == current_order
            except (TypeError, ValueError):
                return False

        current_stage = next((s for s in schedule if _is_current_stage(s)), None)
        if not current_stage:
            raise HTTPException(status_code=400, detail="当前工作流环节不存在")

        approved_result = await db.execute(
            select(func.count()).select_from(ContractorDeliverable).where(
                ContractorDeliverable.assignment_id == assignment.id,
                ContractorDeliverable.stage_config_id == current_stage.get("stage_config_id"),
                ContractorDeliverable.stage_order == current_order,
                ContractorDeliverable.status == DeliverableStatus.ADMIN_APPROVED,
            )
        )
        if (approved_result.scalar() or 0) < 1:
            raise HTTPException(status_code=400, detail="当前环节需要至少一个已审核通过的交付物才能推进")
        
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
            assignment.completed_at = beijing_now()
            message = "所有环节已完成"
            
            # 同步推进订单状态：制作中 → 初稿交付
            from app.models.order import Order, OrderStatus
            order_result = await db.execute(
                select(Order).where(Order.id == assignment.order_id)
            )
            order = order_result.scalar_one_or_none()
            if order and order.status == OrderStatus.IN_PRODUCTION:
                order.status = OrderStatus.PREVIEW_READY
                message += "，订单已推进到「初稿交付」"
        
        assignment.schedule = schedule  # 更新 JSON 字段
        flag_modified(assignment, "schedule")
        
        await db.commit()
        await db.refresh(assignment)
        log_business_event(
            logger,
            "contractor_assignment_advanced",
            admin_id=current_user.id,
            assignment_id=assignment.id,
            order_id=assignment.order_id,
            contractor_id=assignment.contractor_id,
            stage_from=current_order,
            stage_to=next_order if has_next else None,
            has_next=has_next,
            assignment_status=assignment.status,
        )
        
        # 通知承包商环节推进
        try:
            from app.models.notification import Notification, NotificationType
            
            order_result = await db.execute(
                select(Order).where(Order.id == assignment.order_id)
            )
            order = order_result.scalar_one_or_none()
            order_number = order.order_number if order else "未知订单"
            
            if has_next:
                # 通知承包商进入下一环节
                next_stage_name = next((s.get("name", "") for s in schedule if s.get("display_order") == next_order), "")
                notif = Notification(
                    user_id=assignment.contractor_id,
                    order_id=assignment.order_id,
                    type=NotificationType.CONTRACTOR_ASSIGNMENT,
                    title=f"环节推进 - {order_number}",
                    content=f"订单 {order_number} 已推进到下一环节「{next_stage_name}」，请继续完成交付。",
                )
            else:
                # 通知承包商所有环节完成
                notif = Notification(
                    user_id=assignment.contractor_id,
                    order_id=assignment.order_id,
                    type=NotificationType.ORDER_COMPLETED,
                    title=f"派单完成 - {order_number}",
                    content=f"订单 {order_number} 的所有工作环节已完成，感谢您的工作。",
                )
            db.add(notif)
            await db.commit()
        except Exception as notify_err:
            import logging
            logging.getLogger(__name__).warning(f"发送环节推进通知失败: {notify_err}")
        
        return ApiResponse(code=200, message=message, data={
            "id": assignment.id,
            "status": assignment.status.value,
            "currentStageOrder": assignment.current_stage_order,
            "schedule": assignment.schedule,
            "advancedAt": beijing_now_iso(),
            "completedAt": _iso_beijing(assignment.completed_at),
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试") from e


# ========== 管理员评论（给 Contractor 的反馈） ==========

class AdminCommentRequest(BaseModel):
    content: str


@router.post("/deliverables/{deliverable_id}/comment")
async def add_admin_comment(
    deliverable_id: str,
    data: AdminCommentRequest,
    current_user: AnyUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """管理员对交付物添加评论（Contractor 可见，随时可添加）"""
    try:
        creator_type, deliverable, assignment = await _get_admin_deliverable_context(db, deliverable_id)
        
        if not deliverable:
            raise HTTPException(status_code=404, detail="交付物不存在")
        
        if not data.content.strip():
            raise HTTPException(status_code=400, detail="评论内容不能为空")
        
        now = beijing_now()
        admin_name = current_user.username if hasattr(current_user, 'username') else '管理员'
        
        # 追加到 admin_comments JSON 数组
        comments = deliverable.admin_comments or []
        comments.append({
            "id": generate_id("comment"),
            "content": data.content.strip(),
            "createdBy": current_user.id,
            "createdByName": admin_name,
            "createdAt": now.isoformat(),
        })
        deliverable.admin_comments = comments
        
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(deliverable, "admin_comments")
        
        await db.commit()
        await db.refresh(deliverable)
        log_business_event(
            logger,
            f"{creator_type}_deliverable_commented",
            admin_id=current_user.id,
            deliverable_id=deliverable.id,
            assignment_id=deliverable.assignment_id,
            comment_count=len(deliverable.admin_comments or []),
        )
        
        # 通知制作者有新评论
        try:
            from app.models.notification import Notification, NotificationType
            
            if assignment:
                order_result = await db.execute(
                    select(Order).where(Order.id == assignment.order_id)
                )
                order = order_result.scalar_one_or_none()
                order_number = order.order_number if order else "未知订单"
                stage_name = deliverable.stage_name or '未知环节'
                recipient_id = assignment.staff_id if creator_type == "staff" else assignment.contractor_id
                
                notif = Notification(
                    user_id=recipient_id,
                    order_id=assignment.order_id,
                    type=NotificationType.NEW_FEEDBACK,
                    title=f"管理员评论 - {order_number}",
                    content=f"管理员对「{stage_name}」环节的交付物（V{deliverable.version}）添加了新评论：{data.content[:80]}",
                )
                db.add(notif)
                await db.commit()
        except Exception as notify_err:
            import logging
            logging.getLogger(__name__).warning(f"发送评论通知失败: {notify_err}")
        
        return ApiResponse(code=200, message="评论已添加", data={
            "id": deliverable.id,
            "adminComments": _normalize_admin_comments(deliverable.admin_comments),
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试") from e
