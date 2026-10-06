from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from core.auth_dep import require_bearer
from core.response import failure, success
from core.schemas import (
    CareerGoalCreateRequest,
    CareerGoalUpdateRequest,
    JobApplicationCreateRequest,
    JobApplicationUpdateRequest,
    SkillCreateRequest,
    SkillUpdateRequest,
)
from core.store import store

router = APIRouter(prefix="/career-goals", tags=["career-goals"])


@router.get("")
async def list_goals(request: Request, user_id: str = Depends(require_bearer)):
    return success(request, {"goals": [g.model_dump(mode="json") for g in store.list_goals(user_id)]})


@router.post("")
async def create_goal(payload: CareerGoalCreateRequest, request: Request, user_id: str = Depends(require_bearer)):
    goal = store.create_goal(user_id, payload)
    return success(request, {"goal": goal.model_dump(mode="json")})


@router.patch("/{goal_id}")
async def update_goal(goal_id: str, payload: CareerGoalUpdateRequest, request: Request, user_id: str = Depends(require_bearer)):
    try:
        goal = store.update_goal(user_id, goal_id, payload)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "career goal not found")
    return success(request, {"goal": goal.model_dump(mode="json")})


@router.delete("/{goal_id}")
async def delete_goal(goal_id: str, request: Request, user_id: str = Depends(require_bearer)):
    try:
        store.delete_goal(user_id, goal_id)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "career goal not found")
    return success(request, {"deleted": True})


skills_router = APIRouter(prefix="/skills", tags=["skills"])


@skills_router.get("")
async def list_skills(request: Request, user_id: str = Depends(require_bearer)):
    return success(request, {"skills": [s.model_dump(mode="json") for s in store.list_skills(user_id)]})


@skills_router.post("")
async def create_skill(payload: SkillCreateRequest, request: Request, user_id: str = Depends(require_bearer)):
    skill = store.create_skill(user_id, payload)
    return success(request, {"skill": skill.model_dump(mode="json")})


@skills_router.patch("/{skill_id}")
async def update_skill(skill_id: str, payload: SkillUpdateRequest, request: Request, user_id: str = Depends(require_bearer)):
    try:
        skill = store.update_skill(user_id, skill_id, payload)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "skill not found")
    return success(request, {"skill": skill.model_dump(mode="json")})


@skills_router.delete("/{skill_id}")
async def delete_skill(skill_id: str, request: Request, user_id: str = Depends(require_bearer)):
    try:
        store.delete_skill(user_id, skill_id)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "skill not found")
    return success(request, {"deleted": True})


applications_router = APIRouter(prefix="/job-applications", tags=["job-applications"])


@applications_router.get("")
async def list_applications(request: Request, user_id: str = Depends(require_bearer)):
    return success(request, {"applications": [a.model_dump(mode="json") for a in store.list_applications(user_id)]})


@applications_router.post("")
async def create_application(payload: JobApplicationCreateRequest, request: Request, user_id: str = Depends(require_bearer)):
    app = store.create_application(user_id, payload)
    return success(request, {"application": app.model_dump(mode="json")})


@applications_router.patch("/{application_id}")
async def update_application(application_id: str, payload: JobApplicationUpdateRequest, request: Request, user_id: str = Depends(require_bearer)):
    try:
        app = store.update_application(user_id, application_id, payload)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "job application not found")
    return success(request, {"application": app.model_dump(mode="json")})


@applications_router.delete("/{application_id}")
async def delete_application(application_id: str, request: Request, user_id: str = Depends(require_bearer)):
    try:
        store.delete_application(user_id, application_id)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "job application not found")
    return success(request, {"deleted": True})
