from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from core.auth_dep import require_bearer
from core.response import failure, success
from core.schemas import JournalEntryCreateRequest, LifeGoalCreateRequest, LifeGoalUpdateRequest
from core.store import store

journal_router = APIRouter(prefix="/journal", tags=["growth"])
life_goals_router = APIRouter(prefix="/life-goals", tags=["growth"])


@journal_router.get("")
async def list_journal(request: Request, user_id: str = Depends(require_bearer)):
    return success(request, {"entries": [e.model_dump(mode="json") for e in store.list_journal_entries(user_id)]})


@journal_router.post("")
async def create_journal(payload: JournalEntryCreateRequest, request: Request, user_id: str = Depends(require_bearer)):
    entry = store.create_journal_entry(user_id, payload)
    return success(request, {"entry": entry.model_dump(mode="json")})


@journal_router.delete("/{entry_id}")
async def delete_journal(entry_id: str, request: Request, user_id: str = Depends(require_bearer)):
    try:
        store.delete_journal_entry(user_id, entry_id)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "journal entry not found")
    return success(request, {"deleted": True})


@life_goals_router.get("")
async def list_life_goals(request: Request, user_id: str = Depends(require_bearer)):
    return success(request, {"goals": [g.model_dump(mode="json") for g in store.list_life_goals(user_id)]})


@life_goals_router.post("")
async def create_life_goal(payload: LifeGoalCreateRequest, request: Request, user_id: str = Depends(require_bearer)):
    goal = store.create_life_goal(user_id, payload)
    return success(request, {"goal": goal.model_dump(mode="json")})


@life_goals_router.patch("/{goal_id}")
async def update_life_goal(goal_id: str, payload: LifeGoalUpdateRequest, request: Request, user_id: str = Depends(require_bearer)):
    try:
        goal = store.update_life_goal(user_id, goal_id, payload)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "life goal not found")
    return success(request, {"goal": goal.model_dump(mode="json")})


@life_goals_router.delete("/{goal_id}")
async def delete_life_goal(goal_id: str, request: Request, user_id: str = Depends(require_bearer)):
    try:
        store.delete_life_goal(user_id, goal_id)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "life goal not found")
    return success(request, {"deleted": True})
