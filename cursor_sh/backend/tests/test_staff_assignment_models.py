from app.models.staff_assignment import StaffAssignment, StaffAssignmentStatus
from app.models.staff_deliverable import StaffDeliverable


def test_staff_assignment_uses_separate_table_and_internal_statuses():
    assert StaffAssignment.__tablename__ == "staff_assignments"
    assert {status.value for status in StaffAssignmentStatus} == {
        "in_progress",
        "completed",
        "cancelled",
    }
    assert "staff_id" in StaffAssignment.__table__.columns
    assert "reject_reason" not in StaffAssignment.__table__.columns


def test_staff_deliverable_uses_staff_assignment_foreign_key():
    assignment_fk = next(iter(StaffDeliverable.__table__.columns["assignment_id"].foreign_keys))

    assert StaffDeliverable.__tablename__ == "staff_deliverables"
    assert assignment_fk.target_fullname == "staff_assignments.id"
