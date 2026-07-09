"""create staff assignment tables

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-08
"""

from alembic import op
import sqlalchemy as sa


revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "staff_assignments",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("order_id", sa.String(length=50), nullable=False),
        sa.Column("staff_id", sa.String(length=50), nullable=False),
        sa.Column("assigned_by", sa.String(length=50), nullable=False),
        sa.Column("status", sa.Enum("IN_PROGRESS", "COMPLETED", "CANCELLED", name="staffassignmentstatus"), nullable=False),
        sa.Column("schedule", sa.JSON(), nullable=True),
        sa.Column("current_stage_order", sa.String(length=10), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_staff_assignments_id"), "staff_assignments", ["id"], unique=False)
    op.create_index(op.f("ix_staff_assignments_order_id"), "staff_assignments", ["order_id"], unique=False)
    op.create_index(op.f("ix_staff_assignments_staff_id"), "staff_assignments", ["staff_id"], unique=False)

    op.create_table(
        "staff_deliverables",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("assignment_id", sa.String(length=50), nullable=False),
        sa.Column("stage_config_id", sa.String(length=50), nullable=False),
        sa.Column("stage_name", sa.String(length=50), nullable=False),
        sa.Column("stage_order", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.String(length=50), nullable=True),
        sa.Column("files", sa.JSON(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("self_review_checks", sa.JSON(), nullable=True),
        sa.Column("status", sa.Enum("DRAFT", "SUBMITTED", "ADMIN_APPROVED", "ADMIN_REJECTED", name="deliverablestatus"), nullable=False),
        sa.Column("admin_review_note", sa.Text(), nullable=True),
        sa.Column("admin_reviewed_by", sa.String(length=50), nullable=True),
        sa.Column("admin_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_published_to_user", sa.Boolean(), nullable=True),
        sa.Column("published_note", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_by", sa.String(length=50), nullable=True),
        sa.Column("admin_comments", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["assignment_id"], ["staff_assignments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_staff_deliverables_id"), "staff_deliverables", ["id"], unique=False)
    op.create_index(op.f("ix_staff_deliverables_assignment_id"), "staff_deliverables", ["assignment_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_staff_deliverables_assignment_id"), table_name="staff_deliverables")
    op.drop_index(op.f("ix_staff_deliverables_id"), table_name="staff_deliverables")
    op.drop_table("staff_deliverables")
    op.drop_index(op.f("ix_staff_assignments_staff_id"), table_name="staff_assignments")
    op.drop_index(op.f("ix_staff_assignments_order_id"), table_name="staff_assignments")
    op.drop_index(op.f("ix_staff_assignments_id"), table_name="staff_assignments")
    op.drop_table("staff_assignments")
