from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from core.auth_dep import require_bearer
from core.response import failure, success
from core.schemas import FamilyAffairCreateRequest, FamilyAffairUpdateRequest
from core.store import store

router = APIRouter(prefix="/family-affairs", tags=["family-affairs"])


@router.get("")
async def list_family_affairs(request: Request, user_id: str = Depends(require_bearer)):
    affairs = store.list_family_affairs(user_id)
    return success(request, {"affairs": [a.model_dump(mode="json") for a in affairs]})


@router.post("")
async def create_family_affair(payload: FamilyAffairCreateRequest, request: Request, user_id: str = Depends(require_bearer)):
    affair = store.create_family_affair(user_id, payload)
    return success(request, {"affair": affair.model_dump(mode="json")})


@router.patch("/{affair_id}")
async def update_family_affair(affair_id: str, payload: FamilyAffairUpdateRequest, request: Request, user_id: str = Depends(require_bearer)):
    try:
        affair = store.update_family_affair(user_id, affair_id, payload)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "family affair not found")
    return success(request, {"affair": affair.model_dump(mode="json")})


@router.delete("/{affair_id}")
async def delete_family_affair(affair_id: str, request: Request, user_id: str = Depends(require_bearer)):
    try:
        store.delete_family_affair(user_id, affair_id)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "family affair not found")
    return success(request, {"deleted": True})
