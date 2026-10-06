"""add learning_items

Revision ID: 20260331_0022
Revises: 20260331_0021
Create Date: 2026-03-31
"""

from alembic import op
import sqlalchemy as sa


revision = "20260331_0022"
down_revision = "20260331_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "learning_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=128), nullable=False),
        sa.Column("item_type", sa.String(length=16), nullable=False, server_default="course"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="TODO"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_learning_items_user_id", "learning_items", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_learning_items_user_id", table_name="learning_items")
    op.drop_table("learning_items")
