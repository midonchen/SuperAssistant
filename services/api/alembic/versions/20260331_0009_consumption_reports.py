"""add consumption_reports

Revision ID: 20260331_0009
Revises: 20260331_0008
Create Date: 2026-03-31
"""

from alembic import op
import sqlalchemy as sa


revision = "20260331_0009"
down_revision = "20260331_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "consumption_reports",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("household_id", sa.String(length=36), nullable=False),
        sa.Column("month", sa.String(length=7), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("household_id", "month", name="uq_consumption_report_household_month"),
    )
    op.create_index("ix_consumption_reports_household_id", "consumption_reports", ["household_id"], unique=False)
    op.create_index("ix_consumption_reports_month", "consumption_reports", ["month"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_consumption_reports_month", table_name="consumption_reports")
    op.drop_index("ix_consumption_reports_household_id", table_name="consumption_reports")
    op.drop_table("consumption_reports")
