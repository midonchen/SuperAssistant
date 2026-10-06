"""add skills

Revision ID: 20260331_0020
Revises: 20260331_0019
Create Date: 2026-03-31
"""

from alembic import op
import sqlalchemy as sa


revision = "20260331_0020"
down_revision = "20260331_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "skills",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=True),
        sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("target_level", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_skills_user_id", "skills", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_skills_user_id", table_name="skills")
    op.drop_table("skills")
