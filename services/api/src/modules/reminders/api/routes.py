from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from core.auth_dep import require_bearer
from core.response import failure, success
from core.schemas import (
    BillReminderCreateRequest,
    BillReminderUpdateRequest,
    HealthReminderCreateRequest,
    HealthReminderUpdateRequest,
)
from core.store import store

health_router = APIRouter(prefix="/health-reminders", tags=["health-reminders"])


@health_router.get("")
async def list_health_reminders(request: Request, user_id: str = Depends(require_bearer)):
    return success(request, {"reminders": [r.model_dump(mode="json") for r in store.list_health_reminders(user_id)]})


@health_router.post("")
async def create_health_reminder(payload: HealthReminderCreateRequest, request: Request, user_id: str = Depends(require_bearer)):
    reminder = store.create_health_reminder(user_id, payload)
    return success(request, {"reminder": reminder.model_dump(mode="json")})


@health_router.patch("/{reminder_id}")
async def update_health_reminder(reminder_id: str, payload: HealthReminderUpdateRequest, request: Request, user_id: str = Depends(require_bearer)):
    try:
        reminder = store.update_health_reminder(user_id, reminder_id, payload)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "health reminder not found")
    return success(request, {"reminder": reminder.model_dump(mode="json")})


@health_router.delete("/{reminder_id}")
async def delete_health_reminder(reminder_id: str, request: Request, user_id: str = Depends(require_bearer)):
    try:
        store.delete_health_reminder(user_id, reminder_id)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "health reminder not found")
    return success(request, {"deleted": True})


bills_router = APIRouter(prefix="/bill-reminders", tags=["bill-reminders"])


@bills_router.get("")
async def list_bill_reminders(request: Request, user_id: str = Depends(require_bearer)):
    return success(request, {"reminders": [r.model_dump(mode="json") for r in store.list_bill_reminders(user_id)]})


@bills_router.post("")
async def create_bill_reminder(payload: BillReminderCreateRequest, request: Request, user_id: str = Depends(require_bearer)):
    reminder = store.create_bill_reminder(user_id, payload)
    return success(request, {"reminder": reminder.model_dump(mode="json")})


@bills_router.patch("/{reminder_id}")
async def update_bill_reminder(reminder_id: str, payload: BillReminderUpdateRequest, request: Request, user_id: str = Depends(require_bearer)):
    try:
        reminder = store.update_bill_reminder(user_id, reminder_id, payload)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "bill reminder not found")
    return success(request, {"reminder": reminder.model_dump(mode="json")})


@bills_router.delete("/{reminder_id}")
async def delete_bill_reminder(reminder_id: str, request: Request, user_id: str = Depends(require_bearer)):
    try:
        store.delete_bill_reminder(user_id, reminder_id)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "bill reminder not found")
    return success(request, {"deleted": True})
