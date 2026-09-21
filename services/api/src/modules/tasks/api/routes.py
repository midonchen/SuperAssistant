from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from core.auth_dep import require_bearer
from core.response import failure, success
from core.schemas import TaskCreateRequest, TaskUpdateRequest
from core.store import store

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("")
async def list_tasks(
    request: Request,
    user_id: str = Depends(require_bearer),
    status: str | None = Query(default=None),
):
    tasks = store.list_tasks(user_id, status=status)
    return success(request, {"tasks": [t.model_dump(mode="json") for t in tasks]})


@router.post("")
async def create_task(payload: TaskCreateRequest, request: Request, user_id: str = Depends(require_bearer)):
    task = store.create_task(user_id, payload)
    return success(request, {"task": task.model_dump(mode="json")})


@router.post("/prioritize")
async def prioritize_tasks(request: Request, user_id: str = Depends(require_bearer)):
    ranked = store.prioritize_tasks(user_id)
    return success(request, {"tasks": [t.model_dump(mode="json") for t in ranked]})


@router.patch("/{task_id}")
async def update_task(task_id: str, payload: TaskUpdateRequest, request: Request, user_id: str = Depends(require_bearer)):
    try:
        task = store.update_task(user_id, task_id, payload)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "task not found")
    return success(request, {"task": task.model_dump(mode="json")})


@router.delete("/{task_id}")
async def delete_task(task_id: str, request: Request, user_id: str = Depends(require_bearer)):
    try:
        store.delete_task(user_id, task_id)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "task not found")
    return success(request, {"deleted": True})
