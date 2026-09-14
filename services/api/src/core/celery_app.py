from __future__ import annotations

import os

from celery import Celery
from celery.schedules import crontab

BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

celery_app = Celery("superassistant", broker=BROKER_URL, backend=RESULT_BACKEND)

celery_app.conf.update(
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
)

celery_app.conf.beat_schedule = {
    "daily-auto-decay": {
        "task": "modules.inventory.domain.tasks.run_daily_auto_decay_task",
        "schedule": crontab(minute=5, hour=0),
    },
    "offline-replay-every-minute": {
        "task": "modules.inventory.domain.tasks.run_offline_replay_queue_task",
        "schedule": crontab(minute="*"),
    },
    "daily-purchase-reminder": {
        "task": "modules.push.domain.tasks.run_purchase_reminder_task",
        "schedule": crontab(minute=0, hour=20),
    },
}

celery_app.autodiscover_tasks(["modules.inventory.domain", "modules.push.domain"])
