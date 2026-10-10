from __future__ import annotations

import uuid

from sqlalchemy import delete, func, select

from core.db import SessionLocal
from core.errors import ApiException
from core.models import IdeaNoteModel, StartupIdeaModel
from core.schemas import (
    IdeaNote,
    IdeaNoteCreateRequest,
    StartupIdea,
    StartupIdeaCreateRequest,
    StartupIdeaUpdateRequest,
    utc_now,
)
from core.store.base import StoreBase

IDEA_STATUSES = {"idea", "research", "building", "launched", "paused", "dropped"}
NOTE_TYPES = {"thought", "summary", "milestone"}


class StartupIdeaStoreMixin(StoreBase):
    def _idea(self, row: StartupIdeaModel) -> StartupIdea:
        return StartupIdea(
            idea_id=row.id,
            title=row.title,
            description=row.description,
            status=row.status,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _note(self, row: IdeaNoteModel) -> IdeaNote:
        return IdeaNote(
            note_id=row.id,
            idea_id=row.idea_id,
            content=row.content,
            note_type=row.note_type,
            created_at=row.created_at,
        )

    def _count_ideas(self, user_id: str) -> int:
        with SessionLocal() as db:
            return (
                db.scalar(select(func.count()).select_from(StartupIdeaModel).where(StartupIdeaModel.user_id == user_id))
                or 0
            )

    def create_idea(self, user_id: str, request: StartupIdeaCreateRequest) -> StartupIdea:
        if not self.can_use_feature(user_id, "startup_ideas", self._count_ideas(user_id)):
            self.record_event(user_id, "subscription_gate_hit", {"feature": "startup_ideas"})
            raise ApiException(402, "BIZ_402_UPGRADE_REQUIRED", "free tier startup idea limit reached")
        with SessionLocal() as db:
            row = StartupIdeaModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                title=request.title,
                description=request.description,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._idea(row)

    def list_ideas(self, user_id: str) -> list[StartupIdea]:
        with SessionLocal() as db:
            rows = db.scalars(
                select(StartupIdeaModel)
                .where(StartupIdeaModel.user_id == user_id)
                .order_by(StartupIdeaModel.created_at.desc())
            ).all()
            return [self._idea(r) for r in rows]

    def update_idea(self, user_id: str, idea_id: str, request: StartupIdeaUpdateRequest) -> StartupIdea:
        with SessionLocal() as db:
            row = db.scalar(
                select(StartupIdeaModel).where(StartupIdeaModel.id == idea_id, StartupIdeaModel.user_id == user_id)
            )
            if row is None:
                raise KeyError("startup idea not found")
            if request.title is not None:
                row.title = request.title
            if request.description is not None:
                row.description = request.description
            if request.status is not None:
                if request.status not in IDEA_STATUSES:
                    raise ApiException(400, "VAL_400_INVALID_PARAM", "invalid idea status")
                row.status = request.status
            row.updated_at = utc_now()
            db.commit()
            db.refresh(row)
            return self._idea(row)

    def delete_idea(self, user_id: str, idea_id: str) -> None:
        with SessionLocal() as db:
            row = db.scalar(
                select(StartupIdeaModel).where(StartupIdeaModel.id == idea_id, StartupIdeaModel.user_id == user_id)
            )
            if row is None:
                raise KeyError("startup idea not found")
            db.execute(delete(IdeaNoteModel).where(IdeaNoteModel.idea_id == idea_id))
            db.delete(row)
            db.commit()

    def add_note(self, user_id: str, idea_id: str, request: IdeaNoteCreateRequest) -> IdeaNote:
        if request.note_type not in NOTE_TYPES:
            raise ApiException(400, "VAL_400_INVALID_PARAM", "invalid note type")
        with SessionLocal() as db:
            idea = db.scalar(
                select(StartupIdeaModel).where(StartupIdeaModel.id == idea_id, StartupIdeaModel.user_id == user_id)
            )
            if idea is None:
                raise KeyError("startup idea not found")
            row = IdeaNoteModel(
                id=str(uuid.uuid4()),
                idea_id=idea_id,
                user_id=user_id,
                content=request.content,
                note_type=request.note_type,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._note(row)

    def list_notes(self, user_id: str, idea_id: str) -> list[IdeaNote]:
        with SessionLocal() as db:
            rows = db.scalars(
                select(IdeaNoteModel)
                .where(IdeaNoteModel.idea_id == idea_id, IdeaNoteModel.user_id == user_id)
                .order_by(IdeaNoteModel.created_at.asc())
            ).all()
            return [self._note(r) for r in rows]

    def delete_note(self, user_id: str, note_id: str) -> None:
        with SessionLocal() as db:
            row = db.scalar(
                select(IdeaNoteModel).where(IdeaNoteModel.id == note_id, IdeaNoteModel.user_id == user_id)
            )
            if row is None:
                raise KeyError("idea note not found")
            db.delete(row)
            db.commit()
