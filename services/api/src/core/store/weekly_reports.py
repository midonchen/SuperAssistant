from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import or_, select

from core.ai_pipeline import ai_pipeline
from core.db import SessionLocal
from core.models import MeetingModel, TaskModel, WeeklyReportModel
from core.schemas import WeeklyReport, utc_now
from core.store.base import StoreBase


def _monday(dt: datetime) -> date:
    day = dt.date()
    return day - timedelta(days=day.weekday())


class WeeklyReportStoreMixin(StoreBase):
    def _weekly_report(self, row: WeeklyReportModel) -> WeeklyReport:
        return WeeklyReport(
            report_id=row.id,
            week_start=row.week_start,
            content=row.content,
            generated_at=row.generated_at,
        )

    def generate_weekly_report(self, user_id: str, week_start: str | None = None) -> WeeklyReport:
        start_date = date.fromisoformat(week_start) if week_start else _monday(utc_now())
        end_date = start_date + timedelta(days=7)
        start_dt = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
        end_dt = datetime.combine(end_date, time.min, tzinfo=timezone.utc)
        now = utc_now()

        with SessionLocal() as db:
            done_rows = db.scalars(
                select(TaskModel)
                .where(TaskModel.user_id == user_id, TaskModel.status == "DONE")
                .order_by(TaskModel.updated_at.desc())
                .limit(20)
            ).all()
            overdue_rows = db.scalars(
                select(TaskModel).where(
                    TaskModel.user_id == user_id,
                    TaskModel.status != "DONE",
                    TaskModel.due_at.isnot(None),
                    TaskModel.due_at < now,
                )
            ).all()
            pending_rows = db.scalars(
                select(TaskModel).where(
                    TaskModel.user_id == user_id,
                    TaskModel.status != "DONE",
                    or_(TaskModel.due_at.is_(None), TaskModel.due_at >= now),
                )
            ).all()
            meeting_rows = db.scalars(
                select(MeetingModel)
                .where(
                    MeetingModel.user_id == user_id,
                    MeetingModel.started_at >= start_dt,
                    MeetingModel.started_at < end_dt,
                )
                .order_by(MeetingModel.started_at.asc())
            ).all()

        def _due(t: TaskModel) -> str | None:
            return t.due_at.isoformat() if t.due_at else None

        tasks = (
            [{"title": t.title, "status": "已完成", "due_at": _due(t)} for t in done_rows]
            + [{"title": t.title, "status": "已逾期", "due_at": _due(t)} for t in overdue_rows]
            + [{"title": t.title, "status": "进行中", "due_at": _due(t)} for t in pending_rows]
        )
        meetings = [{"title": m.title, "summary": m.summary or ""} for m in meeting_rows]

        content = ai_pipeline.generate_weekly_report(start_date.isoformat(), tasks, meetings)

        with SessionLocal() as db:
            row = db.scalar(
                select(WeeklyReportModel).where(
                    WeeklyReportModel.user_id == user_id,
                    WeeklyReportModel.week_start == start_date.isoformat(),
                )
            )
            if row is None:
                row = WeeklyReportModel(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    week_start=start_date.isoformat(),
                    content=content,
                )
                db.add(row)
            else:
                row.content = content
                row.generated_at = utc_now()
            db.commit()
            db.refresh(row)
            return self._weekly_report(row)

    def get_weekly_report(self, user_id: str, week_start: str) -> WeeklyReport:
        with SessionLocal() as db:
            row = db.scalar(
                select(WeeklyReportModel).where(
                    WeeklyReportModel.user_id == user_id,
                    WeeklyReportModel.week_start == week_start,
                )
            )
            if row is None:
                raise KeyError("weekly report not found")
            return self._weekly_report(row)

    def list_weekly_reports(self, user_id: str) -> list[WeeklyReport]:
        with SessionLocal() as db:
            rows = db.scalars(
                select(WeeklyReportModel)
                .where(WeeklyReportModel.user_id == user_id)
                .order_by(WeeklyReportModel.week_start.desc())
            ).all()
            return [self._weekly_report(r) for r in rows]
