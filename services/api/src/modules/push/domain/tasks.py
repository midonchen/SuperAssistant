from __future__ import annotations

from core.celery_app import celery_app
from core.store import store


@celery_app.task(name="modules.push.domain.tasks.run_purchase_reminder_task")
def run_purchase_reminder_task() -> dict:
    return store.run_purchase_reminders_for_all()
