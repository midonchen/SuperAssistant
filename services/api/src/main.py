from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from core.errors import ApiException
from core.init_db import init_db
from core.middleware import HeaderValidationMiddleware
from core.response import failure
from modules.admin.api.routes import router as admin_router
from modules.auth.api.routes import router as auth_router
from modules.categories.api.routes import router as categories_router
from modules.inventory.api.routes import router as inventory_router
from modules.ocr.api.routes import router as ocr_router
from modules.push.api.routes import router as push_router
from modules.voice.api.routes import router as voice_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="SuperAssistant API", version="0.1.0", lifespan=lifespan)
app.add_middleware(HeaderValidationMiddleware)


@app.exception_handler(ApiException)
async def api_exception_handler(request: Request, exc: ApiException):
    detail = exc.detail
    return failure(
        request,
        status_code=exc.status_code,
        code=detail["code"],
        message=detail["message"],
        details=detail.get("details", {}),
        retriable=detail.get("retriable", False),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return failure(
        request,
        status_code=500,
        code="SYS_500_INTERNAL",
        message="internal error",
        details={"error": str(exc)},
        retriable=True,
    )


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


app.include_router(auth_router, prefix="/api/v1")
app.include_router(categories_router, prefix="/api/v1")
app.include_router(inventory_router, prefix="/api/v1")
app.include_router(voice_router, prefix="/api/v1")
app.include_router(ocr_router, prefix="/api/v1")
app.include_router(push_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
