from __future__ import annotations

import uuid

from sqlalchemy import select

from core.db import SessionLocal
from core.errors import ApiException
from core.models import JournalEntryModel, LifeGoalModel
from core.schemas import (
    JournalEntry,
    JournalEntryCreateRequest,
    LifeGoal,
    LifeGoalCreateRequest,
    LifeGoalUpdateRequest,
    utc_now,
)
from core.store.base import StoreBase


class JournalStoreMixin(StoreBase):
    def _journal(self, row: JournalEntryModel) -> JournalEntry:
        return JournalEntry(
            entry_id=row.id,
            content=row.content,
            mood=row.mood,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def create_journal_entry(self, user_id: str, request: JournalEntryCreateRequest) -> JournalEntry:
        with SessionLocal() as db:
            row = JournalEntryModel(id=str(uuid.uuid4()), user_id=user_id, content=request.content, mood=request.mood)
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._journal(row)

    def list_journal_entries(self, user_id: str) -> list[JournalEntry]:
        with SessionLocal() as db:
            rows = db.scalars(
                select(JournalEntryModel)
                .where(JournalEntryModel.user_id == user_id)
                .order_by(JournalEntryModel.created_at.desc())
            ).all()
            return [self._journal(r) for r in rows]

    def delete_journal_entry(self, user_id: str, entry_id: str) -> None:
        with SessionLocal() as db:
            row = db.scalar(
                select(JournalEntryModel).where(
                    JournalEntryModel.id == entry_id, JournalEntryModel.user_id == user_id
                )
            )
            if row is None:
                raise KeyError("journal entry not found")
            db.delete(row)
            db.commit()


class LifeGoalStoreMixin(StoreBase):
    def _life_goal(self, row: LifeGoalModel) -> LifeGoal:
        return LifeGoal(
            goal_id=row.id,
            dimension=row.dimension,
            title=row.title,
            description=row.description,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def create_life_goal(self, user_id: str, request: LifeGoalCreateRequest) -> LifeGoal:
        if request.dimension not in {"career", "health", "family", "wealth"}:
            raise ApiException(400, "VAL_400_INVALID_PARAM", "invalid dimension")
        with SessionLocal() as db:
            row = LifeGoalModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                dimension=request.dimension,
                title=request.title,
                description=request.description,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._life_goal(row)

    def list_life_goals(self, user_id: str) -> list[LifeGoal]:
        with SessionLocal() as db:
            rows = db.scalars(
                select(LifeGoalModel).where(LifeGoalModel.user_id == user_id).order_by(LifeGoalModel.created_at.asc())
            ).all()
            return [self._life_goal(r) for r in rows]

    def update_life_goal(self, user_id: str, goal_id: str, request: LifeGoalUpdateRequest) -> LifeGoal:
        with SessionLocal() as db:
            row = db.scalar(
                select(LifeGoalModel).where(LifeGoalModel.id == goal_id, LifeGoalModel.user_id == user_id)
            )
            if row is None:
                raise KeyError("life goal not found")
            if request.dimension is not None:
                if request.dimension not in {"career", "health", "family", "wealth"}:
                    raise ApiException(400, "VAL_400_INVALID_PARAM", "invalid dimension")
                row.dimension = request.dimension
            if request.title is not None:
                row.title = request.title
            if request.description is not None:
                row.description = request.description
            row.updated_at = utc_now()
            db.commit()
            db.refresh(row)
            return self._life_goal(row)

    def delete_life_goal(self, user_id: str, goal_id: str) -> None:
        with SessionLocal() as db:
            row = db.scalar(
                select(LifeGoalModel).where(LifeGoalModel.id == goal_id, LifeGoalModel.user_id == user_id)
            )
            if row is None:
                raise KeyError("life goal not found")
            db.delete(row)
            db.commit()
