from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from core.auth_dep import require_bearer
from core.response import failure, success
from core.store import store

router = APIRouter(prefix="/weekly-reports", tags=["weekly-reports"])


@router.get("")
async def list_weekly_reports(request: Request, user_id: str = Depends(require_bearer)):
    reports = store.list_weekly_reports(user_id)
    return success(request, {"reports": [r.model_dump(mode="json") for r in reports]})


@router.post("/generate")
async def generate_weekly_report(
    request: Request,
    user_id: str = Depends(require_bearer),
    week_start: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
):
    report = store.generate_weekly_report(user_id, week_start)
    return success(request, {"report": report.model_dump(mode="json")})


@router.get("/{week_start}")
async def get_weekly_report(week_start: str, request: Request, user_id: str = Depends(require_bearer)):
    try:
        report = store.get_weekly_report(user_id, week_start)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "weekly report not found")
    return success(request, {"report": report.model_dump(mode="json")})
