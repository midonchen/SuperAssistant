from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from core.db import SessionLocal
from core.models import MeetingModel, TaskModel
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
            mstmt = (
                select(MeetingModel)
                .where(
                    MeetingModel.user_id == user_id,
                    MeetingModel.started_at >= start,
                    MeetingModel.started_at < end,
                )
                .order_by(MeetingModel.started_at.asc())
            )
            for row in db.scalars(mstmt).all():
                events.append(
                    CalendarEvent(
                        event_id=f"meeting:{row.id}",
                        source="meeting",
                        title=row.title,
                        start_at=row.started_at,
                        end_at=row.ended_at,
                        task_id=None,
                        meeting_id=row.id,
                        status=None,
                        priority=None,
                    )
                )
        events.sort(key=lambda e: e.start_at)
        return events
