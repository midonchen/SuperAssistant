from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select

from core.db import SessionLocal
from core.models import AnalyticsEventModel
from core.store.base import StoreBase


def _naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class AnalyticsStoreMixin(StoreBase):
    def record_event(
        self,
        user_id: str | None,
        event_type: str,
        payload: dict | None = None,
        household_id: str | None = None,
    ) -> None:
        with SessionLocal() as db:
            db.add(
                AnalyticsEventModel(
                    user_id=user_id,
                    household_id=household_id,
                    event_type=event_type,
                    payload=payload or {},
                )
            )
            db.commit()

    def analytics_snapshot(self, event_type: str | None = None, limit: int = 100) -> dict:
        with SessionLocal() as db:
            summary_rows = db.execute(
                select(AnalyticsEventModel.event_type, func.count())
                .group_by(AnalyticsEventModel.event_type)
            ).all()
            summary = {row[0]: int(row[1]) for row in summary_rows}

            stmt = select(AnalyticsEventModel).order_by(AnalyticsEventModel.created_at.desc()).limit(limit)
            if event_type:
                stmt = stmt.where(AnalyticsEventModel.event_type == event_type)
            rows = db.scalars(stmt).all()
            events = [
                {
                    "event_id": row.id,
                    "user_id": row.user_id,
                    "household_id": row.household_id,
                    "event_type": row.event_type,
                    "payload": row.payload,
                    "created_at": _naive_utc(row.created_at).isoformat(),
                }
                for row in rows
            ]
            return {"summary": summary, "list": events, "total": len(events)}
