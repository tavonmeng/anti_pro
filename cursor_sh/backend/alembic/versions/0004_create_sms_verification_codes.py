"""create sms verification codes

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-10
"""

from alembic import op
import sqlalchemy as sa


revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sms_verification_codes",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("send_status", sa.String(length=30), nullable=False),
        sa.Column("consumed", sa.Boolean(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sms_verification_codes_id"), "sms_verification_codes", ["id"], unique=False)
    op.create_index(op.f("ix_sms_verification_codes_phone"), "sms_verification_codes", ["phone"], unique=False)
    op.create_index(op.f("ix_sms_verification_codes_send_status"), "sms_verification_codes", ["send_status"], unique=False)
    op.create_index(op.f("ix_sms_verification_codes_consumed"), "sms_verification_codes", ["consumed"], unique=False)
    op.create_index(op.f("ix_sms_verification_codes_expires_at"), "sms_verification_codes", ["expires_at"], unique=False)
    op.create_index(op.f("ix_sms_verification_codes_created_at"), "sms_verification_codes", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_sms_verification_codes_created_at"), table_name="sms_verification_codes")
    op.drop_index(op.f("ix_sms_verification_codes_expires_at"), table_name="sms_verification_codes")
    op.drop_index(op.f("ix_sms_verification_codes_consumed"), table_name="sms_verification_codes")
    op.drop_index(op.f("ix_sms_verification_codes_send_status"), table_name="sms_verification_codes")
    op.drop_index(op.f("ix_sms_verification_codes_phone"), table_name="sms_verification_codes")
    op.drop_index(op.f("ix_sms_verification_codes_id"), table_name="sms_verification_codes")
    op.drop_table("sms_verification_codes")

