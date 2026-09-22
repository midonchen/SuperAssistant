from __future__ import annotations

from datetime import datetime, timezone

from core.schemas import CalendarEvent


def _fmt(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def build_ical(events: list[CalendarEvent], now: datetime) -> str:
    """Render calendar events as an RFC 5545 iCalendar (.ics) feed."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//SuperAssistant//Calendar//CN",
        "CALSCALE:GREGORIAN",
    ]
    for e in events:
        lines += [
            "BEGIN:VEVENT",
            f"UID:{e.event_id}@superassistant",
            f"DTSTAMP:{_fmt(now)}",
            f"DTSTART:{_fmt(e.start_at)}",
        ]
        if e.end_at is not None:
            lines.append(f"DTEND:{_fmt(e.end_at)}")
        lines += [f"SUMMARY:{_escape(e.title)}", "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)
