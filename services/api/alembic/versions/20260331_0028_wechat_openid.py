"""add openid to users

Revision ID: 20260331_0028
Revises: 20260331_0027
Create Date: 2026-03-31
"""

from alembic import op
import sqlalchemy as sa


revision = "20260331_0028"
down_revision = "20260331_0027"


def upgrade():
    op.add_column("users", sa.Column("openid", sa.String(64), nullable=True))
    op.create_index("ix_users_openid", "users", ["openid"], unique=True)


def downgrade():
    op.drop_index("ix_users_openid", table_name="users")
    op.drop_column("users", "openid")
