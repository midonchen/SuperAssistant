from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from core.auth_dep import require_bearer
from core.response import failure, success
from core.schemas import MeetingActionItemUpdateRequest, MeetingCreateRequest
from core.store import store

router = APIRouter(prefix="/meetings", tags=["meetings"])


@router.get("")
async def list_meetings(request: Request, user_id: str = Depends(require_bearer)):
    meetings = store.list_meetings(user_id)
    return success(request, {"meetings": [m.model_dump(mode="json") for m in meetings]})


@router.post("")
async def create_meeting(payload: MeetingCreateRequest, request: Request, user_id: str = Depends(require_bearer)):
    meeting = store.create_meeting(user_id, payload)
    return success(request, {"meeting": meeting.model_dump(mode="json")})


@router.get("/{meeting_id}")
async def get_meeting(meeting_id: str, request: Request, user_id: str = Depends(require_bearer)):
    try:
        meeting = store.get_meeting(user_id, meeting_id)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "meeting not found")
    return success(request, {"meeting": meeting.model_dump(mode="json")})


@router.patch("/action-items/{action_item_id}")
async def update_action_item(
    action_item_id: str,
    payload: MeetingActionItemUpdateRequest,
    request: Request,
    user_id: str = Depends(require_bearer),
):
    try:
        item = store.update_action_item(user_id, action_item_id, payload.done)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "action item not found")
    return success(request, {"action_item": item.model_dump(mode="json")})
