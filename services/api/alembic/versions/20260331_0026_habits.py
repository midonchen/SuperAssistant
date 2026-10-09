"""add habits, habit_checkins, workouts

Revision ID: 20260331_0026
Revises: 20260331_0025
Create Date: 2026-03-31
"""

from alembic import op
import sqlalchemy as sa


revision = "20260331_0026"
down_revision = "20260331_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "habits",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("schedule", sa.String(length=32), nullable=True),
        sa.Column("period_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_habits_user_id", "habits", ["user_id"], unique=False)

    op.create_table(
        "habit_checkins",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("habit_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("checkin_date", sa.String(length=10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("habit_id", "checkin_date", name="uq_habit_checkin"),
    )
    op.create_index("ix_habit_checkins_habit_id", "habit_checkins", ["habit_id"], unique=False)
    op.create_index("ix_habit_checkins_user_id", "habit_checkins", ["user_id"], unique=False)

    op.create_table(
        "workouts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("workout_type", sa.String(length=16), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("distance_km", sa.Float(), nullable=True),
        sa.Column("workout_date", sa.String(length=10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workouts_user_id", "workouts", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_workouts_user_id", table_name="workouts")
    op.drop_table("workouts")
    op.drop_index("ix_habit_checkins_user_id", table_name="habit_checkins")
    op.drop_index("ix_habit_checkins_habit_id", table_name="habit_checkins")
    op.drop_table("habit_checkins")
    op.drop_index("ix_habits_user_id", table_name="habits")
    op.drop_table("habits")
