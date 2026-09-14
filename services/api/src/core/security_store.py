from __future__ import annotations

from sqlalchemy import select

from core.db import SessionLocal
from core.models import SecurityEventModel


def query_security_events(
    user_id: str | None = None,
    event_type: str | None = None,
    limit: int = 50,
) -> list[dict]:
    with SessionLocal() as db:
        stmt = select(SecurityEventModel).order_by(SecurityEventModel.created_at.desc())
        if user_id:
            stmt = stmt.where(SecurityEventModel.user_id == user_id)
        if event_type:
            stmt = stmt.where(SecurityEventModel.event_type == event_type)
        rows = db.scalars(stmt.limit(limit)).all()
        return [
            {
                "event_id": row.id,
                "user_id": row.user_id,
                "event_type": row.event_type,
                "details": row.details,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ]
