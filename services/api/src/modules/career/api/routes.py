from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from core.auth_dep import require_bearer
from core.response import failure, success
from core.schemas import CareerGoalCreateRequest, CareerGoalUpdateRequest
from core.store import store

router = APIRouter(prefix="/career-goals", tags=["career-goals"])


@router.get("")
async def list_goals(request: Request, user_id: str = Depends(require_bearer)):
    return success(request, {"goals": [g.model_dump(mode="json") for g in store.list_goals(user_id)]})


@router.post("")
async def create_goal(payload: CareerGoalCreateRequest, request: Request, user_id: str = Depends(require_bearer)):
    goal = store.create_goal(user_id, payload)
    return success(request, {"goal": goal.model_dump(mode="json")})


@router.patch("/{goal_id}")
async def update_goal(goal_id: str, payload: CareerGoalUpdateRequest, request: Request, user_id: str = Depends(require_bearer)):
    try:
        goal = store.update_goal(user_id, goal_id, payload)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "career goal not found")
    return success(request, {"goal": goal.model_dump(mode="json")})


@router.delete("/{goal_id}")
async def delete_goal(goal_id: str, request: Request, user_id: str = Depends(require_bearer)):
    try:
        store.delete_goal(user_id, goal_id)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "career goal not found")
    return success(request, {"deleted": True})
