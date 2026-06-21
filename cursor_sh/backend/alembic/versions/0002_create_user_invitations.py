"""create user invitations

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-02
"""

from alembic import op
import sqlalchemy as sa


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_invitations",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("token", sa.String(length=100), nullable=False),
        sa.Column("created_by", sa.String(length=50), nullable=False),
        sa.Column("used_by", sa.String(length=50), nullable=True),
        sa.Column("is_used", sa.Boolean(), nullable=True),
        sa.Column("company_name", sa.String(length=100), nullable=True),
        sa.Column("memory_user_id", sa.String(length=50), nullable=True),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_invitations_id"), "user_invitations", ["id"], unique=False)
    op.create_index(op.f("ix_user_invitations_token"), "user_invitations", ["token"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_invitations_token"), table_name="user_invitations")
    op.drop_index(op.f("ix_user_invitations_id"), table_name="user_invitations")
    op.drop_table("user_invitations")
