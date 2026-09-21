from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from core.ai_pipeline import ai_pipeline
from core.approval_store import approval_store
from core.auth_dep import require_admin, require_audit_reviewer
from core.response import success
from core.security_store import query_security_events
from core.schemas import ParsedEntity
from core.store import store

router = APIRouter(prefix="/admin", tags=["admin"])


class AuditReviewRequest(BaseModel):
    action: str
    corrected_entities: list[ParsedEntity] | None = None


class ApprovalCreateRequest(BaseModel):
    reason: str | None = None


class ApprovalReviewRequest(BaseModel):
    decision: str
    comment: str | None = None


@router.get("/dashboard/summary")
async def dashboard_summary(request: Request, user_id: str = Depends(require_admin)):
    total_users = store.count_users()
    total_audit_tasks, pending_audit_tasks = store.count_audit_tasks()
    push_stats = store.get_push_delivery_stats()
    ai_runtime = ai_pipeline.metrics_snapshot()
    return success(
        request,
        {
            "kpi": {
                "total_users": total_users,
                "total_audit_tasks": total_audit_tasks,
                "pending_audit_tasks": pending_audit_tasks,
                "push_sent": push_stats["sent"],
                "push_failed": push_stats["failed"],
            },
            "ai_runtime": ai_runtime,
            "alerts": [{"level": "INFO", "message": "MVP baseline running"}],
        },
    )


@router.get("/users")
async def query_users(
    request: Request,
    user_id: str = Depends(require_admin),
    phone: str | None = Query(default=None),
    user_id_query: str | None = Query(default=None, alias="user_id"),
    status: str | None = Query(default=None),
):
    rows = [profile.model_dump(mode="json") for profile in store.list_users(phone=phone, user_id_query=user_id_query)]
    return success(request, {"list": rows, "total": len(rows)})


@router.get("/households")
async def list_households(request: Request, user_id: str = Depends(require_admin)):
    rows = store.list_households_admin()
    return success(request, {"list": rows, "total": len(rows)})


@router.post("/users/{target_user_id}/session/revoke")
async def revoke_user_session(
    target_user_id: str,
    payload: ApprovalCreateRequest,
    request: Request,
    user_id: str = Depends(require_admin),
):
    approval = approval_store.create_revoke_user_sessions_request(user_id, target_user_id, payload.reason)
    return success(request, {"approval_request": approval})


@router.get("/approvals")
async def list_approval_requests(
    request: Request,
    user_id: str = Depends(require_audit_reviewer),
    status: str | None = Query(default=None),
    action_type: str | None = Query(default=None),
):
    rows = approval_store.list_requests(status=status, action_type=action_type)
    return success(request, {"list": rows, "total": len(rows)})


@router.post("/approvals/{approval_id}/review")
async def review_approval_request(
    approval_id: str,
    payload: ApprovalReviewRequest,
    request: Request,
    user_id: str = Depends(require_audit_reviewer),
):
    reviewed = approval_store.review_request(approval_id, user_id, payload.decision, payload.comment)
    if reviewed is None:
        return success(request, {"approval_id": approval_id, "status": "NOT_FOUND"})
    return success(request, {"approval_request": reviewed})


@router.get("/audit/tasks")
async def list_audit_tasks(request: Request, user_id: str = Depends(require_audit_reviewer)):
    tasks = store.list_audit_tasks()
    return success(request, {"list": tasks, "total": len(tasks)})


@router.post("/audit/tasks/{task_id}/review")
async def review_audit_task(
    task_id: str,
    payload: AuditReviewRequest,
    request: Request,
    user_id: str = Depends(require_audit_reviewer),
):
    ok = store.review_audit_task(
        task_id,
        payload.action,
        corrected_entities=[e.model_dump(mode="json") for e in payload.corrected_entities or []],
    )
    store.add_security_event(
        user_id,
        "ADMIN_AUDIT_REVIEW",
        {"task_id": task_id, "action": payload.action, "result": "DONE" if ok else "NOT_FOUND"},
    )
    return success(request, {"task_id": task_id, "status": "DONE" if ok else "NOT_FOUND"})


@router.get("/security/events")
async def list_security_events(
    request: Request,
    _operator_user_id: str = Depends(require_audit_reviewer),
    target_user_id: str | None = Query(default=None, alias="user_id"),
    event_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    rows = query_security_events(user_id=target_user_id, event_type=event_type, limit=limit)
    return success(request, {"list": rows, "total": len(rows)})
