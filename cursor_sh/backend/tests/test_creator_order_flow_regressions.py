from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api import contractor_admin, upload
from app.api.contractor_admin import AssignOrderRequest, PublishDeliverableRequest
from app.models.admin import Admin
from app.models.contractor import Contractor
from app.models.contractor_assignment import AssignmentStatus, ContractorAssignment
from app.models.contractor_deliverable import DeliverableStatus
from app.models.feedback import Feedback, FeedbackType
from app.models.order import Order, OrderStatus, OrderType
from app.models.notification import Notification, NotificationType
from app.models.staff_assignment import StaffAssignment, StaffAssignmentStatus
from app.models.staff_deliverable import StaffDeliverable
from app.models.staff_member import StaffMember
from app.models.user import User, UserRole
from app.schemas.feedback import FeedbackCreate
from app.services import order_service
from app.services.email_service import EmailService
from app.services.order_service import OrderService, OrderStateMachine


class _ScalarCollection:
    def __init__(self, values):
        self._values = list(values)

    def all(self):
        return self._values

    def first(self):
        return self._values[0] if self._values else None


class _Result:
    def __init__(self, *, scalar=None, scalars=None, rows=None):
        self._scalar = scalar
        self._scalars = list(scalars or [])
        self._rows = list(rows or [])

    def scalar_one_or_none(self):
        return self._scalar

    def scalar_one(self):
        return self._scalar

    def scalar(self):
        return self._scalar

    def scalars(self):
        return _ScalarCollection(self._scalars)

    def all(self):
        return self._rows


class _FakeDb:
    def __init__(self, results):
        self._results = list(results)
        self.added = []
        self.commit_count = 0

    async def execute(self, _query):
        assert self._results, "unexpected database query"
        return self._results.pop(0)

    def add(self, value):
        self.added.append(value)

    async def commit(self):
        self.commit_count += 1

    async def refresh(self, _value):
        return None

    async def rollback(self):
        return None


class _AdminUser:
    id = "admin-1"
    username = "admin"
    role = UserRole.ADMIN


class _CustomerUser:
    id = "user-1"
    username = "customer"
    role = UserRole.USER


class _StaffUser:
    id = "staff-1"
    username = "staff"
    role = UserRole.STAFF


@pytest.mark.asyncio
async def test_admin_assignment_list_handles_staff_only_submitted_deliverable():
    assignment = StaffAssignment(
        id="staff-assign-1",
        order_id="order-1",
        staff_id="staff-1",
        assigned_by="admin-1",
        status=StaffAssignmentStatus.IN_PROGRESS,
    )
    staff = StaffMember(
        id="staff-1",
        username="staff",
        password_hash="hash",
        real_name="内部负责人",
    )
    order = Order(
        id="order-1",
        order_number="ORD-1",
        order_type=OrderType.AI_3D_CUSTOM,
        status=OrderStatus.IN_PRODUCTION,
        user_id="user-1",
        order_data={},
    )
    deliverable = StaffDeliverable(
        id="staff-dlv-1",
        assignment_id=assignment.id,
        stage_config_id="staff_default_delivery",
        stage_name="制作交付",
        stage_order=1,
        version=1,
        status=DeliverableStatus.SUBMITTED,
    )
    db = _FakeDb([
        _Result(scalars=[]),
        _Result(scalars=[assignment]),
        _Result(scalar=staff),
        _Result(scalar=order),
        _Result(scalars=[deliverable]),
    ])

    response = await contractor_admin.get_all_assignments(
        order_id=order.id,
        status=None,
        page=1,
        pageSize=20,
        current_user=_AdminUser(),
        db=db,
    )

    assert response.data["total"] == 1
    assert response.data["data"][0]["creatorType"] == "staff"
    assert response.data["data"][0]["pendingReviewCount"] == 1


@pytest.mark.asyncio
async def test_customer_feedback_resolves_published_staff_deliverable():
    db = _FakeDb([
        _Result(scalar=None),
        _Result(scalar="staff-dlv-1"),
    ])

    creator_type = await order_service._resolve_published_feedback_deliverable(
        db,
        "order-1",
        "staff-dlv-1",
    )

    assert creator_type == "staff"


