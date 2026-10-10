from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from core.auth_dep import require_bearer
from core.response import failure, success
from core.schemas import WorkReflectionCreateRequest
from core.store import store

router = APIRouter(prefix="/work-reflections", tags=["work"])


@router.get("")
async def list_reflections(request: Request, user_id: str = Depends(require_bearer)):
    return success(request, {"reflections": [r.model_dump(mode="json") for r in store.list_work_reflections(user_id)]})


@router.post("")
async def create_reflection(payload: WorkReflectionCreateRequest, request: Request, user_id: str = Depends(require_bearer)):
    reflection = store.create_work_reflection(user_id, payload)
    return success(request, {"reflection": reflection.model_dump(mode="json")})


@router.delete("/{reflection_id}")
async def delete_reflection(reflection_id: str, request: Request, user_id: str = Depends(require_bearer)):
    try:
        store.delete_work_reflection(user_id, reflection_id)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "work reflection not found")
    return success(request, {"deleted": True})
