"""initial schema

Revision ID: 20260331_0001
Revises:
Create Date: 2026-03-31
"""

from alembic import op
import sqlalchemy as sa


revision = "20260331_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("phone_masked", sa.String(length=32), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("shopping_day", sa.Integer(), nullable=False),
        sa.Column("shopping_cycle", sa.Integer(), nullable=False),
        sa.Column("onboarded", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_phone", "users", ["phone"], unique=True)

    op.create_table(
        "sessions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("access_token", sa.String(length=96), nullable=False),
        sa.Column("refresh_token", sa.String(length=96), nullable=False),
        sa.Column("device_id", sa.String(length=128), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sessions_access_token", "sessions", ["access_token"], unique=True)
    op.create_index("ix_sessions_refresh_token", "sessions", ["refresh_token"], unique=True)
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"], unique=False)

    op.create_table(
        "inventory_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("item_key", sa.String(length=16), nullable=False),
        sa.Column("item_name", sa.String(length=32), nullable=False),
        sa.Column("unit", sa.String(length=16), nullable=False),
        sa.Column("current_stock", sa.Float(), nullable=False),
        sa.Column("max_stock", sa.Float(), nullable=False),
        sa.Column("warning_threshold", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("daily_avg_rate", sa.Float(), nullable=False),
        sa.Column("last_calibrated", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=False),
        sa.Column("server_version", sa.Integer(), nullable=False),
        sa.UniqueConstraint("user_id", "item_key", name="uq_inventory_user_item"),
    )
    op.create_index("ix_inventory_items_user_id", "inventory_items", ["user_id"], unique=False)
    op.create_index("ix_inventory_items_item_key", "inventory_items", ["item_key"], unique=False)

    op.create_table(
        "activity_logs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("item_key", sa.String(length=16), nullable=False),
        sa.Column("action_type", sa.String(length=24), nullable=False),
        sa.Column("operation", sa.String(length=16), nullable=False),
        sa.Column("delta_value", sa.Float(), nullable=False),
        sa.Column("before_value", sa.Float(), nullable=False),
        sa.Column("after_value", sa.Float(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("operator_role", sa.String(length=32), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_activity_logs_user_id", "activity_logs", ["user_id"], unique=False)
    op.create_index("ix_activity_logs_item_key", "activity_logs", ["item_key"], unique=False)
    op.create_index("ix_activity_logs_timestamp", "activity_logs", ["timestamp"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_activity_logs_timestamp", table_name="activity_logs")
    op.drop_index("ix_activity_logs_item_key", table_name="activity_logs")
    op.drop_index("ix_activity_logs_user_id", table_name="activity_logs")
    op.drop_table("activity_logs")

    op.drop_index("ix_inventory_items_item_key", table_name="inventory_items")
    op.drop_index("ix_inventory_items_user_id", table_name="inventory_items")
    op.drop_table("inventory_items")

    op.drop_index("ix_sessions_user_id", table_name="sessions")
    op.drop_index("ix_sessions_refresh_token", table_name="sessions")
    op.drop_index("ix_sessions_access_token", table_name="sessions")
    op.drop_table("sessions")

    op.drop_index("ix_users_phone", table_name="users")
    op.drop_table("users")
