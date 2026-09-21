from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from core.auth_dep import require_bearer
from core.errors import ApiException
from core.response import failure, success
from core.schemas import ActionType, Operation
from core.store import store

router = APIRouter(prefix="/inventory", tags=["inventory"])


def _current_household_id(user_id: str) -> str:
    household_id = store.get_user_household_id(user_id)
    if household_id is None:
        raise ApiException(403, "AUTH_403_FORBIDDEN", "user has no household")
    return household_id


class BatchOperation(BaseModel):
    item_key: str
    operation: Operation
    value: float
    unit: str
    source: ActionType
    op_id: str | None = None
    client_version: int | None = None


class BatchOperationsRequest(BaseModel):
    operations: list[BatchOperation]


class OfflineReplayOp(BaseModel):
    op_id: str
    created_at: str | None = None
    endpoint: str = "/inventory/operations/batch"
    payload: BatchOperationsRequest
    retry_count: int = 0


class OfflineReplayRequest(BaseModel):
    offline_ops: list[OfflineReplayOp]


class CalibrateRequest(BaseModel):
    value: float
    unit: str


@router.get("/items")
async def list_items(request: Request, user_id: str = Depends(require_bearer), status: str | None = Query(default=None)):
    household_id = _current_household_id(user_id)
    items = store.list_items(household_id, status=status)
    return success(request, {"items": [item.model_dump(mode="json") for item in items]})


@router.post("/operations/batch")
async def batch_ops(payload: BatchOperationsRequest, request: Request, user_id: str = Depends(require_bearer)):
    household_id = _current_household_id(user_id)
    if not store.can_write_inventory(user_id, household_id):
        return failure(request, 403, "AUTH_403_FORBIDDEN", "insufficient household role")
    result = store.apply_batch_operations(household_id, UUID(user_id), [op.model_dump(mode="json") for op in payload.operations])
    return success(request, result)


@router.get("/logs")
async def list_logs(
    request: Request,
    user_id: str = Depends(require_bearer),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    item_key: str | None = Query(default=None),
):
    household_id = _current_household_id(user_id)
    rows, total = store.list_logs(household_id, page=page, page_size=page_size, item_key=item_key)
    return success(
        request,
        {
            "list": [log.model_dump(mode="json") for log in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    )


@router.post("/items/{item_key}/calibrate")
async def calibrate(item_key: str, payload: CalibrateRequest, request: Request, user_id: str = Depends(require_bearer)):
    household_id = _current_household_id(user_id)
    if not store.can_write_inventory(user_id, household_id):
        return failure(request, 403, "AUTH_403_FORBIDDEN", "insufficient household role")
    store.apply_operation(household_id, UUID(user_id), item_key, Operation.SET, payload.value, ActionType.CALIBRATE)
    item = store.get_item(household_id, item_key)
    return success(request, {"item": item.model_dump(mode="json")})


@router.post("/offline/replay")
async def offline_replay(payload: OfflineReplayRequest, request: Request, user_id: str = Depends(require_bearer)):
    household_id = _current_household_id(user_id)
    if not store.can_write_inventory(user_id, household_id):
        return failure(request, 403, "AUTH_403_FORBIDDEN", "insufficient household role")
    result = store.enqueue_offline_replay_ops(household_id, UUID(user_id), [op.model_dump(mode="json") for op in payload.offline_ops])
    return success(request, result)
