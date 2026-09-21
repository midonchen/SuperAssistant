"""add analytics_events

Revision ID: 20260331_0011
Revises: 20260331_0010
Create Date: 2026-03-31
"""

from alembic import op
import sqlalchemy as sa


revision = "20260331_0011"
down_revision = "20260331_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analytics_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("household_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_analytics_events_user_id", "analytics_events", ["user_id"], unique=False)
    op.create_index("ix_analytics_events_household_id", "analytics_events", ["household_id"], unique=False)
    op.create_index("ix_analytics_events_event_type", "analytics_events", ["event_type"], unique=False)
    op.create_index("ix_analytics_events_created_at", "analytics_events", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_analytics_events_created_at", table_name="analytics_events")
    op.drop_index("ix_analytics_events_event_type", table_name="analytics_events")
    op.drop_index("ix_analytics_events_household_id", table_name="analytics_events")
    op.drop_index("ix_analytics_events_user_id", table_name="analytics_events")
    op.drop_table("analytics_events")
