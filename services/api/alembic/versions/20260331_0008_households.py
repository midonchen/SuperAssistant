"""add households, memberships, invitations and household_id isolation

Revision ID: 20260331_0008
Revises: 20260331_0007
Create Date: 2026-03-31
"""

from alembic import op
import sqlalchemy as sa


revision = "20260331_0008"
down_revision = "20260331_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "households",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "household_memberships",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("household_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False, server_default="MEMBER"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("household_id", "user_id", name="uq_household_membership"),
    )
    op.create_index("ix_household_memberships_household_id", "household_memberships", ["household_id"], unique=False)
    op.create_index("ix_household_memberships_user_id", "household_memberships", ["user_id"], unique=False)
    op.create_table(
        "household_invitations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("household_id", sa.String(length=36), nullable=False),
        sa.Column("inviter_id", sa.String(length=36), nullable=False),
        sa.Column("invite_code", sa.String(length=16), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False, server_default="MEMBER"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="PENDING"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invite_code"),
    )
    op.create_index("ix_household_invitations_household_id", "household_invitations", ["household_id"], unique=False)
    op.create_index("ix_household_invitations_invite_code", "household_invitations", ["invite_code"], unique=False)

    op.add_column("users", sa.Column("household_id", sa.String(length=36), nullable=True))
    op.create_index("ix_users_household_id", "users", ["household_id"], unique=False)

    op.add_column("categories", sa.Column("household_id", sa.String(length=36), nullable=True))
    op.create_index("ix_categories_household_id", "categories", ["household_id"], unique=False)
    with op.batch_alter_table("categories") as batch_op:
        batch_op.drop_constraint("uq_category_user_item_key", type_="unique")
        batch_op.create_unique_constraint("uq_category_household_item_key", ["household_id", "item_key"])

    op.add_column("inventory_items", sa.Column("household_id", sa.String(length=36), nullable=True))
    op.create_index("ix_inventory_items_household_id", "inventory_items", ["household_id"], unique=False)
    with op.batch_alter_table("inventory_items") as batch_op:
        batch_op.drop_constraint("uq_inventory_user_item", type_="unique")
        batch_op.create_unique_constraint("uq_inventory_household_item", ["household_id", "item_key"])

    op.add_column("activity_logs", sa.Column("household_id", sa.String(length=36), nullable=True))
    op.create_index("ix_activity_logs_household_id", "activity_logs", ["household_id"], unique=False)

    op.add_column("purchase_suggestions", sa.Column("household_id", sa.String(length=36), nullable=True))
    op.create_index("ix_purchase_suggestions_household_id", "purchase_suggestions", ["household_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_purchase_suggestions_household_id", table_name="purchase_suggestions")
    op.drop_column("purchase_suggestions", "household_id")

    op.drop_index("ix_activity_logs_household_id", table_name="activity_logs")
    op.drop_column("activity_logs", "household_id")

    with op.batch_alter_table("inventory_items") as batch_op:
        batch_op.drop_constraint("uq_inventory_household_item", type_="unique")
        batch_op.create_unique_constraint("uq_inventory_user_item", ["user_id", "item_key"])
    op.drop_index("ix_inventory_items_household_id", table_name="inventory_items")
    op.drop_column("inventory_items", "household_id")

    op.drop_index("ix_users_household_id", table_name="users")
    op.drop_column("users", "household_id")

    with op.batch_alter_table("categories") as batch_op:
        batch_op.drop_constraint("uq_category_household_item_key", type_="unique")
        batch_op.create_unique_constraint("uq_category_user_item_key", ["user_id", "item_key"])
    op.drop_index("ix_categories_household_id", table_name="categories")
    op.drop_column("categories", "household_id")

    op.drop_index("ix_household_invitations_invite_code", table_name="household_invitations")
    op.drop_index("ix_household_invitations_household_id", table_name="household_invitations")
    op.drop_table("household_invitations")
    op.drop_index("ix_household_memberships_user_id", table_name="household_memberships")
    op.drop_index("ix_household_memberships_household_id", table_name="household_memberships")
    op.drop_table("household_memberships")
    op.drop_table("households")
