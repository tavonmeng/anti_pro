"""承包商端 API 路由"""

import copy
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified
from typing import Any, Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime

from app.database import get_db
from app.config import settings
from app.models.user import UserRole
from app.models.contractor import Contractor
from app.models.contractor_invitation import ContractorInvitation
from app.models.contractor_assignment import ContractorAssignment, AssignmentStatus
from app.models.contractor_deliverable import ContractorDeliverable, DeliverableStatus
from app.models.staff_assignment import StaffAssignment, StaffAssignmentStatus
from app.models.staff_deliverable import StaffDeliverable
from app.models.order import Order
from app.schemas.response import ApiResponse
from app.utils.dependencies import require_contractor, require_creator, AnyUser
from app.utils.validators import generate_id
from app.services.auth_service import register_contractor
from app.services.production_asset_service import build_production_assets
from app.services.staff_creator_service import (
    serialize_staff_assignment_for_creator,
    serialize_staff_deliverable_for_creator,
)
from app.utils.business_log import log_business_event
from app.utils.log_setup import get_module_logger
from app.utils.timezone import beijing_iso, beijing_now, beijing_now_iso, ensure_beijing

router = APIRouter(prefix="/contractor", tags=["承包商"])
logger = get_module_logger("contractor")


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


def _first_text(*values: str | None) -> str | None:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return None


def _role_value(user: AnyUser) -> str:
    role = getattr(user, "role", "")
    return role.value if hasattr(role, "value") else str(role)


def _is_staff_creator(user: AnyUser) -> bool:
    return _role_value(user) == UserRole.STAFF.value


def _serialize_creator_profile(user: AnyUser) -> dict[str, Any]:
    is_staff = _is_staff_creator(user)
    return {
        "id": user.id,
        "username": user.username,
        "email": getattr(user, "email", None),
        "phone": getattr(user, "phone", None),
        "realName": getattr(user, "real_name", None),
        "company": getattr(user, "company", None) or "",
        "address": "" if is_staff else (getattr(user, "address", None) or ""),
        "specialty": "" if is_staff else (getattr(user, "specialty", None) or ""),
        "expertise": "" if is_staff else (getattr(user, "expertise", None) or ""),
        "showcaseCases": [] if is_staff else _sign_file_items(getattr(user, "showcase_cases", None)),
        "creatorType": "staff" if is_staff else "contractor",
        "isInternalCreator": is_staff,
        "createdAt": beijing_iso(getattr(user, "created_at", None)),
    }


def _apply_creator_profile_update(user: AnyUser, data: "ProfileUpdate") -> None:
    if data.email is not None:
        user.email = data.email
    if data.real_name is not None:
        user.real_name = data.real_name

    if _is_staff_creator(user):
        return

    if data.company is not None:
        user.company = data.company
    if data.address is not None:
        user.address = data.address
    if data.specialty is not None:
        user.specialty = data.specialty
    if data.expertise is not None:
        user.expertise = data.expertise
    if data.showcase_cases is not None:
        user.showcase_cases = data.showcase_cases


def _status_value(status: Any) -> str:
    return status.value if hasattr(status, "value") else str(status)


def _staff_status_filter(status_filter: str | None) -> StaffAssignmentStatus | None:
    if not status_filter:
        return None
    try:
        return StaffAssignmentStatus(status_filter)
    except ValueError:
        return None


def _build_order_info(order: Order | None, *, detail: bool = False) -> dict[str, Any] | None:
    """制作端订单信息：只保留制作所需字段，不返回客户个人信息。"""
    if not order:
        return None

    order_data = order.order_data or {}
    order_info: dict[str, Any] = {
        "id": order.id,
        "orderNumber": order.order_number,
        "orderType": _status_value(order.order_type),
        "status": _status_value(order.status),
        "brand": order_data.get("brand"),
        "projectName": order_data.get("project_name") or order_data.get("projectName"),
        "content": order_data.get("content"),
        "style": order_data.get("style"),
        "city": order_data.get("city"),
        "city_location": order_data.get("city_location"),
        "media_size": order_data.get("media_size"),
        "media_specs": order_data.get("media_specs"),
        "time_number": order_data.get("time_number"),
        "timing_number": order_data.get("timing_number"),
        "technology": order_data.get("technology"),
        "tech_delivery": order_data.get("tech_delivery"),
        "online_time": order_data.get("online_time"),
        "target_group": order_data.get("target_group"),
        "audience_scene": order_data.get("audience_scene"),
        "background": order_data.get("background"),
        "resource_background": order_data.get("resource_background"),
        "theme_concept": order_data.get("theme_concept"),
        "art_direction": order_data.get("art_direction"),
        "site_photos": _sign_file_items(order_data.get("site_photos") or order_data.get("scenePhotos")),
        "productionAssets": _sign_file_items(build_production_assets(order_data, order.design_plan)),
        "content_review": order_data.get("content_review"),
        "special_requirements": order_data.get("special_requirements"),
        "remarks": order_data.get("remarks"),
        "createdAt": beijing_iso(order.created_at),
    }

    if detail:
        order_info.update({
            "brand_tone": order_data.get("brand_tone"),
            "media_positioning": order_data.get("media_positioning"),
            "viewing_path": order_data.get("viewing_path"),
            "prohibited_content": order_data.get("prohibited_content"),
        })
        if order.design_plan:
            order_info["designPlan"] = {
                "content": order.design_plan.get("content", ""),
                "files": _sign_file_items(order.design_plan.get("files", [])),
                "status": order.design_plan.get("status", "draft"),
            }

    return order_info


