from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy import delete, select

from core.db import SessionLocal
from core.errors import ApiException
from core.models import HabitCheckinModel, HabitModel, WorkoutModel
from core.schemas import (
    Habit,
    HabitCheckin,
    HabitCreateRequest,
    Workout,
    WorkoutCreateRequest,
)
from core.store.base import StoreBase


def _streak(db, habit_id: str) -> int:
    dates = db.scalars(
        select(HabitCheckinModel.checkin_date).where(HabitCheckinModel.habit_id == habit_id)
    ).all()
    if not dates:
        return 0
    ds = sorted(set(dates), reverse=True)
    today = date.today()
    cursor = today if ds[0] == today.isoformat() else today - timedelta(days=1)
    streak = 0
    for d in ds:
        if d == cursor.isoformat():
            streak += 1
            cursor -= timedelta(days=1)
        else:
            break
    return streak


class HabitStoreMixin(StoreBase):
    def _habit(self, db, row: HabitModel) -> Habit:
        return Habit(
            habit_id=row.id,
            name=row.name,
            schedule=row.schedule,
            period_days=row.period_days,
            streak=_streak(db, row.id),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def create_habit(self, user_id: str, request: HabitCreateRequest) -> Habit:
        with SessionLocal() as db:
            row = HabitModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                name=request.name,
                schedule=request.schedule,
                period_days=request.period_days,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._habit(db, row)

    def list_habits(self, user_id: str) -> list[Habit]:
        with SessionLocal() as db:
            rows = db.scalars(
                select(HabitModel).where(HabitModel.user_id == user_id).order_by(HabitModel.created_at.asc())
            ).all()
            return [self._habit(db, r) for r in rows]

    def delete_habit(self, user_id: str, habit_id: str) -> None:
        with SessionLocal() as db:
            row = db.scalar(select(HabitModel).where(HabitModel.id == habit_id, HabitModel.user_id == user_id))
            if row is None:
                raise KeyError("habit not found")
            db.execute(delete(HabitCheckinModel).where(HabitCheckinModel.habit_id == habit_id))
            db.delete(row)
            db.commit()

    def checkin(self, user_id: str, habit_id: str, checkin_date: str) -> dict:
        with SessionLocal() as db:
            habit = db.scalar(select(HabitModel).where(HabitModel.id == habit_id, HabitModel.user_id == user_id))
            if habit is None:
                raise KeyError("habit not found")
            existing = db.scalar(
                select(HabitCheckinModel).where(
                    HabitCheckinModel.habit_id == habit_id,
                    HabitCheckinModel.checkin_date == checkin_date,
                )
            )
            if existing is None:
                existing = HabitCheckinModel(
                    id=str(uuid.uuid4()), habit_id=habit_id, user_id=user_id, checkin_date=checkin_date
                )
                db.add(existing)
                db.commit()
                db.refresh(existing)
            streak = _streak(db, habit_id)
            checkin = HabitCheckin(
                checkin_id=existing.id,
                habit_id=habit_id,
                checkin_date=checkin_date,
                created_at=existing.created_at,
            )
            return {"checkin": checkin.model_dump(mode="json"), "streak": streak}


class WorkoutStoreMixin(StoreBase):
    def _workout(self, row: WorkoutModel) -> Workout:
        return Workout(
            workout_id=row.id,
            workout_type=row.workout_type,
            duration_minutes=row.duration_minutes,
            distance_km=row.distance_km,
            workout_date=row.workout_date,
            created_at=row.created_at,
        )

    def create_workout(self, user_id: str, request: WorkoutCreateRequest) -> Workout:
        if request.workout_type not in {"run", "strength", "tennis"}:
            raise ApiException(400, "VAL_400_INVALID_PARAM", "invalid workout type")
        with SessionLocal() as db:
            row = WorkoutModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                workout_type=request.workout_type,
                duration_minutes=request.duration_minutes,
                distance_km=request.distance_km,
                workout_date=request.workout_date,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._workout(row)

    def list_workouts(self, user_id: str) -> list[Workout]:
        with SessionLocal() as db:
            rows = db.scalars(
                select(WorkoutModel).where(WorkoutModel.user_id == user_id).order_by(WorkoutModel.workout_date.desc())
            ).all()
            return [self._workout(r) for r in rows]

    def delete_workout(self, user_id: str, workout_id: str) -> None:
        with SessionLocal() as db:
            row = db.scalar(select(WorkoutModel).where(WorkoutModel.id == workout_id, WorkoutModel.user_id == user_id))
            if row is None:
                raise KeyError("workout not found")
            db.delete(row)
            db.commit()
