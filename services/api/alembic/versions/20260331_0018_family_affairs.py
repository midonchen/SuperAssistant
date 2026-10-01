"""add family_affairs

Revision ID: 20260331_0018
Revises: 20260331_0017
Create Date: 2026-03-31
"""

from alembic import op
import sqlalchemy as sa


revision = "20260331_0018"
down_revision = "20260331_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "family_affairs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("household_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=128), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assignee", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="TODO"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_family_affairs_household_id", "family_affairs", ["household_id"], unique=False)
    op.create_index("ix_family_affairs_user_id", "family_affairs", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_family_affairs_user_id", table_name="family_affairs")
    op.drop_index("ix_family_affairs_household_id", table_name="family_affairs")
    op.drop_table("family_affairs")
