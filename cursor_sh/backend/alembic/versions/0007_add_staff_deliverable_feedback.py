"""add staff deliverable feedback target

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-15
"""

from alembic import op
import sqlalchemy as sa


revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "feedbacks",
        sa.Column("staff_deliverable_id", sa.String(length=50), nullable=True),
    )
    op.create_index(
        op.f("ix_feedbacks_staff_deliverable_id"),
        "feedbacks",
        ["staff_deliverable_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_feedbacks_staff_deliverable_id",
        "feedbacks",
        "staff_deliverables",
        ["staff_deliverable_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_feedbacks_staff_deliverable_id",
        "feedbacks",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_feedbacks_staff_deliverable_id"),
        table_name="feedbacks",
    )
    op.drop_column("feedbacks", "staff_deliverable_id")