@pytest.mark.asyncio
async def test_staff_deliverable_feedback_is_saved_and_only_admins_are_notified(monkeypatch):
    order = Order(
        id="order-1",
        order_number="ORD-1",
        order_type=OrderType.AI_3D_CUSTOM,
        status=OrderStatus.IN_PRODUCTION,
        user_id="user-1",
        order_data={},
        revision_count=0,
    )
    admins = [Admin(id="admin-1", username="admin", password_hash="hash")]
    db = _FakeDb([
        _Result(scalar=order),
        _Result(scalar=None),
        _Result(scalar="staff-dlv-1"),
        _Result(scalars=admins),
    ])
    notification_calls = []

    async def fake_notify(**kwargs):
        notification_calls.append(kwargs)

    monkeypatch.setattr(
        order_service.NotificationService,
        "create_notification_for_multiple_users",
        fake_notify,
    )
    monkeypatch.setattr(order_service, "log_business_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(order_service, "generate_id", lambda _prefix: "feedback-1")

    result = await OrderService.submit_feedback(
        db,
        order.id,
        FeedbackCreate(
            type=FeedbackType.REVISION,
            content="请调整节奏",
            deliverableId="staff-dlv-1",
        ),
        _CustomerUser(),
    )

    saved_feedback = next(item for item in db.added if isinstance(item, Feedback))
    assert saved_feedback.deliverable_id is None
    assert saved_feedback.staff_deliverable_id == "staff-dlv-1"
    assert result["deliverableId"] == "staff-dlv-1"
    assert len(notification_calls) == 1
    assert notification_calls[0]["user_ids"] == ["admin-1"]


def test_customer_feedback_visibility_excludes_all_creators():
    assert order_service._can_view_customer_feedback(_CustomerUser()) is True
    assert order_service._can_view_customer_feedback(_AdminUser()) is True
    assert order_service._can_view_customer_feedback(_StaffUser()) is False
    contractor_user = SimpleNamespace(role=UserRole.CONTRACTOR)
    assert order_service._can_view_customer_feedback(contractor_user) is False


@pytest.mark.asyncio
async def test_contractor_assignment_rejects_active_staff_order():
    order = Order(
        id="order-1",
        order_number="ORD-1",
        order_type=OrderType.AI_3D_CUSTOM,
        status=OrderStatus.IN_PRODUCTION,
        user_id="user-1",
        order_data={},
    )
    contractor = Contractor(
        id="contractor-1",
        username="contractor",
        password_hash="hash",
        is_active=True,
    )
    db = _FakeDb([
        _Result(scalar=order),
        _Result(scalar=contractor),
        _Result(scalar=None),
        _Result(scalar="staff-assign-1"),
    ])

    with pytest.raises(HTTPException) as exc:
        await contractor_admin.assign_order_to_contractor(
            data=AssignOrderRequest(order_id=order.id, contractor_id=contractor.id),
            current_user=_AdminUser(),
            db=db,
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "该订单已分配给内部负责人，不能再派给承包商"


@pytest.mark.asyncio
async def test_staff_assignment_rejects_active_contractor_order():
    order = Order(
        id="order-1",
        order_number="ORD-1",
        order_type=OrderType.AI_3D_CUSTOM,
        status=OrderStatus.IN_PRODUCTION,
        user_id="user-1",
        order_data={},
        design_plan={"status": "completed"},
    )
    staff = StaffMember(
        id="staff-1",
        username="staff",
        password_hash="hash",
    )
    db = _FakeDb([
        _Result(scalar=order),
        _Result(scalars=[staff]),
        _Result(scalar="assign-1"),
    ])

    with pytest.raises(HTTPException) as exc:
        await OrderService.assign_order(
            db=db,
            order_id=order.id,
            assignee_ids=[staff.id],
            assignee_names=[staff.username],
            current_user=_AdminUser(),
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "该订单已派给承包商，不能再分配内部负责人"


def test_feedback_model_has_separate_staff_deliverable_foreign_key():
    column = Feedback.__table__.columns["staff_deliverable_id"]
    target = next(iter(column.foreign_keys)).target_fullname

    assert target == "staff_deliverables.id"
    assert column.nullable is True


def test_creator_review_status_uses_latest_current_stage_version():
    rows = [
        (
            "order-pending",
            "1",
            SimpleNamespace(
                assignment_id="staff-assign-1",
                stage_order=1,
                version=1,
                status=DeliverableStatus.SUBMITTED,
                parent_id=None,
            ),
        ),
        (
            "order-resolved",
            "1",
            SimpleNamespace(
                assignment_id="contractor-assign-1",
                stage_order=1,
                version=1,
                status=DeliverableStatus.ADMIN_REJECTED,
                parent_id=None,
            ),
        ),
        (
            "order-resolved",
            "1",
            SimpleNamespace(
                assignment_id="contractor-assign-1",
                stage_order=1,
                version=2,
                status=DeliverableStatus.ADMIN_APPROVED,
                parent_id="deliverable-v1",
            ),
        ),
        (
            "order-revising",
            "2",
            SimpleNamespace(
                assignment_id="staff-assign-2",
                stage_order=2,
                version=2,
                status=DeliverableStatus.DRAFT,
                parent_id="rejected-v1",
            ),
        ),
        (
            "order-other-stage",
            "2",
            SimpleNamespace(
                assignment_id="staff-assign-3",
                stage_order=1,
                version=1,
                status=DeliverableStatus.SUBMITTED,
                parent_id=None,
            ),
        ),
    ]

    statuses = order_service._derive_creator_review_statuses(rows)

    assert statuses == {
        "order-pending": "pending_review",
        "order-revising": "review_rejected",
    }


def test_creator_generic_upload_supports_200mb_and_multiple_format_categories():
    assert upload.UPLOAD_MAX_SIZE == 200 * 1024 * 1024
    assert upload.UPLOAD_MAX_SIZE_MESSAGE == "文件大小不能超过200MB"
    assert {'.png', '.mp4', '.pdf', '.psd', '.fbx', '.zip'}.issubset(
        upload.GENERIC_UPLOAD_ALLOWED_EXTENSIONS
    )


def test_order_state_machine_only_allows_the_next_stage_and_no_rollback():
    ordered = [
        OrderStatus.DRAFT,
        OrderStatus.PENDING_CONTRACT,
        OrderStatus.IN_PRODUCTION,
        OrderStatus.PREVIEW_READY,
        OrderStatus.FINAL_PREVIEW,
        OrderStatus.COMPLETED,
    ]

    for current, expected_next in zip(ordered, ordered[1:]):
        assert OrderStateMachine.next_status(current) == expected_next
        assert OrderStateMachine.can_transition(current, expected_next) is True

    assert OrderStateMachine.can_transition(OrderStatus.IN_PRODUCTION, OrderStatus.FINAL_PREVIEW) is False
    assert OrderStateMachine.can_transition(OrderStatus.PREVIEW_READY, OrderStatus.IN_PRODUCTION) is False
    assert OrderStateMachine.can_transition(OrderStatus.FINAL_PREVIEW, OrderStatus.PREVIEW_READY) is False
    assert OrderStateMachine.can_transition(OrderStatus.COMPLETED, OrderStatus.CANCELLED) is False


def test_legacy_order_states_only_normalize_to_their_current_stage():
    assert OrderStateMachine.next_status(OrderStatus.PENDING_ASSIGN) == OrderStatus.PENDING_CONTRACT
    assert OrderStateMachine.next_status(OrderStatus.PENDING_REVIEW) == OrderStatus.PREVIEW_READY
    assert OrderStateMachine.next_status(
        OrderStatus.REVISION_NEEDED,
        has_final_preview=True,
    ) == OrderStatus.FINAL_PREVIEW


@pytest.mark.asyncio
async def test_staff_cannot_manually_change_order_main_status():
    order = Order(
        id="order-1",
        order_number="ORD-1",
        order_type=OrderType.AI_3D_CUSTOM,
        status=OrderStatus.IN_PRODUCTION,
        user_id="user-1",
        order_data={},
    )
    db = _FakeDb([_Result(scalar=order)])

    with pytest.raises(HTTPException) as exc:
        await OrderService.update_order_status(
            db,
            order.id,
            OrderStatus.PREVIEW_READY,
            _StaffUser(),
        )

    assert exc.value.status_code == 403
    assert order.status == OrderStatus.IN_PRODUCTION


@pytest.mark.asyncio
async def test_customer_revision_keeps_main_stage_and_increments_revision(monkeypatch):
    order = Order(
        id="order-1",
        order_number="ORD-1",
        order_type=OrderType.AI_3D_CUSTOM,
        status=OrderStatus.PREVIEW_READY,
        user_id="user-1",
        order_data={},
        revision_count=0,
    )
    admins = [Admin(id="admin-1", username="admin", password_hash="hash")]
    db = _FakeDb([
        _Result(scalar=order),
        _Result(scalars=admins),
    ])

    async def fake_notify(**_kwargs):
        return None

    monkeypatch.setattr(
        order_service.NotificationService,
        "create_notification_for_multiple_users",
        fake_notify,
    )
    monkeypatch.setattr(order_service, "log_business_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(order_service, "generate_id", lambda _prefix: "feedback-1")

    await OrderService.submit_feedback(
        db,
        order.id,
        FeedbackCreate(type=FeedbackType.REVISION, content="请修改"),
        _CustomerUser(),
    )

    assert order.status == OrderStatus.PREVIEW_READY
    assert order.revision_count == 1


@pytest.mark.asyncio
async def test_admin_publish_staff_deliverable_notifies_customer_by_inbox_and_email(monkeypatch):
    assignment = StaffAssignment(
        id="staff-assign-1",
        order_id="order-1",
        staff_id="staff-1",
        assigned_by="admin-1",
        status=StaffAssignmentStatus.IN_PROGRESS,
    )
    deliverable = StaffDeliverable(
        id="staff-dlv-1",
        assignment_id=assignment.id,
        stage_config_id="staff_default_delivery",
        stage_name="初稿交付",
        stage_order=1,
        version=1,
        status=DeliverableStatus.ADMIN_APPROVED,
    )
    order = Order(
        id="order-1",
        order_number="ORD-1",
        order_type=OrderType.AI_3D_CUSTOM,
        status=OrderStatus.IN_PRODUCTION,
        user_id="user-1",
        order_data={},
    )
    customer = User(
        id="user-1",
        username="customer",
        password_hash="hash",
        email="customer@example.com",
        role=UserRole.USER,
    )
    db = _FakeDb([
        _Result(scalar=None),
        _Result(scalar=deliverable),
        _Result(scalar=assignment),
        _Result(scalar=order),
        _Result(scalar=customer),
    ])
    email_calls = []

    async def fake_send_email(user_email, order_number, stage_name, published_note=None):
        email_calls.append((user_email, order_number, stage_name, published_note))
        return True

    monkeypatch.setattr(
        EmailService,
        "send_deliverable_published_notification",
        fake_send_email,
    )

    response = await contractor_admin.publish_deliverable_to_user(
        deliverable_id=deliverable.id,
        data=PublishDeliverableRequest(published_note="请确认初稿"),
        current_user=_AdminUser(),
        db=db,
    )

    notification = next(item for item in db.added if isinstance(item, Notification))
    assert notification.user_id == customer.id
    assert notification.type == NotificationType.PREVIEW_READY
    assert email_calls == [
        (customer.email, order.order_number, deliverable.stage_name, "请确认初稿")
    ]
    assert response.data["isPublishedToUser"] is True


@pytest.mark.asyncio
async def test_deliverable_published_email_uses_dedicated_template(monkeypatch):
    captured = {}

    async def fake_send_email(to_emails, subject, html_content, text_content=None, attachments=None):
        captured.update(
            to_emails=to_emails,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            attachments=attachments,
        )
        return True

    monkeypatch.setattr(EmailService, "send_email", fake_send_email)

    result = await EmailService.send_deliverable_published_notification(
        "customer@example.com",
        "ORD-1",
        "初稿交付",
        "请确认 <script>alert(1)</script>",
    )

    assert result is True
    assert captured["to_emails"] == ["customer@example.com"]
    assert captured["subject"] == "新交付物已发布 - ORD-1"
    assert "初稿交付" in captured["html_content"]
    assert "请确认 &lt;script&gt;alert(1)&lt;/script&gt;" in captured["html_content"]
    assert "请确认 <script>alert(1)</script>" in captured["text_content"]
