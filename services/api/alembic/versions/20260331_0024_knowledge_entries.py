"""add knowledge_entries

Revision ID: 20260331_0024
Revises: 20260331_0023
Create Date: 2026-03-31
"""

from alembic import op
import sqlalchemy as sa


revision = "20260331_0024"
down_revision = "20260331_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_entries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("applications", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_entries_user_id", "knowledge_entries", ["user_id"], unique=False)
    op.create_index("ix_knowledge_entries_kind", "knowledge_entries", ["kind"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_knowledge_entries_kind", table_name="knowledge_entries")
    op.drop_index("ix_knowledge_entries_user_id", table_name="knowledge_entries")
    op.drop_table("knowledge_entries")
