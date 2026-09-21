from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from core.auth_dep import require_bearer
from core.response import failure, success
from core.schemas import HouseholdCreateRequest, HouseholdInviteRequest, HouseholdJoinRequest
from core.store import store

router = APIRouter(prefix="/households", tags=["households"])


@router.get("/me")
async def get_my_household(request: Request, user_id: str = Depends(require_bearer)):
    try:
        household = store.get_household(user_id)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "household not found")
    return success(request, {"household": household.model_dump(mode="json")})


@router.post("")
async def create_household(
    payload: HouseholdCreateRequest,
    request: Request,
    user_id: str = Depends(require_bearer),
):
    try:
        household = store.create_household(user_id, payload)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "user not found")
    return success(request, {"household": household.model_dump(mode="json")})


@router.post("/invitations")
async def create_invitation(
    payload: HouseholdInviteRequest,
    request: Request,
    user_id: str = Depends(require_bearer),
):
    try:
        invitation = store.create_invitation(user_id, role=payload.role)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "household not found")
    store.record_event(user_id, "invitation_created", {"role": payload.role}, invitation.household_id)
    return success(request, {"invitation": invitation.model_dump(mode="json")})


@router.post("/join")
async def join_household(
    payload: HouseholdJoinRequest,
    request: Request,
    user_id: str = Depends(require_bearer),
):
    try:
        household = store.join_household(user_id, payload.invite_code)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "user not found")
    store.record_event(user_id, "household_joined", {"household_id": household.household_id}, household.household_id)
    return success(request, {"household": household.model_dump(mode="json")})
