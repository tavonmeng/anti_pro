"""内部制作者任务服务。"""

from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.staff_assignment import StaffAssignment, StaffAssignmentStatus
from app.models.staff_deliverable import StaffDeliverable
from app.utils.timezone import beijing_now, beijing_iso
from app.utils.validators import generate_id


@dataclass(frozen=True)
class StaffAssignmentSyncPlan:
    newly_assigned: set[str]
    removed: set[str]
    unchanged: set[str]


def default_staff_schedule() -> list[dict[str, Any]]:
    """内部负责人默认单环节排期。"""
    return [
        {
            "stage_config_id": "staff_default_delivery",
            "name": "制作交付",
            "display_order": 1,
            "days": 1,
            "deadline": None,
            "status": "active",
        }
    ]


def plan_staff_assignment_sync(
    old_staff_ids: set[str],
    new_staff_ids: set[str],
) -> StaffAssignmentSyncPlan:
    return StaffAssignmentSyncPlan(
        newly_assigned=new_staff_ids - old_staff_ids,
        removed=old_staff_ids - new_staff_ids,
        unchanged=old_staff_ids & new_staff_ids,
    )


def plan_staff_assignment_backfill(
    assignee_pairs: set[tuple[str, str]],
    existing_pairs: set[tuple[str, str]],
) -> set[tuple[str, str]]:
    """计算历史负责人分配中还缺少的内部制作者任务。"""
    return assignee_pairs - existing_pairs


def build_staff_assignment(
    order_id: str,
    staff_id: str,
    assigned_by: str,
    schedule: Optional[list[dict[str, Any]]] = None,
) -> StaffAssignment:
    """创建内部负责人制作任务对象，不提交数据库。"""
    now = beijing_now()
    return StaffAssignment(
        id=generate_id("staff_assign"),
        order_id=order_id,
        staff_id=staff_id,
        assigned_by=assigned_by,
        status=StaffAssignmentStatus.IN_PROGRESS,
        schedule=schedule or default_staff_schedule(),
        current_stage_order="1",
        assigned_at=now,
        responded_at=now,
    )


async def sync_staff_assignments_for_order(
    db: AsyncSession,
    order_id: str,
    old_staff_ids: set[str],
    new_staff_ids: set[str],
    assigned_by: str,
) -> StaffAssignmentSyncPlan:
    """同步内部负责人制作任务，保留未变更任务和交付历史。"""
    plan = plan_staff_assignment_sync(old_staff_ids, new_staff_ids)

    if plan.newly_assigned:
        existing_result = await db.execute(
            select(StaffAssignment).where(
                StaffAssignment.order_id == order_id,
                StaffAssignment.staff_id.in_(plan.newly_assigned),
                StaffAssignment.status == StaffAssignmentStatus.IN_PROGRESS,
            )
        )
        existing_active = {assignment.staff_id for assignment in existing_result.scalars().all()}
        for staff_id in sorted(plan.newly_assigned - existing_active):
            db.add(build_staff_assignment(order_id=order_id, staff_id=staff_id, assigned_by=assigned_by))

    if plan.removed:
        removed_result = await db.execute(
            select(StaffAssignment).where(
                StaffAssignment.order_id == order_id,
                StaffAssignment.staff_id.in_(plan.removed),
                StaffAssignment.status == StaffAssignmentStatus.IN_PROGRESS,
            )
        )
        now = beijing_now()
        for assignment in removed_result.scalars().all():
            assignment.status = StaffAssignmentStatus.CANCELLED
            assignment.completed_at = now
            assignment.updated_at = now
            if assignment.schedule:
                for stage in assignment.schedule:
                    if stage.get("status") == "active":
                        stage["status"] = "cancelled"
                flag_modified(assignment, "schedule")

    return plan


