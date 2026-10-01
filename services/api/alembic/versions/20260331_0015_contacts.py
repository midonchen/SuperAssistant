"""add contacts and occasions

Revision ID: 20260331_0015
Revises: 20260331_0014
Create Date: 2026-03-31
"""

from alembic import op
import sqlalchemy as sa


revision = "20260331_0015"
down_revision = "20260331_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contacts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("relationship", sa.String(length=32), nullable=True),
        sa.Column("birthday", sa.String(length=10), nullable=True),
        sa.Column("preferences", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_contacts_user_id", "contacts", ["user_id"], unique=False)

    op.create_table(
        "occasions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("contact_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("day", sa.Integer(), nullable=False),
        sa.Column("is_lunar", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("remind_days_before", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_occasions_contact_id", "occasions", ["contact_id"], unique=False)
    op.create_index("ix_occasions_user_id", "occasions", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_occasions_user_id", table_name="occasions")
    op.drop_index("ix_occasions_contact_id", table_name="occasions")
    op.drop_table("occasions")
    op.drop_index("ix_contacts_user_id", table_name="contacts")
    op.drop_table("contacts")
