"""add push device, preference, and delivery tables

Revision ID: 20260331_0003
Revises: 20260331_0002
Create Date: 2026-03-31
"""

from alembic import op
import sqlalchemy as sa


revision = "20260331_0003"
down_revision = "20260331_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "push_devices",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("platform", sa.String(length=16), nullable=False),
        sa.Column("device_token", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "device_token", name="uq_push_device_user_token"),
    )
    op.create_index("ix_push_devices_user_id", "push_devices", ["user_id"], unique=False)

    op.create_table(
        "push_preferences",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("notify_time", sa.String(length=8), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", name="uq_push_preference_user"),
    )
    op.create_index("ix_push_preferences_user_id", "push_preferences", ["user_id"], unique=False)

    op.create_table(
        "push_deliveries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("suggestion_id", sa.String(length=36), sa.ForeignKey("purchase_suggestions.id"), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_push_deliveries_user_id", "push_deliveries", ["user_id"], unique=False)
    op.create_index("ix_push_deliveries_suggestion_id", "push_deliveries", ["suggestion_id"], unique=False)
    op.create_index("ix_push_deliveries_status", "push_deliveries", ["status"], unique=False)
    op.create_index("ix_push_deliveries_created_at", "push_deliveries", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_push_deliveries_created_at", table_name="push_deliveries")
    op.drop_index("ix_push_deliveries_status", table_name="push_deliveries")
    op.drop_index("ix_push_deliveries_suggestion_id", table_name="push_deliveries")
    op.drop_index("ix_push_deliveries_user_id", table_name="push_deliveries")
    op.drop_table("push_deliveries")

    op.drop_index("ix_push_preferences_user_id", table_name="push_preferences")
    op.drop_table("push_preferences")

    op.drop_index("ix_push_devices_user_id", table_name="push_devices")
    op.drop_table("push_devices")
