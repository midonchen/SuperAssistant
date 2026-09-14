"""add suggestion and audit task tables

Revision ID: 20260331_0002
Revises: 20260331_0001
Create Date: 2026-03-31
"""

from alembic import op
import sqlalchemy as sa


revision = "20260331_0002"
down_revision = "20260331_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "purchase_suggestions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
    )
    op.create_index("ix_purchase_suggestions_user_id", "purchase_suggestions", ["user_id"], unique=False)
    op.create_index("ix_purchase_suggestions_generated_at", "purchase_suggestions", ["generated_at"], unique=False)

    op.create_table(
        "purchase_suggestion_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("suggestion_id", sa.String(length=36), sa.ForeignKey("purchase_suggestions.id"), nullable=False),
        sa.Column("item_key", sa.String(length=16), nullable=False),
        sa.Column("suggested_qty", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.String(length=256), nullable=False),
    )
    op.create_index("ix_purchase_suggestion_items_suggestion_id", "purchase_suggestion_items", ["suggestion_id"], unique=False)

    op.create_table(
        "audit_tasks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("parse_session_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("entities", sa.JSON(), nullable=False),
        sa.Column("review_action", sa.String(length=16), nullable=True),
        sa.Column("corrected_entities", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_audit_tasks_parse_session_id", "audit_tasks", ["parse_session_id"], unique=False)
    op.create_index("ix_audit_tasks_status", "audit_tasks", ["status"], unique=False)
    op.create_index("ix_audit_tasks_created_at", "audit_tasks", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_tasks_created_at", table_name="audit_tasks")
    op.drop_index("ix_audit_tasks_status", table_name="audit_tasks")
    op.drop_index("ix_audit_tasks_parse_session_id", table_name="audit_tasks")
    op.drop_table("audit_tasks")

    op.drop_index("ix_purchase_suggestion_items_suggestion_id", table_name="purchase_suggestion_items")
    op.drop_table("purchase_suggestion_items")

    op.drop_index("ix_purchase_suggestions_generated_at", table_name="purchase_suggestions")
    op.drop_index("ix_purchase_suggestions_user_id", table_name="purchase_suggestions")
    op.drop_table("purchase_suggestions")
