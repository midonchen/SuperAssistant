from __future__ import annotations

import uuid

from sqlalchemy import select

from core.db import SessionLocal
from core.models import WorkReflectionModel
from core.schemas import WorkReflection, WorkReflectionCreateRequest
from core.store.base import StoreBase


class WorkReflectionStoreMixin(StoreBase):
    def _reflection(self, row: WorkReflectionModel) -> WorkReflection:
        return WorkReflection(
            reflection_id=row.id,
            title=row.title,
            content=row.content,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def create_work_reflection(self, user_id: str, request: WorkReflectionCreateRequest) -> WorkReflection:
        with SessionLocal() as db:
            row = WorkReflectionModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                title=request.title,
                content=request.content,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._reflection(row)

    def list_work_reflections(self, user_id: str) -> list[WorkReflection]:
        with SessionLocal() as db:
            rows = db.scalars(
                select(WorkReflectionModel)
                .where(WorkReflectionModel.user_id == user_id)
                .order_by(WorkReflectionModel.created_at.desc())
            ).all()
            return [self._reflection(r) for r in rows]

    def delete_work_reflection(self, user_id: str, reflection_id: str) -> None:
        with SessionLocal() as db:
            row = db.scalar(
                select(WorkReflectionModel).where(
                    WorkReflectionModel.id == reflection_id, WorkReflectionModel.user_id == user_id
                )
            )
            if row is None:
                raise KeyError("work reflection not found")
            db.delete(row)
            db.commit()