def _serialize_deliverable_for_creator(deliverable: ContractorDeliverable | StaffDeliverable) -> dict[str, Any]:
    if isinstance(deliverable, StaffDeliverable):
        dto = serialize_staff_deliverable_for_creator(deliverable)
        dto["files"] = _sign_file_items(dto.get("files"))
        dto["adminComments"] = _normalize_admin_comments(dto.get("adminComments"))
        return dto

    return {
        "id": deliverable.id,
        "stageConfigId": deliverable.stage_config_id,
        "stageName": deliverable.stage_name,
        "stageOrder": deliverable.stage_order,
        "version": deliverable.version,
        "parentId": deliverable.parent_id,
        "files": _sign_file_items(deliverable.files),
        "description": deliverable.description,
        "selfReviewChecks": deliverable.self_review_checks or {},
        "status": deliverable.status.value,
        "adminReviewNote": deliverable.admin_review_note,
        "adminReviewedAt": _iso_beijing(deliverable.admin_reviewed_at),
        "adminComments": _normalize_admin_comments(deliverable.admin_comments),
        "createdAt": _iso_beijing(deliverable.created_at),
    }


async def _latest_assignment_feedback(
    db: AsyncSession,
    assignment_id: str,
    order: Order | None,
    deliverable_model: type[ContractorDeliverable] | type[StaffDeliverable],
) -> dict[str, Any] | None:
    d_result = await db.execute(
        select(deliverable_model)
        .where(deliverable_model.assignment_id == assignment_id)
        .order_by(deliverable_model.created_at.desc())
    )
    for deliverable in d_result.scalars().all():
        admin_note = _first_text(deliverable.admin_review_note)
        if admin_note:
            return {
                "source": "admin",
                "label": "管理员反馈",
                "content": admin_note,
                "createdAt": _iso_beijing(deliverable.admin_reviewed_at) or _iso_beijing(deliverable.created_at),
            }
        comments = _normalize_admin_comments(deliverable.admin_comments)
        latest_comment = next(
            (comment for comment in reversed(comments) if _first_text(comment.get("content"))),
            None,
        )
        if latest_comment:
            return {
                "source": "admin",
                "label": "管理员评论",
                "content": _first_text(latest_comment.get("content")),
                "createdAt": latest_comment.get("createdAt") or _iso_beijing(deliverable.created_at),
            }

    if order:
        order_data = order.order_data or {}
        user_feedback = _first_text(
            order_data.get("remarks"),
            order_data.get("special_requirements"),
            order_data.get("content_review"),
        )
        if user_feedback:
            return {
                "source": "user",
                "label": "用户反馈",
                "content": user_feedback,
                "createdAt": beijing_iso(order.created_at),
            }

    return None


def _stage_order_value(stage: dict) -> int | None:
    try:
        return int(stage.get("display_order"))
    except (TypeError, ValueError):
        return None


def _get_current_stage(assignment: ContractorAssignment) -> dict:
    schedule = assignment.schedule or []
    if not schedule:
        raise HTTPException(status_code=400, detail="当前派单未配置工作流排期")

    try:
        current_order = int(assignment.current_stage_order or "1")
    except ValueError:
        raise HTTPException(status_code=400, detail="当前派单工作流状态异常")

    current_stage = next((stage for stage in schedule if _stage_order_value(stage) == current_order), None)
    if not current_stage:
        raise HTTPException(status_code=400, detail="当前工作流环节不存在")
    return current_stage


def _ensure_current_stage_payload(
    assignment: ContractorAssignment,
    stage_config_id: str,
    stage_name: str,
    stage_order: int,
) -> dict:
    current_stage = _get_current_stage(assignment)
    current_order = _stage_order_value(current_stage)
    if (
        current_stage.get("stage_config_id") != stage_config_id
        or current_stage.get("name") != stage_name
        or current_order != stage_order
    ):
        raise HTTPException(status_code=400, detail="只能上传当前工作流环节的交付物")
    return current_stage


