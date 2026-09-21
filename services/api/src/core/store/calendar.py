from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from core.db import SessionLocal
from core.models import TaskModel
from core.schemas import CalendarEvent
from core.store.base import StoreBase


class CalendarStoreMixin(StoreBase):
    def list_calendar_events(self, user_id: str, start: datetime, end: datetime) -> list[CalendarEvent]:
        """Aggregate task deadlines (and later meetings) within [start, end) into a unified event list."""
        events: list[CalendarEvent] = []
        with SessionLocal() as db:
            stmt = (
                select(TaskModel)
                .where(
                    TaskModel.user_id == user_id,
                    TaskModel.due_at.isnot(None),
                    TaskModel.due_at >= start,
                    TaskModel.due_at < end,
                    TaskModel.status != "DONE",
                )
                .order_by(TaskModel.due_at.asc())
            )
            rows = db.scalars(stmt).all()
            for row in rows:
                if row.due_at is None:
                    continue
                events.append(
                    CalendarEvent(
                        event_id=f"task:{row.id}",
                        source="task",
                        title=row.title,
                        start_at=row.due_at,
                        end_at=None,
                        task_id=row.id,
                        status=row.status,
                        priority=row.priority,
                    )
                )
        return events
