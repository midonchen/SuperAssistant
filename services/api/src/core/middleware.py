from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from core.response import failure


WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class HeaderValidationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/healthz":
            response = await call_next(request)
            response.headers["X-API-Revision"] = response.headers.get("X-API-Revision", "1.1")
            return response

        required = ["X-Request-Id", "X-App-Version", "X-Platform"]
        for header in required:
            if not request.headers.get(header):
                return failure(
                    request,
                    status_code=400,
                    code="VAL_400_INVALID_PARAM",
                    message=f"missing header: {header}",
                )

        if request.method in WRITE_METHODS and not request.headers.get("Idempotency-Key"):
            return failure(
                request,
                status_code=400,
                code="VAL_400_INVALID_PARAM",
                message="missing header: Idempotency-Key",
            )

        response = await call_next(request)
        response.headers["X-API-Revision"] = response.headers.get("X-API-Revision", "1.1")
        return response
