"""add meetings and meeting_action_items

Revision ID: 20260331_0013
Revises: 20260331_0012
Create Date: 2026-03-31
"""

from alembic import op
import sqlalchemy as sa


revision = "20260331_0013"
down_revision = "20260331_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "meetings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("transcript", sa.Text(), nullable=False, server_default=""),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_meetings_user_id", "meetings", ["user_id"], unique=False)
    op.create_index("ix_meetings_started_at", "meetings", ["started_at"], unique=False)

    op.create_table(
        "meeting_action_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("meeting_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("assignee", sa.String(length=128), nullable=True),
        sa.Column("done", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_meeting_action_items_meeting_id", "meeting_action_items", ["meeting_id"], unique=False)
    op.create_index("ix_meeting_action_items_user_id", "meeting_action_items", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_meeting_action_items_user_id", table_name="meeting_action_items")
    op.drop_index("ix_meeting_action_items_meeting_id", table_name="meeting_action_items")
    op.drop_table("meeting_action_items")
    op.drop_index("ix_meetings_started_at", table_name="meetings")
    op.drop_index("ix_meetings_user_id", table_name="meetings")
    op.drop_table("meetings")
