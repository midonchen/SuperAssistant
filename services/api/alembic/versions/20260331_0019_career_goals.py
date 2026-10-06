"""add career_goals

Revision ID: 20260331_0019
Revises: 20260331_0018
Create Date: 2026-03-31
"""

from alembic import op
import sqlalchemy as sa


revision = "20260331_0019"
down_revision = "20260331_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "career_goals",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("target_year", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="ACTIVE"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_career_goals_user_id", "career_goals", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_career_goals_user_id", table_name="career_goals")
    op.drop_table("career_goals")
