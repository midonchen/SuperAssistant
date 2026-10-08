"""add health_reminders and bill_reminders

Revision ID: 20260331_0023
Revises: 20260331_0022
Create Date: 2026-03-31
"""

from alembic import op
import sqlalchemy as sa


revision = "20260331_0023"
down_revision = "20260331_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "health_reminders",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("household_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("member_name", sa.String(length=64), nullable=False),
        sa.Column("reminder_type", sa.String(length=16), nullable=False, server_default="medication"),
        sa.Column("title", sa.String(length=128), nullable=False),
        sa.Column("period_days", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("next_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_health_reminders_household_id", "health_reminders", ["household_id"], unique=False)
    op.create_index("ix_health_reminders_user_id", "health_reminders", ["user_id"], unique=False)

    op.create_table(
        "bill_reminders",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("household_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.Column("period_months", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("next_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bill_reminders_household_id", "bill_reminders", ["household_id"], unique=False)
    op.create_index("ix_bill_reminders_user_id", "bill_reminders", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_bill_reminders_user_id", table_name="bill_reminders")
    op.drop_index("ix_bill_reminders_household_id", table_name="bill_reminders")
    op.drop_table("bill_reminders")
    op.drop_index("ix_health_reminders_user_id", table_name="health_reminders")
    op.drop_index("ix_health_reminders_household_id", table_name="health_reminders")
    op.drop_table("health_reminders")
