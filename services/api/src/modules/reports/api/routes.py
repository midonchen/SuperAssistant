from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request

from core.auth_dep import require_bearer
from core.errors import ApiException
from core.response import success
from core.store import store

router = APIRouter(prefix="/reports", tags=["reports"])


def _current_household_id(user_id: str) -> str:
    household_id = store.get_user_household_id(user_id)
    if household_id is None:
        raise ApiException(403, "AUTH_403_FORBIDDEN", "user has no household")
    return household_id


def _previous_month() -> str:
    now = datetime.now(timezone.utc)
    if now.month == 1:
        return f"{now.year - 1:04d}-12"
    return f"{now.year:04d}-{now.month - 1:02d}"


@router.get("/consumption/monthly")
async def get_monthly_consumption_report(
    request: Request,
    user_id: str = Depends(require_bearer),
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
):
    household_id = _current_household_id(user_id)
    report_month = month or _previous_month()
    report = store.get_monthly_report(household_id, report_month)
    return success(request, {"report": report.model_dump(mode="json")})