def _ensure_deliverable_matches_current_stage(
    assignment: ContractorAssignment,
    deliverable: ContractorDeliverable,
) -> dict:
    return _ensure_current_stage_payload(
        assignment,
        deliverable.stage_config_id,
        deliverable.stage_name,
        deliverable.stage_order,
    )


# ========== Schemas ==========

class ContractorRegisterRequest(BaseModel):
    invite_token: str
    phone: str
    sms_code: str
    username: Optional[str] = None
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
    showcase_cases: Optional[list] = None


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
        
        now = beijing_now()
        expires_at = ensure_beijing(invitation.expires_at)
        if expires_at and expires_at < now:
            return ApiResponse(code=400, message="邀请链接已过期", data={"valid": False, "reason": "expired"})
        
        return ApiResponse(code=200, message="邀请链接有效", data={
            "valid": True,
            "note": invitation.note,
            "expiresAt": beijing_iso(invitation.expires_at),
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试") from e


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
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试") from e


# ========== 我的派单 ==========

async def _get_my_staff_assignments(
    status_filter: str | None,
    current_user: AnyUser,
    db: AsyncSession,
) -> list[dict[str, Any]]:
    query = select(StaffAssignment).where(
        StaffAssignment.staff_id == current_user.id
    )

    if status_filter:
        staff_status = _staff_status_filter(status_filter)
        if staff_status is None:
            return []
        query = query.where(StaffAssignment.status == staff_status)

    query = query.order_by(StaffAssignment.assigned_at.desc())
    result = await db.execute(query)
    assignments = result.scalars().all()

    items = []
    for assignment in assignments:
        o_result = await db.execute(
            select(Order).where(Order.id == assignment.order_id)
        )
        order = o_result.scalar_one_or_none()
        order_info = _build_order_info(order, detail=False)
        feedback = await _latest_assignment_feedback(db, assignment.id, order, StaffDeliverable)

        item = serialize_staff_assignment_for_creator(
            assignment,
            order_info=order_info,
            deliverables=[],
        )
        item["feedback"] = feedback
        items.append(item)

    return items


@router.get("/assignments")
async def get_my_assignments(
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: AnyUser = Depends(require_creator),
    db: AsyncSession = Depends(get_db)
):
    """获取我的派单列表"""
    try:
        if _is_staff_creator(current_user):
            items = await _get_my_staff_assignments(status_filter, current_user, db)
            return ApiResponse(code=200, message="获取成功", data=items)

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
                    "projectName": order_data.get("project_name") or order_data.get("projectName"),
                    "content": order_data.get("content"),
                    "style": order_data.get("style"),
                    "city": order_data.get("city"),
                    "city_location": order_data.get("city_location"),
                    "media_size": order_data.get("media_size"),
                    "media_specs": order_data.get("media_specs"),
                    "time_number": order_data.get("time_number"),
                    "timing_number": order_data.get("timing_number"),
                    "technology": order_data.get("technology"),
                    "tech_delivery": order_data.get("tech_delivery"),
                    "online_time": order_data.get("online_time"),
                    "target_group": order_data.get("target_group"),
                    "audience_scene": order_data.get("audience_scene"),
                    "background": order_data.get("background"),
                    "resource_background": order_data.get("resource_background"),
                    "theme_concept": order_data.get("theme_concept"),
                    "art_direction": order_data.get("art_direction"),
                    "site_photos": _sign_file_items(order_data.get("site_photos") or order_data.get("scenePhotos")),
                    "productionAssets": _sign_file_items(build_production_assets(order_data, order.design_plan)),
                    "content_review": order_data.get("content_review"),
                    "special_requirements": order_data.get("special_requirements"),
                    "remarks": order_data.get("remarks"),
                    "createdAt": beijing_iso(order.created_at),
                }

            feedback = await _latest_assignment_feedback(db, a.id, order, ContractorDeliverable)
            
            items.append({
                "id": a.id,
                "creatorType": "contractor",
                "creatorId": a.contractor_id,
                "orderId": a.order_id,
                "order": order_info,
                "feedback": feedback,
                "status": a.status.value,
                "rejectReason": a.reject_reason,
                "schedule": a.schedule,
                "currentStageOrder": a.current_stage_order,
                "canAccept": a.status == AssignmentStatus.PENDING,
                "canReject": a.status == AssignmentStatus.PENDING,
                "canSubmitDeliverable": a.status == AssignmentStatus.IN_PROGRESS,
                "assignedAt": beijing_iso(a.assigned_at),
                "respondedAt": beijing_iso(a.responded_at),
            })
        
        return ApiResponse(code=200, message="获取成功", data=items)
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试") from e


async def _get_staff_assignment_detail(
    assignment_id: str,
    current_user: AnyUser,
    db: AsyncSession,
) -> dict[str, Any]:
    result = await db.execute(
        select(StaffAssignment).where(
            StaffAssignment.id == assignment_id,
            StaffAssignment.staff_id == current_user.id,
        )
    )
    assignment = result.scalar_one_or_none()

    if not assignment:
        raise HTTPException(status_code=404, detail="派单不存在")

    o_result = await db.execute(
        select(Order).where(Order.id == assignment.order_id)
    )
    order = o_result.scalar_one_or_none()
    order_info = _build_order_info(order, detail=True)

    d_result = await db.execute(
        select(StaffDeliverable)
        .where(StaffDeliverable.assignment_id == assignment_id)
        .order_by(StaffDeliverable.created_at.desc(), StaffDeliverable.stage_order.asc(), StaffDeliverable.version.desc())
    )
    deliverables = [
        _serialize_deliverable_for_creator(deliverable)
        for deliverable in d_result.scalars().all()
    ]

    return serialize_staff_assignment_for_creator(
        assignment,
        order_info=order_info,
        deliverables=deliverables,
    )


@router.get("/assignments/{assignment_id}")
async def get_assignment_detail(
    assignment_id: str,
    current_user: AnyUser = Depends(require_creator),
    db: AsyncSession = Depends(get_db)
):
    """获取派单详情（含订单信息和交付物列表）"""
    try:
        if _is_staff_creator(current_user):
            data = await _get_staff_assignment_detail(assignment_id, current_user, db)
            return ApiResponse(code=200, message="获取成功", data=data)

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
                "projectName": order_data.get("project_name") or order_data.get("projectName"),
                "brand_tone": order_data.get("brand_tone"),
                "content": order_data.get("content"),
                "style": order_data.get("style"),
                "city": order_data.get("city"),
                "city_location": order_data.get("city_location"),
                "media_size": order_data.get("media_size"),
                "media_specs": order_data.get("media_specs"),
                "time_number": order_data.get("time_number"),
                "timing_number": order_data.get("timing_number"),
                "technology": order_data.get("technology"),
                "tech_delivery": order_data.get("tech_delivery"),
                "online_time": order_data.get("online_time"),
                "target_group": order_data.get("target_group"),
                "audience_scene": order_data.get("audience_scene"),
                "background": order_data.get("background"),
                "resource_background": order_data.get("resource_background"),
                "media_positioning": order_data.get("media_positioning"),
                "viewing_path": order_data.get("viewing_path"),
                "art_direction": order_data.get("art_direction"),
                "theme_concept": order_data.get("theme_concept"),
                "content_review": order_data.get("content_review"),
                "special_requirements": order_data.get("special_requirements"),
                "remarks": order_data.get("remarks"),
                "prohibited_content": order_data.get("prohibited_content"),
                "site_photos": _sign_file_items(order_data.get("site_photos") or order_data.get("scenePhotos")),
                "productionAssets": _sign_file_items(build_production_assets(order_data, order.design_plan)),
                "createdAt": beijing_iso(order.created_at),
            }
            # 附加 AI 设计方案（管理员编写的方案，contractor 可见）
            if order.design_plan:
                order_info["designPlan"] = {
                    "content": order.design_plan.get("content", ""),
                    "files": _sign_file_items(order.design_plan.get("files", [])),
                    "status": order.design_plan.get("status", "draft"),
                }
        
        # 获取所有交付物
        d_result = await db.execute(
            select(ContractorDeliverable)
            .where(ContractorDeliverable.assignment_id == assignment_id)
            .order_by(ContractorDeliverable.created_at.desc(), ContractorDeliverable.stage_order.asc(), ContractorDeliverable.version.desc())
        )
        deliverables = d_result.scalars().all()
        
        deliverables_data = [
            _serialize_deliverable_for_creator(d)
            for d in deliverables
        ]
        
        return ApiResponse(code=200, message="获取成功", data={
            "id": assignment.id,
            "creatorType": "contractor",
            "creatorId": assignment.contractor_id,
            "orderId": assignment.order_id,
            "order": order_info,
            "status": assignment.status.value,
            "rejectReason": assignment.reject_reason,
            "schedule": assignment.schedule,
            "currentStageOrder": assignment.current_stage_order,
            "deliverables": deliverables_data,
            "canAccept": assignment.status == AssignmentStatus.PENDING,
            "canReject": assignment.status == AssignmentStatus.PENDING,
            "canSubmitDeliverable": assignment.status == AssignmentStatus.IN_PROGRESS,
            "assignedAt": beijing_iso(assignment.assigned_at),
            "respondedAt": beijing_iso(assignment.responded_at),
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试") from e


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
        
        now = beijing_now()
        old_status = assignment.status
        assignment.status = AssignmentStatus.IN_PROGRESS
        assignment.responded_at = now
        
        # 激活第一个环节
        schedule = assignment.schedule or []
        if schedule:
            schedule[0]["status"] = "active"
            assignment.schedule = schedule
            flag_modified(assignment, "schedule")
        
        await db.commit()
        await db.refresh(assignment)
        log_business_event(
            logger,
            "contractor_assignment_accepted",
            assignment_id=assignment.id,
            order_id=assignment.order_id,
            contractor_id=current_user.id,
            status_from=old_status,
            status_to=assignment.status,
            current_stage_order=assignment.current_stage_order,
        )
        
        # 通知管理员承包商已接单
        try:
            from app.models.notification import Notification, NotificationType
            from app.models.admin import Admin
            
            order_result = await db.execute(
                select(Order).where(Order.id == assignment.order_id)
            )
            order = order_result.scalar_one_or_none()
            order_number = order.order_number if order else "未知订单"
            contractor_name = current_user.real_name or current_user.username
            
            admins_result = await db.execute(select(Admin).where(Admin.is_active == True))
            admins = admins_result.scalars().all()
            
            for admin in admins:
                notif = Notification(
                    user_id=admin.id,
                    order_id=assignment.order_id,
                    type=NotificationType.CONTRACTOR_RESPONDED,
                    title=f"承包商已接单 - {order_number}",
                    content=f"承包商 {contractor_name} 已接受订单 {order_number} 的派单，即将开始制作。",
                )
                db.add(notif)
            await db.commit()
        except Exception as notify_err:
            log_business_event(
                logger,
                "contractor_assignment_accept_notification_failed",
                level="warning",
                assignment_id=assignment.id,
                order_id=assignment.order_id,
                contractor_id=current_user.id,
                error=str(notify_err),
            )
        
        return ApiResponse(code=200, message="接单成功", data={
            "id": assignment.id,
            "status": assignment.status.value,
            "respondedAt": beijing_iso(assignment.responded_at) or now.isoformat(),
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试") from e


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
        
        now = beijing_now()
        old_status = assignment.status
        assignment.status = AssignmentStatus.REJECTED
        assignment.reject_reason = data.reject_reason
        assignment.responded_at = now
        
        await db.commit()
        await db.refresh(assignment)
        log_business_event(
            logger,
            "contractor_assignment_rejected",
            assignment_id=assignment.id,
            order_id=assignment.order_id,
            contractor_id=current_user.id,
            status_from=old_status,
            status_to=assignment.status,
            has_reject_reason=bool(data.reject_reason),
        )
        
        # 通知管理员承包商已拒单
        try:
            from app.models.notification import Notification, NotificationType
            from app.models.admin import Admin
            
            order_result = await db.execute(
                select(Order).where(Order.id == assignment.order_id)
            )
            order = order_result.scalar_one_or_none()
            order_number = order.order_number if order else "未知订单"
            contractor_name = current_user.real_name or current_user.username
            reject_reason = f"原因：{data.reject_reason}" if data.reject_reason else ""
            
            admins_result = await db.execute(select(Admin).where(Admin.is_active == True))
            admins = admins_result.scalars().all()
            
            for admin in admins:
                notif = Notification(
                    user_id=admin.id,
                    order_id=assignment.order_id,
                    type=NotificationType.CONTRACTOR_RESPONDED,
                    title=f"承包商已拒单 - {order_number}",
                    content=f"承包商 {contractor_name} 拒绝了订单 {order_number} 的派单。{reject_reason}请重新分配。",
                )
                db.add(notif)
            await db.commit()
        except Exception as notify_err:
            log_business_event(
                logger,
                "contractor_assignment_reject_notification_failed",
                level="warning",
                assignment_id=assignment.id,
                order_id=assignment.order_id,
                contractor_id=current_user.id,
                error=str(notify_err),
            )
        
        return ApiResponse(code=200, message="已拒单", data={
            "id": assignment.id,
            "status": assignment.status.value,
            "rejectReason": assignment.reject_reason,
            "respondedAt": beijing_iso(assignment.responded_at) or now.isoformat(),
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试") from e


# ========== 交付物管理 ==========

async def _create_staff_deliverable(
    data: DeliverableCreate,
    current_user: AnyUser,
    db: AsyncSession,
) -> ApiResponse:
    a_result = await db.execute(
        select(StaffAssignment).where(
            StaffAssignment.id == data.assignment_id,
            StaffAssignment.staff_id == current_user.id,
        )
    )
    assignment = a_result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="派单不存在")

    if assignment.status != StaffAssignmentStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="当前派单状态不可上传交付物")
    _ensure_current_stage_payload(
        assignment,
        data.stage_config_id,
        data.stage_name,
        data.stage_order,
    )

    v_result = await db.execute(
        select(StaffDeliverable).where(
            StaffDeliverable.assignment_id == data.assignment_id,
            StaffDeliverable.stage_config_id == data.stage_config_id,
        ).order_by(StaffDeliverable.version.desc())
    )
    latest = v_result.scalars().first()
    version = (latest.version + 1) if latest else 1
    parent_id = latest.id if latest and latest.status == DeliverableStatus.ADMIN_REJECTED else None

    deliverable = StaffDeliverable(
        id=generate_id("staff_dlv"),
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
    log_business_event(
        logger,
        "staff_deliverable_draft_created",
        deliverable_id=deliverable.id,
        assignment_id=assignment.id,
        order_id=assignment.order_id,
        staff_id=current_user.id,
        stage_config_id=deliverable.stage_config_id,
        stage_name=deliverable.stage_name,
        stage_order=deliverable.stage_order,
        version=deliverable.version,
        parent_id=deliverable.parent_id,
        file_count=len(deliverable.files or []),
        self_review_count=len(deliverable.self_review_checks or {}),
        status=deliverable.status,
    )

    return ApiResponse(code=201, message="交付物已创建", data={
        "id": deliverable.id,
        "version": deliverable.version,
        "status": deliverable.status.value,
        "createdAt": _iso_beijing(deliverable.created_at) or beijing_now_iso(),
    })


async def _update_staff_deliverable(
    deliverable_id: str,
    data: DeliverableUpdate,
    current_user: AnyUser,
    db: AsyncSession,
) -> ApiResponse:
    result = await db.execute(
        select(StaffDeliverable).where(StaffDeliverable.id == deliverable_id)
    )
    deliverable = result.scalar_one_or_none()

    if not deliverable:
        raise HTTPException(status_code=404, detail="交付物不存在")

    a_result = await db.execute(
        select(StaffAssignment).where(
            StaffAssignment.id == deliverable.assignment_id,
            StaffAssignment.staff_id == current_user.id,
        )
    )
    assignment = a_result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=403, detail="无权操作")
    if assignment.status != StaffAssignmentStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="当前派单状态不可编辑交付物")
    _ensure_deliverable_matches_current_stage(assignment, deliverable)

    if deliverable.status != DeliverableStatus.DRAFT:
        raise HTTPException(status_code=400, detail="只有草稿状态的交付物可以编辑")

    updated_fields = []
    if data.description is not None:
        deliverable.description = data.description
        updated_fields.append("description")
    if data.files is not None:
        deliverable.files = data.files
        updated_fields.append("files")
    if data.self_review_checks is not None:
        deliverable.self_review_checks = data.self_review_checks
        updated_fields.append("self_review_checks")

    await db.commit()
    await db.refresh(deliverable)
    log_business_event(
        logger,
        "staff_deliverable_draft_updated",
        deliverable_id=deliverable.id,
        assignment_id=assignment.id,
        order_id=assignment.order_id,
        staff_id=current_user.id,
        stage_config_id=deliverable.stage_config_id,
        stage_name=deliverable.stage_name,
        stage_order=deliverable.stage_order,
        version=deliverable.version,
        updated_fields=updated_fields,
        file_count=len(deliverable.files or []),
        self_review_count=len(deliverable.self_review_checks or {}),
        status=deliverable.status,
    )

    return ApiResponse(code=200, message="更新成功", data={
        "id": deliverable.id,
        "status": deliverable.status.value,
        "updatedAt": _iso_beijing(deliverable.updated_at) or beijing_now_iso(),
    })


async def _submit_staff_deliverable(
    deliverable_id: str,
    current_user: AnyUser,
    db: AsyncSession,
) -> ApiResponse:
    result = await db.execute(
        select(StaffDeliverable).where(StaffDeliverable.id == deliverable_id)
    )
    deliverable = result.scalar_one_or_none()

    if not deliverable:
        raise HTTPException(status_code=404, detail="交付物不存在")

    a_result = await db.execute(
        select(StaffAssignment).where(
            StaffAssignment.id == deliverable.assignment_id,
            StaffAssignment.staff_id == current_user.id,
        )
    )
    assignment = a_result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=403, detail="无权操作")
    if assignment.status != StaffAssignmentStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="当前派单状态不可提交交付物")
    _ensure_deliverable_matches_current_stage(assignment, deliverable)

    if deliverable.status != DeliverableStatus.DRAFT:
        raise HTTPException(status_code=400, detail="只有草稿状态的交付物可以提交")

    checks = deliverable.self_review_checks or {}
    if not checks:
        raise HTTPException(status_code=400, detail="请先完成所有审核检查项")

    unchecked = [key for key, value in checks.items() if not value]
    if unchecked:
        raise HTTPException(
            status_code=400,
            detail=f"以下审核项未通过：{', '.join(unchecked)}",
        )

    if not deliverable.files:
        raise HTTPException(status_code=400, detail="请至少上传一个文件")

    old_status = deliverable.status
    deliverable.status = DeliverableStatus.SUBMITTED

    await db.commit()
    await db.refresh(deliverable)
    log_business_event(
        logger,
        "staff_deliverable_submitted",
        deliverable_id=deliverable.id,
        assignment_id=assignment.id,
        order_id=assignment.order_id,
        staff_id=current_user.id,
        stage_config_id=deliverable.stage_config_id,
        stage_name=deliverable.stage_name,
        stage_order=deliverable.stage_order,
        version=deliverable.version,
        file_count=len(deliverable.files or []),
        self_review_count=len(deliverable.self_review_checks or {}),
        status_from=old_status,
        status_to=deliverable.status,
    )

    try:
        from app.models.notification import Notification, NotificationType
        from app.models.admin import Admin

        order_result = await db.execute(
            select(Order).where(Order.id == assignment.order_id)
        )
        order = order_result.scalar_one_or_none()
        order_number = order.order_number if order else "未知订单"

        admins_result = await db.execute(
            select(Admin).where(Admin.is_active == True)
        )
        admins = admins_result.scalars().all()

        staff_name = getattr(current_user, "real_name", None) or getattr(current_user, "username", "内部制作者")
        stage_name = deliverable.stage_name or "未知环节"

        for admin in admins:
            notif = Notification(
                user_id=admin.id,
                order_id=assignment.order_id,
                type=NotificationType.DELIVERABLE_SUBMITTED,
                title=f"交付物待审核 - {order_number}",
                content=f"内部制作者 {staff_name} 提交了「{stage_name}」环节的交付物（V{deliverable.version}），请及时审核。",
            )
            db.add(notif)
        await db.commit()
    except Exception as notify_err:
        log_business_event(
            logger,
            "staff_deliverable_submit_notification_failed",
            level="warning",
            deliverable_id=deliverable.id,
            assignment_id=deliverable.assignment_id,
            staff_id=current_user.id,
            error=str(notify_err),
        )

    return ApiResponse(code=200, message="交付物已提交审核", data={
        "id": deliverable.id,
        "status": deliverable.status.value,
        "submittedAt": beijing_now_iso(),
    })


@router.post("/deliverables")
async def create_deliverable(
    data: DeliverableCreate,
    current_user: AnyUser = Depends(require_creator),
    db: AsyncSession = Depends(get_db)
):
    """创建交付物（草稿状态）"""
    try:
        if _is_staff_creator(current_user):
            return await _create_staff_deliverable(data, current_user, db)

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
        
        if assignment.status != AssignmentStatus.IN_PROGRESS:
            raise HTTPException(status_code=400, detail="当前派单状态不可上传交付物")
        _ensure_current_stage_payload(
            assignment,
            data.stage_config_id,
            data.stage_name,
            data.stage_order,
        )
        
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
        log_business_event(
            logger,
            "contractor_deliverable_draft_created",
            deliverable_id=deliverable.id,
            assignment_id=assignment.id,
            order_id=assignment.order_id,
            contractor_id=current_user.id,
            stage_config_id=deliverable.stage_config_id,
            stage_name=deliverable.stage_name,
            stage_order=deliverable.stage_order,
            version=deliverable.version,
            parent_id=deliverable.parent_id,
            file_count=len(deliverable.files or []),
            self_review_count=len(deliverable.self_review_checks or {}),
            status=deliverable.status,
        )
        
        return ApiResponse(code=201, message="交付物已创建", data={
            "id": deliverable.id,
            "version": deliverable.version,
            "status": deliverable.status.value,
            "createdAt": _iso_beijing(deliverable.created_at) or beijing_now_iso(),
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试") from e


@router.put("/deliverables/{deliverable_id}")
async def update_deliverable(
    deliverable_id: str,
    data: DeliverableUpdate,
    current_user: AnyUser = Depends(require_creator),
    db: AsyncSession = Depends(get_db)
):
    """更新交付物（仅草稿状态可编辑）"""
    try:
        if _is_staff_creator(current_user):
            return await _update_staff_deliverable(deliverable_id, data, current_user, db)

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
        assignment = a_result.scalar_one_or_none()
        if not assignment:
            raise HTTPException(status_code=403, detail="无权操作")
        if assignment.status != AssignmentStatus.IN_PROGRESS:
            raise HTTPException(status_code=400, detail="当前派单状态不可编辑交付物")
        _ensure_deliverable_matches_current_stage(assignment, deliverable)
        
        if deliverable.status != DeliverableStatus.DRAFT:
            raise HTTPException(status_code=400, detail="只有草稿状态的交付物可以编辑")
        
        updated_fields = []
        if data.description is not None:
            deliverable.description = data.description
            updated_fields.append("description")
        if data.files is not None:
            deliverable.files = data.files
            updated_fields.append("files")
        if data.self_review_checks is not None:
            deliverable.self_review_checks = data.self_review_checks
            updated_fields.append("self_review_checks")
        
        await db.commit()
        await db.refresh(deliverable)
        log_business_event(
            logger,
            "contractor_deliverable_draft_updated",
            deliverable_id=deliverable.id,
            assignment_id=assignment.id,
            order_id=assignment.order_id,
            contractor_id=current_user.id,
            stage_config_id=deliverable.stage_config_id,
            stage_name=deliverable.stage_name,
            stage_order=deliverable.stage_order,
            version=deliverable.version,
            updated_fields=updated_fields,
            file_count=len(deliverable.files or []),
            self_review_count=len(deliverable.self_review_checks or {}),
            status=deliverable.status,
        )
        
        return ApiResponse(code=200, message="更新成功", data={
            "id": deliverable.id,
            "status": deliverable.status.value,
            "updatedAt": _iso_beijing(deliverable.updated_at) or beijing_now_iso(),
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试") from e


@router.put("/deliverables/{deliverable_id}/submit")
async def submit_deliverable(
    deliverable_id: str,
    current_user: AnyUser = Depends(require_creator),
    db: AsyncSession = Depends(get_db)
):
    """提交交付物审核（需完成所有自审核检查项）"""
    try:
        if _is_staff_creator(current_user):
            return await _submit_staff_deliverable(deliverable_id, current_user, db)

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
        assignment = a_result.scalar_one_or_none()
        if not assignment:
            raise HTTPException(status_code=403, detail="无权操作")
        if assignment.status != AssignmentStatus.IN_PROGRESS:
            raise HTTPException(status_code=400, detail="当前派单状态不可提交交付物")
        _ensure_deliverable_matches_current_stage(assignment, deliverable)
        
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
        
        old_status = deliverable.status
        deliverable.status = DeliverableStatus.SUBMITTED
        
        await db.commit()
        await db.refresh(deliverable)
        log_business_event(
            logger,
            "contractor_deliverable_submitted",
            deliverable_id=deliverable.id,
            assignment_id=assignment.id,
            order_id=assignment.order_id,
            contractor_id=current_user.id,
            stage_config_id=deliverable.stage_config_id,
            stage_name=deliverable.stage_name,
            stage_order=deliverable.stage_order,
            version=deliverable.version,
            file_count=len(deliverable.files or []),
            self_review_count=len(deliverable.self_review_checks or {}),
            status_from=old_status,
            status_to=deliverable.status,
        )
        
        # 通知管理员有新交付物待审核
        try:
            from app.models.notification import Notification, NotificationType
            from app.models.admin import Admin
            
            # 获取订单信息
            assignment_result = await db.execute(
                select(ContractorAssignment).where(ContractorAssignment.id == deliverable.assignment_id)
            )
            assignment = assignment_result.scalar_one_or_none()
            
            order_number = "未知订单"
            if assignment:
                from app.models.order import Order
                order_result = await db.execute(
                    select(Order).where(Order.id == assignment.order_id)
                )
                order = order_result.scalar_one_or_none()
                if order:
                    order_number = order.order_number
            
            # 给所有活跃管理员发站内信
            admins_result = await db.execute(
                select(Admin).where(Admin.is_active == True)
            )
            admins = admins_result.scalars().all()
            
            contractor_name = current_user.username if hasattr(current_user, 'username') else '承包商'
            stage_name = deliverable.stage_name or '未知环节'
            
            for admin in admins:
                notif = Notification(
                    user_id=admin.id,
                    order_id=assignment.order_id if assignment else None,
                    type=NotificationType.DELIVERABLE_SUBMITTED,
                    title=f"交付物待审核 - {order_number}",
                    content=f"承包商 {contractor_name} 提交了「{stage_name}」环节的交付物（V{deliverable.version}），请及时审核。",
                )
                db.add(notif)
            await db.commit()
        except Exception as notify_err:
            log_business_event(
                logger,
                "contractor_deliverable_submit_notification_failed",
                level="warning",
                deliverable_id=deliverable.id,
                assignment_id=deliverable.assignment_id,
                contractor_id=current_user.id,
                error=str(notify_err),
            )
        
        return ApiResponse(code=200, message="交付物已提交审核", data={
            "id": deliverable.id,
            "status": deliverable.status.value,
            "submittedAt": beijing_now_iso(),
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试") from e


# ========== 个人信息 ==========

@router.get("/profile")
async def get_contractor_profile(
    current_user: AnyUser = Depends(require_creator),
    db: AsyncSession = Depends(get_db)
):
    """获取制作者个人信息"""
    return ApiResponse(code=200, message="获取成功", data=_serialize_creator_profile(current_user))


@router.put("/profile")
async def update_contractor_profile(
    data: ProfileUpdate,
    current_user: AnyUser = Depends(require_creator),
    db: AsyncSession = Depends(get_db)
):
    """更新制作者个人信息"""
    try:
        _apply_creator_profile_update(current_user, data)
        
        await db.commit()
        await db.refresh(current_user)
        
        return ApiResponse(code=200, message="更新成功", data={
            "id": current_user.id,
            "username": current_user.username,
            "email": getattr(current_user, "email", None),
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试") from e
