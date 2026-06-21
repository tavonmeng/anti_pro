"""create current schema baseline

Revision ID: 0001
Revises:
Create Date: 2026-05-29
"""

from alembic import op

from app.database import Base
import app.models  # noqa: F401 - register model metadata

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
