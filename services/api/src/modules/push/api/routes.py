from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from core.auth_dep import require_bearer
from core.errors import ApiException
from core.response import failure, success
from core.store import store

router = APIRouter(prefix="", tags=["push"])


def _current_household_id(user_id: str) -> str:
    household_id = store.get_user_household_id(user_id)
    if household_id is None:
        raise ApiException(403, "AUTH_403_FORBIDDEN", "user has no household")
    return household_id


class SuggestionRequest(BaseModel):
    mode: str


class RegisterDeviceRequest(BaseModel):
    platform: str
    device_token: str


class PushPreferenceRequest(BaseModel):
    enabled: bool
    notify_time: str


@router.post("/suggestions/generate")
async def generate_suggestion(payload: SuggestionRequest, request: Request, user_id: str = Depends(require_bearer)):
    household_id = _current_household_id(user_id)
    if not store.can_write_inventory(user_id, household_id):
        return failure(request, 403, "AUTH_403_FORBIDDEN", "insufficient household role")
    suggestion = store.build_suggestion(household_id, UUID(user_id), mode=payload.mode)
    return success(request, {"suggestion_id": str(suggestion.suggestion_id), "items": [x.model_dump(mode="json") for x in suggestion.items]})


@router.get("/suggestions/latest")
async def latest_suggestion(request: Request, user_id: str = Depends(require_bearer)):
    household_id = _current_household_id(user_id)
    suggestion = store.get_latest_suggestion(household_id)
    if not suggestion:
        if not store.can_write_inventory(user_id, household_id):
            return failure(request, 403, "AUTH_403_FORBIDDEN", "insufficient household role")
        suggestion = store.build_suggestion(household_id, UUID(user_id), mode="AUTO")
    return success(request, {"suggestion": suggestion.model_dump(mode="json")})


@router.post("/push/device/register")
async def register_device(payload: RegisterDeviceRequest, request: Request, user_id: str = Depends(require_bearer)):
    uid = UUID(user_id)
    registered = store.register_push_device(uid, payload.platform, payload.device_token)
    return success(request, {"registered": registered})


@router.put("/push/preference")
async def update_preference(payload: PushPreferenceRequest, request: Request, user_id: str = Depends(require_bearer)):
    uid = UUID(user_id)
    preference = store.upsert_push_preference(uid, payload.enabled, payload.notify_time)
    return success(
        request,
        {
            "preference": preference
        },
    )
