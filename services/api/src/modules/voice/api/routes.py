from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from core.ai_pipeline import ai_pipeline
from core.auth_dep import require_bearer
from core.response import success
from core.store import store

router = APIRouter(prefix="/ai", tags=["voice"])


class VoiceParseRequest(BaseModel):
    audio_url: str
    locale: str


@router.post("/voice/parse")
async def parse_voice(payload: VoiceParseRequest, request: Request, user_id: str = Depends(require_bearer)):
    result = ai_pipeline.parse_voice(payload.audio_url, payload.locale)
    store.add_audit_task(result.session_id, result.entities)
    return success(
        request,
        {
            "session_id": result.session_id,
            "entities": [entity.model_dump(mode="json") for entity in result.entities],
            "confidence": result.confidence,
        },
    )
