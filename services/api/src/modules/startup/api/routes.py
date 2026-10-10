from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from core.auth_dep import require_bearer
from core.response import failure, success
from core.schemas import IdeaNoteCreateRequest, StartupIdeaCreateRequest, StartupIdeaUpdateRequest
from core.store import store

router = APIRouter(prefix="/startup-ideas", tags=["startup"])


@router.get("")
async def list_ideas(request: Request, user_id: str = Depends(require_bearer)):
    return success(request, {"ideas": [i.model_dump(mode="json") for i in store.list_ideas(user_id)]})


@router.post("")
async def create_idea(payload: StartupIdeaCreateRequest, request: Request, user_id: str = Depends(require_bearer)):
    idea = store.create_idea(user_id, payload)
    return success(request, {"idea": idea.model_dump(mode="json")})


@router.patch("/{idea_id}")
async def update_idea(idea_id: str, payload: StartupIdeaUpdateRequest, request: Request, user_id: str = Depends(require_bearer)):
    try:
        idea = store.update_idea(user_id, idea_id, payload)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "startup idea not found")
    return success(request, {"idea": idea.model_dump(mode="json")})


@router.delete("/{idea_id}")
async def delete_idea(idea_id: str, request: Request, user_id: str = Depends(require_bearer)):
    try:
        store.delete_idea(user_id, idea_id)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "startup idea not found")
    return success(request, {"deleted": True})


@router.get("/{idea_id}/notes")
async def list_notes(idea_id: str, request: Request, user_id: str = Depends(require_bearer)):
    notes = store.list_notes(user_id, idea_id)
    return success(request, {"notes": [n.model_dump(mode="json") for n in notes]})


@router.post("/{idea_id}/notes")
async def add_note(idea_id: str, payload: IdeaNoteCreateRequest, request: Request, user_id: str = Depends(require_bearer)):
    try:
        note = store.add_note(user_id, idea_id, payload)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "startup idea not found")
    return success(request, {"note": note.model_dump(mode="json")})


@router.delete("/{idea_id}/notes/{note_id}")
async def delete_note(idea_id: str, note_id: str, request: Request, user_id: str = Depends(require_bearer)):
    try:
        store.delete_note(user_id, note_id)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "idea note not found")
    return success(request, {"deleted": True})
