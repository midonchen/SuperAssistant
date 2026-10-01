"""add gift_suggestions

Revision ID: 20260331_0017
Revises: 20260331_0016
Create Date: 2026-03-31
"""

from alembic import op
import sqlalchemy as sa


revision = "20260331_0017"
down_revision = "20260331_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gift_suggestions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("contact_id", sa.String(length=36), nullable=False),
        sa.Column("occasion_id", sa.String(length=36), nullable=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("budget", sa.Float(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_gift_suggestions_contact_id", "gift_suggestions", ["contact_id"], unique=False)
    op.create_index("ix_gift_suggestions_user_id", "gift_suggestions", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_gift_suggestions_user_id", table_name="gift_suggestions")
    op.drop_index("ix_gift_suggestions_contact_id", table_name="gift_suggestions")
    op.drop_table("gift_suggestions")
