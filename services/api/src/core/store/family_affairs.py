from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select

from core.db import SessionLocal
from core.errors import ApiException
from core.models import FamilyAffairModel
from core.schemas import CalendarEvent, FamilyAffair, FamilyAffairCreateRequest, FamilyAffairUpdateRequest, utc_now
from core.store.base import StoreBase


class FamilyAffairStoreMixin(StoreBase):
    def _affair(self, row: FamilyAffairModel) -> FamilyAffair:
        return FamilyAffair(
            affair_id=row.id,
            household_id=row.household_id,
            title=row.title,
            due_at=row.due_at,
            assignee=row.assignee,
            status=row.status,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _require_write(self, user_id: str, household_id: str | None) -> str:
        if household_id is None:
            raise ApiException(403, "AUTH_403_FORBIDDEN", "user has no household")
        if not self.can_write_inventory(user_id, household_id):
            raise ApiException(403, "AUTH_403_FORBIDDEN", "insufficient household role")
        return household_id

    def create_family_affair(self, user_id: str, request: FamilyAffairCreateRequest) -> FamilyAffair:
        household_id = self._require_write(user_id, self.get_user_household_id(user_id))
        with SessionLocal() as db:
            row = FamilyAffairModel(
                id=str(uuid.uuid4()),
                household_id=household_id,
                user_id=user_id,
                title=request.title,
                due_at=request.due_at,
                assignee=request.assignee,
                status="TODO",
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._affair(row)

    def list_family_affairs(self, user_id: str) -> list[FamilyAffair]:
        household_id = self.get_user_household_id(user_id)
        if household_id is None:
            return []
        with SessionLocal() as db:
            rows = db.scalars(
                select(FamilyAffairModel)
                .where(FamilyAffairModel.household_id == household_id)
                .order_by(FamilyAffairModel.created_at.desc())
            ).all()
            return [self._affair(r) for r in rows]

    def update_family_affair(self, user_id: str, affair_id: str, request: FamilyAffairUpdateRequest) -> FamilyAffair:
        household_id = self._require_write(user_id, self.get_user_household_id(user_id))
        with SessionLocal() as db:
            row = db.scalar(select(FamilyAffairModel).where(FamilyAffairModel.id == affair_id, FamilyAffairModel.household_id == household_id))
            if row is None:
                raise KeyError("family affair not found")
            if request.title is not None:
                row.title = request.title
            if request.due_at is not None:
                row.due_at = request.due_at
            if request.assignee is not None:
                row.assignee = request.assignee
            if request.status is not None:
                if request.status not in {"TODO", "IN_PROGRESS", "DONE"}:
                    raise ApiException(400, "VAL_400_INVALID_PARAM", "invalid affair status")
                row.status = request.status
            row.updated_at = utc_now()
            db.commit()
            db.refresh(row)
            return self._affair(row)

    def delete_family_affair(self, user_id: str, affair_id: str) -> None:
        household_id = self._require_write(user_id, self.get_user_household_id(user_id))
        with SessionLocal() as db:
            row = db.scalar(select(FamilyAffairModel).where(FamilyAffairModel.id == affair_id, FamilyAffairModel.household_id == household_id))
            if row is None:
                raise KeyError("family affair not found")
            db.delete(row)
            db.commit()

    def family_affair_events(self, user_id: str, start: datetime, end: datetime) -> list[CalendarEvent]:
        household_id = self.get_user_household_id(user_id)
        if household_id is None:
            return []
        with SessionLocal() as db:
            rows = db.scalars(
                select(FamilyAffairModel).where(
                    FamilyAffairModel.household_id == household_id,
                    FamilyAffairModel.due_at.isnot(None),
                    FamilyAffairModel.due_at >= start,
                    FamilyAffairModel.due_at < end,
                    FamilyAffairModel.status != "DONE",
                )
            ).all()
            events: list[CalendarEvent] = []
            for r in rows:
                if r.due_at is None:
                    continue
                events.append(
                    CalendarEvent(
                        event_id=f"family:{r.id}",
                        source="family",
                        title=r.title,
                        start_at=r.due_at,
                        end_at=None,
                        task_id=None,
                        meeting_id=None,
                        status=r.status,
                        priority=None,
                    )
                )
            return events
