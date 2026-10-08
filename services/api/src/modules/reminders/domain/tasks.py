from __future__ import annotations

from core.celery_app import celery_app
from core.store import store


@celery_app.task(name="modules.reminders.domain.tasks.run_health_reminder_task")
def run_health_reminder_task() -> dict:
    return store.run_health_reminders_for_all()


@celery_app.task(name="modules.reminders.domain.tasks.run_bill_reminder_task")
def run_bill_reminder_task() -> dict:
    return store.run_bill_reminders_for_all()
