"""add website IP geo cache

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-28
"""

from alembic import op
import sqlalchemy as sa


revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "website_ip_geo_cache",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=False),
        sa.Column("country", sa.String(length=80), nullable=True),
        sa.Column("province", sa.String(length=120), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ip_address"),
    )
    op.create_index(op.f("ix_website_ip_geo_cache_id"), "website_ip_geo_cache", ["id"], unique=False)
    op.create_index(op.f("ix_website_ip_geo_cache_ip_address"), "website_ip_geo_cache", ["ip_address"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_website_ip_geo_cache_ip_address"), table_name="website_ip_geo_cache")
    op.drop_index(op.f("ix_website_ip_geo_cache_id"), table_name="website_ip_geo_cache")
    op.drop_table("website_ip_geo_cache")
