from __future__ import annotations

from datetime import timezone

from fastapi import Request
from fastapi.responses import JSONResponse

from core.schemas import utc_now


def request_id_from(request: Request) -> str:
    return request.headers.get("X-Request-Id", "missing-request-id")


def success(request: Request, data: dict) -> JSONResponse:
    return JSONResponse(
        {
            "code": "OK",
            "message": "success",
            "request_id": request_id_from(request),
            "timestamp": utc_now().isoformat(),
            "data": data,
        },
        headers={"X-API-Revision": "1.1"},
    )


def failure(request: Request, status_code: int, code: str, message: str, details: dict | None = None, retriable: bool = False) -> JSONResponse:
    return JSONResponse(
        {
            "code": code,
            "message": message,
            "request_id": request_id_from(request),
            "timestamp": utc_now().isoformat(),
            "details": details or {},
            "retriable": retriable,
        },
        status_code=status_code,
        headers={"X-API-Revision": "1.1"},
    )
