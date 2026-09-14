"""add approval requests table for high-risk admin actions

Revision ID: 20260331_0006
Revises: 20260331_0005
Create Date: 2026-03-31
"""

from alembic import op
import sqlalchemy as sa


revision = "20260331_0006"
down_revision = "20260331_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "approval_requests",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("action_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("target_user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("requested_by", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reviewed_by", sa.String(length=36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("request_payload", sa.JSON(), nullable=False),
        sa.Column("review_comment", sa.String(length=255), nullable=True),
        sa.Column("execution_result", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_approval_requests_action_type", "approval_requests", ["action_type"], unique=False)
    op.create_index("ix_approval_requests_status", "approval_requests", ["status"], unique=False)
    op.create_index("ix_approval_requests_target_user_id", "approval_requests", ["target_user_id"], unique=False)
    op.create_index("ix_approval_requests_requested_by", "approval_requests", ["requested_by"], unique=False)
    op.create_index("ix_approval_requests_reviewed_by", "approval_requests", ["reviewed_by"], unique=False)
    op.create_index("ix_approval_requests_created_at", "approval_requests", ["created_at"], unique=False)
    op.create_index("ix_approval_requests_reviewed_at", "approval_requests", ["reviewed_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_approval_requests_reviewed_at", table_name="approval_requests")
    op.drop_index("ix_approval_requests_created_at", table_name="approval_requests")
    op.drop_index("ix_approval_requests_reviewed_by", table_name="approval_requests")
    op.drop_index("ix_approval_requests_requested_by", table_name="approval_requests")
    op.drop_index("ix_approval_requests_target_user_id", table_name="approval_requests")
    op.drop_index("ix_approval_requests_status", table_name="approval_requests")
    op.drop_index("ix_approval_requests_action_type", table_name="approval_requests")
    op.drop_table("approval_requests")
