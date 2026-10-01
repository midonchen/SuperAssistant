from __future__ import annotations

from core.celery_app import celery_app
from core.store import store


@celery_app.task(name="modules.contacts.domain.tasks.run_occasion_reminder_task")
def run_occasion_reminder_task() -> dict:
    return store.run_occasion_reminders_for_all()
