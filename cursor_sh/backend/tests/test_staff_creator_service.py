from app.models.staff_assignment import StaffAssignmentStatus
from app.models.staff_deliverable import StaffDeliverable
from app.models.contractor_deliverable import DeliverableStatus
from app.services.staff_creator_service import (
    build_staff_assignment,
    default_staff_schedule,
    plan_staff_assignment_backfill,
    plan_staff_assignment_sync,
    serialize_staff_assignment_for_admin,
    serialize_staff_assignment_for_creator,
    serialize_staff_deliverable_for_admin,
    serialize_staff_deliverable_for_creator,
    serialize_staff_deliverable_for_user,
)


def test_default_staff_schedule_has_active_single_stage():
    assert default_staff_schedule() == [
        {
            "stage_config_id": "staff_default_delivery",
            "name": "制作交付",
            "display_order": 1,
            "days": 1,
            "deadline": None,
            "status": "active",
        }
    ]


def test_build_staff_assignment_starts_internal_creator_in_progress():
    assignment = build_staff_assignment(
        order_id="order-1",
        staff_id="staff-1",
        assigned_by="admin-1",
        schedule=[{"name": "制作交付", "display_order": 1, "days": 1}],
    )

    assert assignment.order_id == "order-1"
    assert assignment.staff_id == "staff-1"
    assert assignment.assigned_by == "admin-1"
    assert assignment.status == StaffAssignmentStatus.IN_PROGRESS
    assert assignment.responded_at == assignment.assigned_at


def test_plan_staff_assignment_sync_only_changes_delta():
    plan = plan_staff_assignment_sync(
        old_staff_ids={"staff-1", "staff-2"},
        new_staff_ids={"staff-2", "staff-3"},
    )

    assert plan.newly_assigned == {"staff-3"}
    assert plan.removed == {"staff-1"}
    assert plan.unchanged == {"staff-2"}


def test_plan_staff_assignment_backfill_skips_existing_non_cancelled_pairs():
    missing = plan_staff_assignment_backfill(
        assignee_pairs={
            ("order-1", "staff-1"),
            ("order-1", "staff-2"),
            ("order-2", "staff-3"),
        },
        existing_pairs={
            ("order-1", "staff-1"),
        },
    )

    assert missing == {
        ("order-1", "staff-2"),
        ("order-2", "staff-3"),
    }


def test_serialize_staff_assignment_creator_dto_has_no_accept_or_reject_actions():
    assignment = build_staff_assignment(
        order_id="order-1",
        staff_id="staff-1",
        assigned_by="admin-1",
    )

    dto = serialize_staff_assignment_for_creator(
        assignment,
        order_info={"id": "order-1", "orderNumber": "ORD-1"},
        deliverables=[],
        production_assets=[],
    )

    assert dto["creatorType"] == "staff"
    assert dto["canAccept"] is False
    assert dto["canReject"] is False
    assert dto["canSubmitDeliverable"] is True
    assert dto["status"] == "in_progress"


def test_serialize_staff_deliverable_for_creator_matches_frontend_payload_shape():
    deliverable = StaffDeliverable(
        id="staff-dlv-1",
        assignment_id="staff-assign-1",
        stage_config_id="staff_default_delivery",
        stage_name="制作交付",
        stage_order=1,
        version=2,
        files=[{"name": "demo.pdf", "url": "/uploads/demo.pdf"}],
        description="第二版",
        self_review_checks={"品质审核": True},
        status=DeliverableStatus.SUBMITTED,
        admin_review_note="请调整字距",
        admin_comments=[{"content": "整体方向正确"}],
    )

    dto = serialize_staff_deliverable_for_creator(deliverable)

    assert dto["id"] == "staff-dlv-1"
    assert dto["stageConfigId"] == "staff_default_delivery"
    assert dto["stageName"] == "制作交付"
    assert dto["stageOrder"] == 1
    assert dto["version"] == 2
    assert dto["files"] == [{"name": "demo.pdf", "url": "/uploads/demo.pdf"}]
    assert dto["description"] == "第二版"
    assert dto["selfReviewChecks"] == {"品质审核": True}
    assert dto["status"] == "submitted"
    assert dto["adminReviewNote"] == "请调整字距"
    assert dto["adminComments"] == [{"content": "整体方向正确"}]


def test_serialize_staff_assignment_for_admin_uses_creator_fields_and_legacy_names():
    assignment = build_staff_assignment(
        order_id="order-1",
        staff_id="staff-1",
        assigned_by="admin-1",
    )

    dto = serialize_staff_assignment_for_admin(
        assignment,
        staff_name="内部制作 A",
        order_number="ORD-1",
        pending_review_count=2,
        total_deliverables=3,
    )

    assert dto["creatorType"] == "staff"
    assert dto["creatorId"] == "staff-1"
    assert dto["creatorName"] == "内部制作 A"
    assert dto["contractorId"] == "staff-1"
    assert dto["contractorName"] == "内部制作 A"
    assert dto["orderNumber"] == "ORD-1"
    assert dto["pendingReviewCount"] == 2
    assert dto["totalDeliverables"] == 3
    assert dto["status"] == "in_progress"
    assert dto["canAccept"] is False
    assert dto["canReject"] is False


def test_serialize_staff_deliverable_for_admin_matches_admin_payload_shape():
    deliverable = StaffDeliverable(
        id="staff-dlv-1",
        assignment_id="staff-assign-1",
        stage_config_id="staff_default_delivery",
        stage_name="制作交付",
        stage_order=1,
        version=1,
        files=[{"name": "final.png"}],
        description="终稿",
        status=DeliverableStatus.ADMIN_APPROVED,
        is_published_to_user=True,
        published_note="已推送",
        published_by="admin-1",
        admin_comments=[{"content": "不错"}],
    )

    dto = serialize_staff_deliverable_for_admin(deliverable)

    assert dto["creatorType"] == "staff"
    assert dto["assignmentId"] == "staff-assign-1"
    assert dto["stageConfigId"] == "staff_default_delivery"
    assert dto["files"] == [{"name": "final.png"}]
    assert dto["status"] == "admin_approved"
    assert dto["isPublishedToUser"] is True
    assert dto["publishedNote"] == "已推送"
    assert dto["publishedBy"] == "admin-1"
    assert dto["adminComments"] == [{"content": "不错"}]


def test_serialize_staff_deliverable_for_user_marks_internal_creator():
    deliverable = StaffDeliverable(
        id="staff-dlv-1",
        assignment_id="staff-assign-1",
        stage_config_id="staff_default_delivery",
        stage_name="制作交付",
        stage_order=1,
        version=1,
        files=[{"name": "final.png"}],
        description="终稿",
        status=DeliverableStatus.ADMIN_APPROVED,
        is_published_to_user=True,
        published_note="已推送",
    )

    dto = serialize_staff_deliverable_for_user(deliverable)

    assert dto["id"] == "staff-dlv-1"
    assert dto["creatorType"] == "staff"
    assert dto["stageName"] == "制作交付"
    assert dto["files"] == [{"name": "final.png"}]
    assert dto["publishedNote"] == "已推送"
