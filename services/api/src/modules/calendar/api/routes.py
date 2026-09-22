from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, Query, Request, Response

from core.auth_dep import require_bearer
from core.ical import build_ical
from core.response import success
from core.schemas import utc_now
from core.store import store

router = APIRouter(prefix="/calendar", tags=["calendar"])


def _next_month_start(d: date) -> date:
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return date(d.year, d.month + 1, 1)


@router.get("/events")
async def list_calendar_events(
    request: Request,
    user_id: str = Depends(require_bearer),
    start_date: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
):
    today = date.today()
    start = date.fromisoformat(start_date) if start_date else today.replace(day=1)
    end = date.fromisoformat(end_date) if end_date else _next_month_start(start)
    start_dt = datetime.combine(start, time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(end, time.min, tzinfo=timezone.utc)
    events = store.list_calendar_events(user_id, start_dt, end_dt)
    return success(request, {"events": [e.model_dump(mode="json") for e in events]})


@router.get("/ical")
async def export_ical(request: Request, user_id: str = Depends(require_bearer)):
    now = utc_now()
    start = now - timedelta(days=30)
    end = now + timedelta(days=365)
    events = store.list_calendar_events(user_id, start, end)
    ical = build_ical(events, now)
    return Response(
        content=ical,
        media_type="text/calendar",
        headers={"Content-Disposition": 'attachment; filename="calendar.ics"'},
    )
