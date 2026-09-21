"""add weekly_reports

Revision ID: 20260331_0014
Revises: 20260331_0013
Create Date: 2026-03-31
"""

from alembic import op
import sqlalchemy as sa


revision = "20260331_0014"
down_revision = "20260331_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "weekly_reports",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("week_start", sa.String(length=10), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "week_start", name="uq_weekly_reports_user_week"),
    )
    op.create_index("ix_weekly_reports_user_id", "weekly_reports", ["user_id"], unique=False)
    op.create_index("ix_weekly_reports_week_start", "weekly_reports", ["week_start"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_weekly_reports_week_start", table_name="weekly_reports")
    op.drop_index("ix_weekly_reports_user_id", table_name="weekly_reports")
    op.drop_table("weekly_reports")
