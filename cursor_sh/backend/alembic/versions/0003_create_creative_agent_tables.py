"""create creative agent tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def _metadata() -> sa.MetaData:
    metadata = sa.MetaData()

    sa.Table(
        "creative_sessions",
        metadata,
        sa.Column("id", sa.String(length=50), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False, default=""),
        sa.Column("created_by_id", sa.String(length=50), nullable=False, index=True),
        sa.Column("created_by_name", sa.String(length=100), nullable=True),
        sa.Column("visibility", sa.String(length=20), nullable=False, default="team", index=True),
        sa.Column("source_type", sa.String(length=30), nullable=False, default="manual", index=True),
        sa.Column("source_order_id", sa.String(length=50), nullable=True, index=True),
        sa.Column("customer_user_id", sa.String(length=50), nullable=True, index=True),
        sa.Column("brief_json", sa.JSON(), nullable=True),
        sa.Column("designer_direction", sa.Text(), nullable=True),
        sa.Column("seed_ideas", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, default="draft", index=True),
        sa.Column("selected_idea_id", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Index("ix_creative_sessions_id", "id"),
    )

    sa.Table(
        "creative_ideas",
        metadata,
        sa.Column("id", sa.String(length=50), primary_key=True),
        sa.Column("session_id", sa.String(length=50), sa.ForeignKey("creative_sessions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("parent_id", sa.String(length=50), nullable=True, index=True),
        sa.Column("run_id", sa.String(length=50), nullable=True, index=True),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.Column("title", sa.String(length=200), nullable=False, default=""),
        sa.Column("core_concept", sa.Text(), nullable=True),
        sa.Column("spatial_mechanism", sa.Text(), nullable=True),
        sa.Column("story_outline", sa.Text(), nullable=True),
        sa.Column("production_notes", sa.Text(), nullable=True),
        sa.Column("risk_notes", sa.Text(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, default="proposed", index=True),
        sa.Column("score", sa.Integer(), nullable=True, index=True),
        sa.Column("created_by_role", sa.String(length=30), nullable=False, default="agent"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Index("ix_creative_ideas_id", "id"),
    )

    sa.Table(
        "creative_reviews",
        metadata,
        sa.Column("id", sa.String(length=50), primary_key=True),
        sa.Column("idea_id", sa.String(length=50), sa.ForeignKey("creative_ideas.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("run_id", sa.String(length=50), nullable=True, index=True),
        sa.Column("rubric_version", sa.String(length=50), nullable=False, default="creative_qc_v1"),
        sa.Column("scores_json", sa.JSON(), nullable=True),
        sa.Column("total_score", sa.Integer(), nullable=False, default=0, index=True),
        sa.Column("grade", sa.String(length=30), nullable=True),
        sa.Column("core_issues", sa.JSON(), nullable=True),
        sa.Column("recommendations", sa.JSON(), nullable=True),
        sa.Column("risk_flags", sa.JSON(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Index("ix_creative_reviews_id", "id"),
    )

    sa.Table(
        "creative_runs",
        metadata,
        sa.Column("id", sa.String(length=50), primary_key=True),
        sa.Column("session_id", sa.String(length=50), sa.ForeignKey("creative_sessions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("run_type", sa.String(length=30), nullable=False, default="auto_optimize", index=True),
        sa.Column("status", sa.String(length=30), nullable=False, default="queued", index=True),
        sa.Column("provider", sa.String(length=30), nullable=False, default="hermes"),
        sa.Column("hermes_run_id", sa.String(length=100), nullable=True, index=True),
        sa.Column("hermes_session_id", sa.String(length=100), nullable=True, index=True),
        sa.Column("previous_response_id", sa.String(length=100), nullable=True),
        sa.Column("input_json", sa.JSON(), nullable=True),
        sa.Column("output_json", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Index("ix_creative_runs_id", "id"),
    )

    sa.Table(
        "creative_run_events",
        metadata,
        sa.Column("id", sa.String(length=50), primary_key=True),
        sa.Column("run_id", sa.String(length=50), sa.ForeignKey("creative_runs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("session_id", sa.String(length=50), nullable=False, index=True),
        sa.Column("sequence", sa.Integer(), nullable=False, default=1),
        sa.Column("event_type", sa.String(length=60), nullable=False, index=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("source", sa.String(length=30), nullable=False, default="backend"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Index("ix_creative_run_events_id", "id"),
    )

    sa.Table(
        "creative_agent_steps",
        metadata,
        sa.Column("id", sa.String(length=50), primary_key=True),
        sa.Column("session_id", sa.String(length=50), sa.ForeignKey("creative_sessions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("run_id", sa.String(length=50), sa.ForeignKey("creative_runs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("step_index", sa.Integer(), nullable=False, default=1, index=True),
        sa.Column("phase", sa.String(length=30), nullable=False, default="action", index=True),
        sa.Column("role", sa.String(length=60), nullable=False, default=""),
        sa.Column("tool_name", sa.String(length=100), nullable=False, default=""),
        sa.Column("input_summary", sa.Text(), nullable=True),
        sa.Column("output_summary", sa.Text(), nullable=True),
        sa.Column("observation", sa.Text(), nullable=True),
        sa.Column("reflection_summary", sa.Text(), nullable=True),
        sa.Column("decision", sa.Text(), nullable=True),
        sa.Column("next_action", sa.Text(), nullable=True),
        sa.Column("score_snapshot", sa.JSON(), nullable=True),
        sa.Column("dimension_deltas", sa.JSON(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Index("ix_creative_agent_steps_id", "id"),
    )

    sa.Table(
        "creative_iterations",
        metadata,
        sa.Column("id", sa.String(length=50), primary_key=True),
        sa.Column("session_id", sa.String(length=50), sa.ForeignKey("creative_sessions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("run_id", sa.String(length=50), sa.ForeignKey("creative_runs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("round_index", sa.Integer(), nullable=False, default=1, index=True),
        sa.Column("action", sa.String(length=80), nullable=False, default=""),
        sa.Column("score_before", sa.Integer(), nullable=True),
        sa.Column("score_after", sa.Integer(), nullable=True),
        sa.Column("score_delta", sa.Integer(), nullable=True),
        sa.Column("focus", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("agent_explanation", sa.Text(), nullable=True),
        sa.Column("dimension_deltas", sa.JSON(), nullable=True),
        sa.Column("key_improvements", sa.JSON(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Index("ix_creative_iterations_id", "id"),
    )

    sa.Table(
        "creative_designer_feedbacks",
        metadata,
        sa.Column("id", sa.String(length=50), primary_key=True),
        sa.Column("session_id", sa.String(length=50), sa.ForeignKey("creative_sessions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("run_id", sa.String(length=50), sa.ForeignKey("creative_runs.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("target_idea_id", sa.String(length=50), nullable=True, index=True),
        sa.Column("feedback_text", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(length=30), nullable=False, default="normal"),
        sa.Column("constraints", sa.JSON(), nullable=True),
        sa.Column("liked_parts", sa.JSON(), nullable=True),
        sa.Column("disliked_parts", sa.JSON(), nullable=True),
        sa.Column("requested_changes", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, default="submitted", index=True),
        sa.Column("created_by_id", sa.String(length=50), nullable=False, default=""),
        sa.Column("created_by_name", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Index("ix_creative_designer_feedbacks_id", "id"),
    )

    sa.Table(
        "creative_memory_entries",
        metadata,
        sa.Column("id", sa.String(length=50), primary_key=True),
        sa.Column("scope", sa.String(length=20), nullable=False, default="team", index=True),
        sa.Column("owner_id", sa.String(length=50), nullable=True, index=True),
        sa.Column("kind", sa.String(length=50), nullable=False, default="principle", index=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, default="approved", index=True),
        sa.Column("created_by_id", sa.String(length=50), nullable=False, default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Index("ix_creative_memory_entries_id", "id"),
    )

    return metadata


def upgrade() -> None:
    bind = op.get_bind()
    for table in _metadata().sorted_tables:
        table.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for table in reversed(_metadata().sorted_tables):
        table.drop(bind=bind, checkfirst=True)
