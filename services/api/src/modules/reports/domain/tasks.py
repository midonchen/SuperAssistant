from __future__ import annotations

from datetime import datetime, timezone

from core.celery_app import celery_app
from core.store import store


def _previous_month() -> str:
    now = datetime.now(timezone.utc)
    if now.month == 1:
        return f"{now.year - 1:04d}-12"
    return f"{now.year:04d}-{now.month - 1:02d}"


@celery_app.task(name="modules.reports.domain.tasks.run_monthly_report_task")
def run_monthly_report_task() -> dict:
    return store.generate_reports_for_all(_previous_month())
