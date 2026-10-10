from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from core.auth_dep import require_bearer
from core.response import failure, success
from core.schemas import (
    AssetCreateRequest,
    HabitCreateRequest,
    InterestCreateRequest,
    InvestmentCreateRequest,
    JournalEntryCreateRequest,
    LifeGoalCreateRequest,
    LifeGoalUpdateRequest,
    LifeSkillCreateRequest,
    WorkoutCreateRequest,
)
from core.store import store

journal_router = APIRouter(prefix="/journal", tags=["growth"])
life_goals_router = APIRouter(prefix="/life-goals", tags=["growth"])


@journal_router.get("")
async def list_journal(request: Request, user_id: str = Depends(require_bearer)):
    return success(request, {"entries": [e.model_dump(mode="json") for e in store.list_journal_entries(user_id)]})


@journal_router.post("")
async def create_journal(payload: JournalEntryCreateRequest, request: Request, user_id: str = Depends(require_bearer)):
    entry = store.create_journal_entry(user_id, payload)
    return success(request, {"entry": entry.model_dump(mode="json")})


@journal_router.delete("/{entry_id}")
async def delete_journal(entry_id: str, request: Request, user_id: str = Depends(require_bearer)):
    try:
        store.delete_journal_entry(user_id, entry_id)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "journal entry not found")
    return success(request, {"deleted": True})


@life_goals_router.get("")
async def list_life_goals(request: Request, user_id: str = Depends(require_bearer)):
    return success(request, {"goals": [g.model_dump(mode="json") for g in store.list_life_goals(user_id)]})


@life_goals_router.post("")
async def create_life_goal(payload: LifeGoalCreateRequest, request: Request, user_id: str = Depends(require_bearer)):
    goal = store.create_life_goal(user_id, payload)
    return success(request, {"goal": goal.model_dump(mode="json")})


@life_goals_router.patch("/{goal_id}")
async def update_life_goal(goal_id: str, payload: LifeGoalUpdateRequest, request: Request, user_id: str = Depends(require_bearer)):
    try:
        goal = store.update_life_goal(user_id, goal_id, payload)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "life goal not found")
    return success(request, {"goal": goal.model_dump(mode="json")})


@life_goals_router.delete("/{goal_id}")
async def delete_life_goal(goal_id: str, request: Request, user_id: str = Depends(require_bearer)):
    try:
        store.delete_life_goal(user_id, goal_id)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "life goal not found")
    return success(request, {"deleted": True})


habits_router = APIRouter(prefix="/habits", tags=["growth"])
workouts_router = APIRouter(prefix="/workouts", tags=["growth"])


@habits_router.get("")
async def list_habits(request: Request, user_id: str = Depends(require_bearer)):
    return success(request, {"habits": [h.model_dump(mode="json") for h in store.list_habits(user_id)]})


@habits_router.post("")
async def create_habit(payload: HabitCreateRequest, request: Request, user_id: str = Depends(require_bearer)):
    habit = store.create_habit(user_id, payload)
    return success(request, {"habit": habit.model_dump(mode="json")})


@habits_router.post("/{habit_id}/checkin")
async def checkin_habit(habit_id: str, payload: dict, request: Request, user_id: str = Depends(require_bearer)):
    try:
        result = store.checkin(user_id, habit_id, payload.get("checkin_date", ""))
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "habit not found")
    return success(request, result)


@habits_router.delete("/{habit_id}")
async def delete_habit(habit_id: str, request: Request, user_id: str = Depends(require_bearer)):
    try:
        store.delete_habit(user_id, habit_id)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "habit not found")
    return success(request, {"deleted": True})


@workouts_router.get("")
async def list_workouts(request: Request, user_id: str = Depends(require_bearer)):
    return success(request, {"workouts": [w.model_dump(mode="json") for w in store.list_workouts(user_id)]})


@workouts_router.post("")
async def create_workout(payload: WorkoutCreateRequest, request: Request, user_id: str = Depends(require_bearer)):
    workout = store.create_workout(user_id, payload)
    return success(request, {"workout": workout.model_dump(mode="json")})


@workouts_router.delete("/{workout_id}")
async def delete_workout(workout_id: str, request: Request, user_id: str = Depends(require_bearer)):
    try:
        store.delete_workout(user_id, workout_id)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "workout not found")
    return success(request, {"deleted": True})


assets_router = APIRouter(prefix="/assets", tags=["growth"])
investments_router = APIRouter(prefix="/investments", tags=["growth"])


@assets_router.get("")
async def list_assets(request: Request, user_id: str = Depends(require_bearer)):
    assets = store.list_assets(user_id)
    total = sum(a.amount for a in assets)
    return success(request, {"assets": [a.model_dump(mode="json") for a in assets], "total": total})


@assets_router.post("")
async def create_asset(payload: AssetCreateRequest, request: Request, user_id: str = Depends(require_bearer)):
    asset = store.create_asset(user_id, payload)
    return success(request, {"asset": asset.model_dump(mode="json")})


@assets_router.delete("/{asset_id}")
async def delete_asset(asset_id: str, request: Request, user_id: str = Depends(require_bearer)):
    try:
        store.delete_asset(user_id, asset_id)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "asset not found")
    return success(request, {"deleted": True})


@investments_router.get("")
async def list_investments(request: Request, user_id: str = Depends(require_bearer)):
    return success(request, {"investments": [i.model_dump(mode="json") for i in store.list_investments(user_id)]})


@investments_router.post("")
async def create_investment(payload: InvestmentCreateRequest, request: Request, user_id: str = Depends(require_bearer)):
    investment = store.create_investment(user_id, payload)
    return success(request, {"investment": investment.model_dump(mode="json")})


@investments_router.delete("/{investment_id}")
async def delete_investment(investment_id: str, request: Request, user_id: str = Depends(require_bearer)):
    try:
        store.delete_investment(user_id, investment_id)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "investment not found")
    return success(request, {"deleted": True})


interests_router = APIRouter(prefix="/interests", tags=["growth"])
life_skills_router = APIRouter(prefix="/life-skills", tags=["growth"])


@interests_router.get("")
async def list_interests(request: Request, user_id: str = Depends(require_bearer)):
    return success(request, {"interests": [i.model_dump(mode="json") for i in store.list_interests(user_id)]})


@interests_router.post("")
async def create_interest(payload: InterestCreateRequest, request: Request, user_id: str = Depends(require_bearer)):
    interest = store.create_interest(user_id, payload)
    return success(request, {"interest": interest.model_dump(mode="json")})


@interests_router.delete("/{interest_id}")
async def delete_interest(interest_id: str, request: Request, user_id: str = Depends(require_bearer)):
    try:
        store.delete_interest(user_id, interest_id)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "interest not found")
    return success(request, {"deleted": True})


@life_skills_router.get("")
async def list_life_skills(request: Request, user_id: str = Depends(require_bearer)):
    return success(request, {"life_skills": [s.model_dump(mode="json") for s in store.list_life_skills(user_id)]})


@life_skills_router.post("")
async def create_life_skill(payload: LifeSkillCreateRequest, request: Request, user_id: str = Depends(require_bearer)):
    skill = store.create_life_skill(user_id, payload)
    return success(request, {"life_skill": skill.model_dump(mode="json")})


@life_skills_router.delete("/{life_skill_id}")
async def delete_life_skill(life_skill_id: str, request: Request, user_id: str = Depends(require_bearer)):
    try:
        store.delete_life_skill(user_id, life_skill_id)
    except KeyError:
        return failure(request, 404, "BIZ_404_NOT_FOUND", "life skill not found")
    return success(request, {"deleted": True})
