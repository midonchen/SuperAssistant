from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request

from core.auth_dep import require_bearer
from core.errors import ApiException
from core.response import failure, success
from core.schemas import CategoryCreateRequest, CategoryUpdateRequest
from core.store import store

router = APIRouter(prefix="/categories", tags=["categories"])


def _current_household_id(user_id: str) -> str:
    household_id = store.get_user_household_id(user_id)
    if household_id is None:
        raise ApiException(403, "AUTH_403_FORBIDDEN", "user has no household")
    return household_id


@router.get("")
async def list_categories(request: Request, user_id: str = Depends(require_bearer)):
    household_id = _current_household_id(user_id)
    categories = store.list_categories(household_id)
    return success(request, {"categories": [category.model_dump(mode="json") for category in categories]})


@router.post("")
async def create_category(
    payload: CategoryCreateRequest,
    request: Request,
    user_id: str = Depends(require_bearer),
):
    household_id = _current_household_id(user_id)
    if not store.can_write_inventory(user_id, household_id):
        return failure(request, 403, "AUTH_403_FORBIDDEN", "insufficient household role")
    category = store.create_category(household_id, UUID(user_id), payload)
    store.create_inventory_for_category(household_id, UUID(user_id), category.category_id)
    store.record_event(user_id, "category_created", {"category_id": category.category_id, "name": category.name}, household_id)
    return success(request, {"category": category.model_dump(mode="json")})


@router.patch("/{category_id}")
async def update_category(
    category_id: str,
    payload: CategoryUpdateRequest,
    request: Request,
    user_id: str = Depends(require_bearer),
):
    household_id = _current_household_id(user_id)
    if not store.can_write_inventory(user_id, household_id):
        return failure(request, 403, "AUTH_403_FORBIDDEN", "insufficient household role")
    try:
        category = store.update_category(household_id, category_id, payload)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "category not found")
    return success(request, {"category": category.model_dump(mode="json")})


@router.delete("/{category_id}")
async def delete_category(
    category_id: str,
    request: Request,
    user_id: str = Depends(require_bearer),
):
    household_id = _current_household_id(user_id)
    if not store.can_write_inventory(user_id, household_id):
        return failure(request, 403, "AUTH_403_FORBIDDEN", "insufficient household role")
    try:
        store.delete_category(household_id, category_id)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "category not found")
    return success(request, {"deleted": True})
