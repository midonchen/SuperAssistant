from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from core.ai_pipeline import ai_pipeline
from core.auth_dep import require_bearer
from core.response import success
from core.schemas import ActionType, ParsedEntity
from core.store import store

router = APIRouter(prefix="/ai", tags=["ocr"])


class OcrParseRequest(BaseModel):
    image_urls: list[str]


class ConfirmRequest(BaseModel):
    session_id: str
    entities: list[ParsedEntity]


@router.post("/ocr/parse")
async def parse_ocr(payload: OcrParseRequest, request: Request, user_id: str = Depends(require_bearer)):
    result = ai_pipeline.parse_ocr(payload.image_urls)
    store.add_audit_task(result.session_id, result.entities)
    return success(
        request,
        {
            "session_id": result.session_id,
            "entities": [entity.model_dump(mode="json") for entity in result.entities],
            "unknown_items": result.unknown_items,
        },
    )


@router.post("/parse/confirm")
async def confirm_parse(payload: ConfirmRequest, request: Request, user_id: str = Depends(require_bearer)):
    uid = UUID(user_id)
    for entity in payload.entities:
        store.apply_operation(uid, entity.item_key, entity.operation, entity.normalized_value, ActionType.MANUAL)

    items = store.list_items(uid)
    return success(
        request,
        {
            "inventory_snapshot": {
                "updated_count": len(payload.entities),
                "items": [item.model_dump(mode="json") for item in items],
            }
        },
    )
