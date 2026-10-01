"""add contact_interactions

Revision ID: 20260331_0016
Revises: 20260331_0015
Create Date: 2026-03-31
"""

from alembic import op
import sqlalchemy as sa


revision = "20260331_0016"
down_revision = "20260331_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contact_interactions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("contact_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column("interacted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_contact_interactions_contact_id", "contact_interactions", ["contact_id"], unique=False)
    op.create_index("ix_contact_interactions_user_id", "contact_interactions", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_contact_interactions_user_id", table_name="contact_interactions")
    op.drop_index("ix_contact_interactions_contact_id", table_name="contact_interactions")
    op.drop_table("contact_interactions")
