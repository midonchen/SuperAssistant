from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from core.auth_dep import require_bearer
from core.response import failure, success
from core.schemas import KnowledgeEntryCreateRequest, KnowledgeEntryUpdateRequest
from core.store import store

thinking_models_router = APIRouter(prefix="/thinking-models", tags=["knowledge"])
value_principles_router = APIRouter(prefix="/value-principles", tags=["knowledge"])


def _list(kind: str, request: Request, user_id: str):
    return success(request, {"entries": [e.model_dump(mode="json") for e in store.list_entries(user_id, kind)]})


@thinking_models_router.get("")
async def list_thinking_models(request: Request, user_id: str = Depends(require_bearer)):
    return _list("thinking_model", request, user_id)


@thinking_models_router.post("")
async def create_thinking_model(payload: KnowledgeEntryCreateRequest, request: Request, user_id: str = Depends(require_bearer)):
    payload.kind = "thinking_model"
    entry = store.create_entry(user_id, payload)
    return success(request, {"entry": entry.model_dump(mode="json")})


@thinking_models_router.patch("/{entry_id}")
async def update_thinking_model(entry_id: str, payload: KnowledgeEntryUpdateRequest, request: Request, user_id: str = Depends(require_bearer)):
    try:
        entry = store.update_entry(user_id, entry_id, payload)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "knowledge entry not found")
    return success(request, {"entry": entry.model_dump(mode="json")})


@thinking_models_router.delete("/{entry_id}")
async def delete_thinking_model(entry_id: str, request: Request, user_id: str = Depends(require_bearer)):
    try:
        store.delete_entry(user_id, entry_id)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "knowledge entry not found")
    return success(request, {"deleted": True})


@value_principles_router.get("")
async def list_value_principles(request: Request, user_id: str = Depends(require_bearer)):
    return _list("value_principle", request, user_id)


@value_principles_router.post("")
async def create_value_principle(payload: KnowledgeEntryCreateRequest, request: Request, user_id: str = Depends(require_bearer)):
    payload.kind = "value_principle"
    entry = store.create_entry(user_id, payload)
    return success(request, {"entry": entry.model_dump(mode="json")})


@value_principles_router.patch("/{entry_id}")
async def update_value_principle(entry_id: str, payload: KnowledgeEntryUpdateRequest, request: Request, user_id: str = Depends(require_bearer)):
    try:
        entry = store.update_entry(user_id, entry_id, payload)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "knowledge entry not found")
    return success(request, {"entry": entry.model_dump(mode="json")})


@value_principles_router.delete("/{entry_id}")
async def delete_value_principle(entry_id: str, request: Request, user_id: str = Depends(require_bearer)):
    try:
        store.delete_entry(user_id, entry_id)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "knowledge entry not found")
    return success(request, {"deleted": True})
