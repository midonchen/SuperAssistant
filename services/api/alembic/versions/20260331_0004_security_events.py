"""add security events table for session governance

Revision ID: 20260331_0004
Revises: 20260331_0003
Create Date: 2026-03-31
"""

from alembic import op
import sqlalchemy as sa


revision = "20260331_0004"
down_revision = "20260331_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "security_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_security_events_user_id", "security_events", ["user_id"], unique=False)
    op.create_index("ix_security_events_event_type", "security_events", ["event_type"], unique=False)
    op.create_index("ix_security_events_created_at", "security_events", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_security_events_created_at", table_name="security_events")
    op.drop_index("ix_security_events_event_type", table_name="security_events")
    op.drop_index("ix_security_events_user_id", table_name="security_events")
    op.drop_table("security_events")
