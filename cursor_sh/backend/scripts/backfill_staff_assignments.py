"""Backfill staff_assignments from existing order_assignees.

Default mode is dry-run. Use --apply to write rows.
"""

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.models  # noqa: F401 - register SQLAlchemy models
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from app.database import async_session_maker
from app.models.order import Order, OrderAssignee, OrderStatus
from app.models.staff_assignment import StaffAssignment, StaffAssignmentStatus
from app.services.staff_creator_service import (
    build_staff_assignment,
    plan_staff_assignment_backfill,
)


def _status_value(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _mark_schedule(schedule: list[dict], status: str) -> list[dict]:
    next_schedule = [dict(stage) for stage in schedule or []]
    for stage in next_schedule:
        stage["status"] = status
    return next_schedule


def _apply_order_status(assignment: StaffAssignment, order: Order | None) -> None:
    if not order:
        return

    status = _status_value(order.status)
    if status == OrderStatus.COMPLETED.value:
        assignment.status = StaffAssignmentStatus.COMPLETED
        assignment.completed_at = order.updated_at or assignment.assigned_at
        assignment.schedule = _mark_schedule(assignment.schedule, "completed")
        flag_modified(assignment, "schedule")
    elif status == OrderStatus.CANCELLED.value:
        assignment.status = StaffAssignmentStatus.CANCELLED
        assignment.completed_at = order.updated_at or assignment.assigned_at
        assignment.schedule = _mark_schedule(assignment.schedule, "cancelled")
        flag_modified(assignment, "schedule")


def _is_missing_table_error(error: Exception) -> bool:
    text = str(error).lower()
    return "no such table" in text or "doesn't exist" in text


async def backfill_staff_assignments(*, apply: bool, assigned_by: str, limit: int | None = None) -> dict:
    async with async_session_maker() as db:
        assignee_result = await db.execute(
            select(
                OrderAssignee.order_id,
                OrderAssignee.assignee_id,
                OrderAssignee.created_at,
            )
        )
        assignee_rows = assignee_result.all()
        assignee_pairs = {(row.order_id, row.assignee_id) for row in assignee_rows}
        assignee_created_at = {
            (row.order_id, row.assignee_id): row.created_at
            for row in assignee_rows
        }

        existing_result = await db.execute(
            select(StaffAssignment.order_id, StaffAssignment.staff_id).where(
                StaffAssignment.status != StaffAssignmentStatus.CANCELLED
            )
        )
        existing_pairs = {(row.order_id, row.staff_id) for row in existing_result.all()}

        missing_pairs = sorted(plan_staff_assignment_backfill(assignee_pairs, existing_pairs))
        if limit is not None:
            missing_pairs = missing_pairs[:limit]

        order_ids = {order_id for order_id, _staff_id in missing_pairs}
        orders_by_id: dict[str, Order] = {}
        if order_ids:
            orders_result = await db.execute(select(Order).where(Order.id.in_(order_ids)))
            orders_by_id = {order.id: order for order in orders_result.scalars().all()}

        if apply:
            for order_id, staff_id in missing_pairs:
                assignment = build_staff_assignment(
                    order_id=order_id,
                    staff_id=staff_id,
                    assigned_by=assigned_by,
                )
                assigned_at = assignee_created_at.get((order_id, staff_id))
                if assigned_at:
                    assignment.assigned_at = assigned_at
                    assignment.responded_at = assigned_at
                _apply_order_status(assignment, orders_by_id.get(order_id))
                db.add(assignment)
            await db.commit()
        else:
            await db.rollback()

        return {
            "assignee_pairs": len(assignee_pairs),
            "existing_pairs": len(existing_pairs),
            "missing_pairs": len(missing_pairs),
            "applied": apply,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill staff_assignments from order_assignees.")
    parser.add_argument("--apply", action="store_true", help="Write missing staff assignment rows.")
    parser.add_argument("--assigned-by", default="system_backfill", help="Value for staff_assignments.assigned_by.")
    parser.add_argument("--limit", type=int, default=None, help="Limit rows for a staged rollout.")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    try:
        result = await backfill_staff_assignments(
            apply=args.apply,
            assigned_by=args.assigned_by,
            limit=args.limit,
        )
    except Exception as exc:
        if _is_missing_table_error(exc):
            raise SystemExit(
                "Database schema is missing required tables. Run `alembic upgrade head` before this backfill."
            ) from exc
        raise
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"[{mode}] order_assignees={result['assignee_pairs']}")
    print(f"[{mode}] existing_staff_assignments={result['existing_pairs']}")
    print(f"[{mode}] missing_staff_assignments={result['missing_pairs']}")
    if not args.apply:
        print("[DRY-RUN] Re-run with --apply to write rows.")


if __name__ == "__main__":
    asyncio.run(main())
