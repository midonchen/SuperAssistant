from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from core.auth_dep import require_bearer
from core.response import failure, success
from core.schemas import ContactCreateRequest, ContactUpdateRequest, OccasionCreateRequest
from core.store import store

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("")
async def list_contacts(request: Request, user_id: str = Depends(require_bearer)):
    contacts = store.list_contacts(user_id)
    return success(request, {"contacts": [c.model_dump(mode="json") for c in contacts]})


@router.post("")
async def create_contact(payload: ContactCreateRequest, request: Request, user_id: str = Depends(require_bearer)):
    contact = store.create_contact(user_id, payload)
    return success(request, {"contact": contact.model_dump(mode="json")})


@router.get("/{contact_id}")
async def get_contact(contact_id: str, request: Request, user_id: str = Depends(require_bearer)):
    try:
        contact = store.get_contact(user_id, contact_id)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "contact not found")
    return success(request, {"contact": contact.model_dump(mode="json")})


@router.patch("/{contact_id}")
async def update_contact(contact_id: str, payload: ContactUpdateRequest, request: Request, user_id: str = Depends(require_bearer)):
    try:
        contact = store.update_contact(user_id, contact_id, payload)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "contact not found")
    return success(request, {"contact": contact.model_dump(mode="json")})


@router.delete("/{contact_id}")
async def delete_contact(contact_id: str, request: Request, user_id: str = Depends(require_bearer)):
    try:
        store.delete_contact(user_id, contact_id)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "contact not found")
    return success(request, {"deleted": True})


@router.post("/{contact_id}/occasions")
async def create_occasion(contact_id: str, payload: OccasionCreateRequest, request: Request, user_id: str = Depends(require_bearer)):
    try:
        occasion = store.create_occasion(user_id, contact_id, payload)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "contact not found")
    return success(request, {"occasion": occasion.model_dump(mode="json")})


@router.get("/{contact_id}/occasions")
async def list_occasions(contact_id: str, request: Request, user_id: str = Depends(require_bearer)):
    occasions = store.list_occasions(user_id, contact_id=contact_id)
    return success(request, {"occasions": [o.model_dump(mode="json") for o in occasions]})


@router.delete("/occasions/{occasion_id}")
async def delete_occasion(occasion_id: str, request: Request, user_id: str = Depends(require_bearer)):
    try:
        store.delete_occasion(user_id, occasion_id)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "occasion not found")
    return success(request, {"deleted": True})
