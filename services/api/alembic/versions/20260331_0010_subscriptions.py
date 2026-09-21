"""add subscription_tiers and users.subscription_tier_id

Revision ID: 20260331_0010
Revises: 20260331_0009
Create Date: 2026-03-31
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


revision = "20260331_0010"
down_revision = "20260331_0009"
branch_labels = None
depends_on = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def upgrade() -> None:
    op.create_table(
        "subscription_tiers",
        sa.Column("id", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=32), nullable=False),
        sa.Column("monthly_price", sa.Float(), nullable=False, server_default="0"),
        sa.Column("limits", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    tiers = sa.table(
        "subscription_tiers",
        sa.column("id", sa.String),
        sa.column("name", sa.String),
        sa.column("monthly_price", sa.Float),
        sa.column("limits", sa.JSON),
        sa.column("created_at", sa.DateTime),
    )
    op.bulk_insert(
        tiers,
        [
            {
                "id": "free",
                "name": "Free",
                "monthly_price": 0.0,
                "limits": {"custom_categories": 3, "household_members": 2},
                "created_at": _now(),
            },
            {
                "id": "pro",
                "name": "Pro",
                "monthly_price": 18.0,
                "limits": None,
                "created_at": _now(),
            },
        ],
    )

    op.add_column("users", sa.Column("subscription_tier_id", sa.String(length=16), nullable=True))
    op.create_index("ix_users_subscription_tier_id", "users", ["subscription_tier_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_users_subscription_tier_id", table_name="users")
    op.drop_column("users", "subscription_tier_id")
    op.drop_table("subscription_tiers")
