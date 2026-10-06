"""add job_applications

Revision ID: 20260331_0021
Revises: 20260331_0020
Create Date: 2026-03-31
"""

from alembic import op
import sqlalchemy as sa


revision = "20260331_0021"
down_revision = "20260331_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_applications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("company", sa.String(length=128), nullable=False),
        sa.Column("position", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="APPLIED"),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_job_applications_user_id", "job_applications", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_job_applications_user_id", table_name="job_applications")
    op.drop_table("job_applications")
