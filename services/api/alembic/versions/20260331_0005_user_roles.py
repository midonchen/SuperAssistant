"""add role field to users for rbac

Revision ID: 20260331_0005
Revises: 20260331_0004
Create Date: 2026-03-31
"""

from alembic import op
import sqlalchemy as sa


revision = "20260331_0005"
down_revision = "20260331_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("role", sa.String(length=16), nullable=False, server_default="USER"))
    op.create_index("ix_users_role", "users", ["role"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_users_role", table_name="users")
    op.drop_column("users", "role")
