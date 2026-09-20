from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request

from core.auth_dep import require_bearer
from core.response import failure, success
from core.schemas import CategoryCreateRequest, CategoryUpdateRequest
from core.store import store

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("")
async def list_categories(request: Request, user_id: str = Depends(require_bearer)):
    uid = UUID(user_id)
    categories = store.list_categories(uid)
    return success(request, {"categories": [category.model_dump(mode="json") for category in categories]})


@router.post("")
async def create_category(
    payload: CategoryCreateRequest,
    request: Request,
    user_id: str = Depends(require_bearer),
):
    uid = UUID(user_id)
    category = store.create_category(uid, payload)
    store.create_inventory_for_category(uid, category.category_id)
    return success(request, {"category": category.model_dump(mode="json")})


@router.patch("/{category_id}")
async def update_category(
    category_id: str,
    payload: CategoryUpdateRequest,
    request: Request,
    user_id: str = Depends(require_bearer),
):
    uid = UUID(user_id)
    try:
        category = store.update_category(uid, category_id, payload)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "category not found")
    return success(request, {"category": category.model_dump(mode="json")})


@router.delete("/{category_id}")
async def delete_category(
    category_id: str,
    request: Request,
    user_id: str = Depends(require_bearer),
):
    uid = UUID(user_id)
    try:
        store.delete_category(uid, category_id)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "category not found")
    return success(request, {"deleted": True})
