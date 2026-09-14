from __future__ import annotations

from core.celery_app import celery_app
from core.store import store


@celery_app.task(name="modules.inventory.domain.tasks.run_daily_auto_decay_task")
def run_daily_auto_decay_task() -> dict:
    return store.run_auto_decay_for_all()


@celery_app.task(name="modules.inventory.domain.tasks.run_offline_replay_queue_task")
def run_offline_replay_queue_task() -> dict:
    return store.process_offline_replay_queue(max_jobs=100)