def serialize_staff_assignment_for_creator(
    assignment: StaffAssignment,
    order_info: dict[str, Any] | None = None,
    deliverables: Optional[list[dict[str, Any]]] = None,
    production_assets: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """将内部负责人任务转为制作端统一 DTO。"""
    order = dict(order_info or {})
    order["productionAssets"] = production_assets or order.get("productionAssets") or []
    return {
        "id": assignment.id,
        "creatorType": "staff",
        "creatorId": assignment.staff_id,
        "orderId": assignment.order_id,
        "order": order,
        "status": assignment.status.value if hasattr(assignment.status, "value") else assignment.status,
        "schedule": assignment.schedule,
        "currentStageOrder": assignment.current_stage_order,
        "deliverables": deliverables or [],
        "canAccept": False,
        "canReject": False,
        "canSubmitDeliverable": assignment.status == StaffAssignmentStatus.IN_PROGRESS,
        "assignedAt": beijing_iso(assignment.assigned_at),
        "respondedAt": beijing_iso(assignment.responded_at),
        "completedAt": beijing_iso(assignment.completed_at),
    }


def serialize_staff_deliverable_for_creator(deliverable: StaffDeliverable) -> dict[str, Any]:
    """将内部负责人交付物转为制作端页面使用的 DTO。"""
    return {
        "id": deliverable.id,
        "stageConfigId": deliverable.stage_config_id,
        "stageName": deliverable.stage_name,
        "stageOrder": deliverable.stage_order,
        "version": deliverable.version,
        "parentId": deliverable.parent_id,
        "files": deliverable.files or [],
        "description": deliverable.description,
        "selfReviewChecks": deliverable.self_review_checks or {},
        "status": deliverable.status.value if hasattr(deliverable.status, "value") else deliverable.status,
        "adminReviewNote": deliverable.admin_review_note,
        "adminReviewedAt": beijing_iso(deliverable.admin_reviewed_at),
        "adminComments": deliverable.admin_comments or [],
        "createdAt": beijing_iso(deliverable.created_at),
    }


def serialize_staff_assignment_for_admin(
    assignment: StaffAssignment,
    *,
    staff_name: str | None = None,
    order_number: str | None = None,
    pending_review_count: int = 0,
    total_deliverables: int = 0,
) -> dict[str, Any]:
    """将内部负责人任务转为管理员端可复用的派单 DTO。"""
    creator_name = staff_name or assignment.staff_id
    return {
        "id": assignment.id,
        "creatorType": "staff",
        "creatorId": assignment.staff_id,
        "creatorName": creator_name,
        "orderId": assignment.order_id,
        "orderNumber": order_number,
        "contractorId": assignment.staff_id,
        "contractorName": creator_name,
        "status": assignment.status.value if hasattr(assignment.status, "value") else assignment.status,
        "rejectReason": None,
        "schedule": assignment.schedule,
        "currentStageOrder": assignment.current_stage_order,
        "pendingReviewCount": pending_review_count,
        "totalDeliverables": total_deliverables,
        "canAccept": False,
        "canReject": False,
        "assignedAt": beijing_iso(assignment.assigned_at),
        "respondedAt": beijing_iso(assignment.responded_at),
        "completedAt": beijing_iso(assignment.completed_at),
    }


def serialize_staff_deliverable_for_admin(deliverable: StaffDeliverable) -> dict[str, Any]:
    """将内部负责人交付物转为管理员审核页面使用的 DTO。"""
    return {
        **serialize_staff_deliverable_for_creator(deliverable),
        "creatorType": "staff",
        "assignmentId": deliverable.assignment_id,
        "adminReviewedBy": deliverable.admin_reviewed_by,
        "isPublishedToUser": bool(deliverable.is_published_to_user),
        "publishedNote": deliverable.published_note,
        "publishedBy": deliverable.published_by,
        "publishedAt": beijing_iso(deliverable.published_at),
    }


def serialize_staff_deliverable_for_user(deliverable: StaffDeliverable) -> dict[str, Any]:
    """将已发布的内部负责人交付物转为用户订单详情 DTO。"""
    return {
        "id": deliverable.id,
        "creatorType": "staff",
        "stageName": deliverable.stage_name,
        "stageOrder": deliverable.stage_order,
        "version": deliverable.version,
        "files": deliverable.files or [],
        "description": deliverable.description,
        "publishedNote": deliverable.published_note,
        "publishedAt": beijing_iso(deliverable.published_at),
        "createdAt": beijing_iso(deliverable.created_at),
    }
