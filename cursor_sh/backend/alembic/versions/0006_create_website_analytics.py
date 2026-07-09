"""create website analytics tables

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-09
"""

from alembic import op
import sqlalchemy as sa


revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "website_visit_events",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("visited_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("visit_date", sa.Date(), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=False),
        sa.Column("ip_hash", sa.String(length=64), nullable=False),
        sa.Column("path", sa.String(length=255), nullable=False),
        sa.Column("referrer", sa.String(length=1000), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("counted_for_pv", sa.Boolean(), nullable=False),
        sa.Column("deduped", sa.Boolean(), nullable=False),
        sa.Column("country", sa.String(length=80), nullable=True),
        sa.Column("province", sa.String(length=120), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("geo_status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_website_visit_events_id"), "website_visit_events", ["id"], unique=False)
    op.create_index(op.f("ix_website_visit_events_visited_at"), "website_visit_events", ["visited_at"], unique=False)
    op.create_index(op.f("ix_website_visit_events_visit_date"), "website_visit_events", ["visit_date"], unique=False)
    op.create_index(op.f("ix_website_visit_events_ip_address"), "website_visit_events", ["ip_address"], unique=False)
    op.create_index(op.f("ix_website_visit_events_ip_hash"), "website_visit_events", ["ip_hash"], unique=False)
    op.create_index("ix_website_visit_events_date_time", "website_visit_events", ["visit_date", "visited_at"], unique=False)
    op.create_index("ix_website_visit_events_ip_date", "website_visit_events", ["ip_address", "visit_date"], unique=False)

    op.create_table(
        "website_visit_daily_stats",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("visit_date", sa.Date(), nullable=False),
        sa.Column("pv", sa.Integer(), nullable=False),
        sa.Column("uv", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("visit_date"),
    )
    op.create_index(op.f("ix_website_visit_daily_stats_id"), "website_visit_daily_stats", ["id"], unique=False)
    op.create_index(op.f("ix_website_visit_daily_stats_visit_date"), "website_visit_daily_stats", ["visit_date"], unique=False)

    op.create_table(
        "website_visit_path_daily_stats",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("visit_date", sa.Date(), nullable=False),
        sa.Column("path", sa.String(length=255), nullable=False),
        sa.Column("pv", sa.Integer(), nullable=False),
        sa.Column("uv", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("visit_date", "path", name="uq_website_visit_path_daily"),
    )
    op.create_index(op.f("ix_website_visit_path_daily_stats_id"), "website_visit_path_daily_stats", ["id"], unique=False)
    op.create_index(op.f("ix_website_visit_path_daily_stats_visit_date"), "website_visit_path_daily_stats", ["visit_date"], unique=False)
    op.create_index("ix_website_visit_path_daily_date_pv", "website_visit_path_daily_stats", ["visit_date", "pv"], unique=False)

    op.create_table(
        "website_visit_uniques",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("visit_date", sa.Date(), nullable=False),
        sa.Column("scope", sa.String(length=20), nullable=False),
        sa.Column("scope_value", sa.String(length=255), nullable=False),
        sa.Column("ip_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("visit_date", "scope", "scope_value", "ip_hash", name="uq_website_visit_unique_scope"),
    )
    op.create_index(op.f("ix_website_visit_uniques_id"), "website_visit_uniques", ["id"], unique=False)
    op.create_index(op.f("ix_website_visit_uniques_visit_date"), "website_visit_uniques", ["visit_date"], unique=False)
    op.create_index("ix_website_visit_uniques_date_scope", "website_visit_uniques", ["visit_date", "scope"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_website_visit_uniques_date_scope", table_name="website_visit_uniques")
    op.drop_index(op.f("ix_website_visit_uniques_visit_date"), table_name="website_visit_uniques")
    op.drop_index(op.f("ix_website_visit_uniques_id"), table_name="website_visit_uniques")
    op.drop_table("website_visit_uniques")

    op.drop_index("ix_website_visit_path_daily_date_pv", table_name="website_visit_path_daily_stats")
    op.drop_index(op.f("ix_website_visit_path_daily_stats_visit_date"), table_name="website_visit_path_daily_stats")
    op.drop_index(op.f("ix_website_visit_path_daily_stats_id"), table_name="website_visit_path_daily_stats")
    op.drop_table("website_visit_path_daily_stats")

    op.drop_index(op.f("ix_website_visit_daily_stats_visit_date"), table_name="website_visit_daily_stats")
    op.drop_index(op.f("ix_website_visit_daily_stats_id"), table_name="website_visit_daily_stats")
    op.drop_table("website_visit_daily_stats")

    op.drop_index("ix_website_visit_events_ip_date", table_name="website_visit_events")
    op.drop_index("ix_website_visit_events_date_time", table_name="website_visit_events")
    op.drop_index(op.f("ix_website_visit_events_ip_hash"), table_name="website_visit_events")
    op.drop_index(op.f("ix_website_visit_events_ip_address"), table_name="website_visit_events")
    op.drop_index(op.f("ix_website_visit_events_visit_date"), table_name="website_visit_events")
    op.drop_index(op.f("ix_website_visit_events_visited_at"), table_name="website_visit_events")
    op.drop_index(op.f("ix_website_visit_events_id"), table_name="website_visit_events")
    op.drop_table("website_visit_events")
