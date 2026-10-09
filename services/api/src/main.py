from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from core.errors import ApiException
from core.init_db import init_db
from core.middleware import HeaderValidationMiddleware
from core.response import failure
from modules.admin.api.routes import router as admin_router
from modules.auth.api.routes import router as auth_router
from modules.calendar.api.routes import router as calendar_router
from modules.categories.api.routes import router as categories_router
from modules.contacts.api.routes import router as contacts_router
from modules.career.api.routes import router as career_router
from modules.career.api.routes import skills_router
from modules.career.api.routes import applications_router
from modules.career.api.routes import learning_router
from modules.career.api.routes import advice_router
from modules.reminders.api.routes import bills_router, health_router
from modules.family_affairs.api.routes import router as family_affairs_router
from modules.growth.api.routes import journal_router, life_goals_router, habits_router, workouts_router, assets_router, investments_router
from modules.households.api.routes import router as households_router
from modules.inventory.api.routes import router as inventory_router
from modules.inventory.api.routes import meals_router
from modules.knowledge.api.routes import thinking_models_router, value_principles_router
from modules.meetings.api.routes import router as meetings_router
from modules.ocr.api.routes import router as ocr_router
from modules.push.api.routes import router as push_router
from modules.reports.api.routes import router as reports_router
from modules.tasks.api.routes import router as tasks_router
from modules.voice.api.routes import router as voice_router
from modules.weekly_reports.api.routes import router as weekly_reports_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="SuperAssistant API", version="0.1.0", lifespan=lifespan)
app.add_middleware(HeaderValidationMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
app.include_router(households_router, prefix="/api/v1")
app.include_router(categories_router, prefix="/api/v1")
app.include_router(inventory_router, prefix="/api/v1")
app.include_router(meals_router, prefix="/api/v1")
app.include_router(thinking_models_router, prefix="/api/v1")
app.include_router(value_principles_router, prefix="/api/v1")
app.include_router(journal_router, prefix="/api/v1")
app.include_router(life_goals_router, prefix="/api/v1")
app.include_router(habits_router, prefix="/api/v1")
app.include_router(workouts_router, prefix="/api/v1")
app.include_router(assets_router, prefix="/api/v1")
app.include_router(investments_router, prefix="/api/v1")
app.include_router(voice_router, prefix="/api/v1")
app.include_router(ocr_router, prefix="/api/v1")
app.include_router(push_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(tasks_router, prefix="/api/v1")
app.include_router(calendar_router, prefix="/api/v1")
app.include_router(meetings_router, prefix="/api/v1")
app.include_router(weekly_reports_router, prefix="/api/v1")
app.include_router(contacts_router, prefix="/api/v1")
app.include_router(career_router, prefix="/api/v1")
app.include_router(skills_router, prefix="/api/v1")
app.include_router(applications_router, prefix="/api/v1")
app.include_router(learning_router, prefix="/api/v1")
app.include_router(advice_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")
app.include_router(bills_router, prefix="/api/v1")
app.include_router(family_affairs_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
