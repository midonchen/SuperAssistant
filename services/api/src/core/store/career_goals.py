from __future__ import annotations

import uuid

from sqlalchemy import func, select

from core.ai_pipeline import ai_pipeline
from core.db import SessionLocal
from core.errors import ApiException
from core.models import CareerGoalModel, JobApplicationModel, LearningItemModel, SkillModel
from core.schemas import CareerGoal, CareerGoalCreateRequest, CareerGoalUpdateRequest, utc_now
from core.store.base import StoreBase


class CareerGoalStoreMixin(StoreBase):
    def _goal(self, row: CareerGoalModel) -> CareerGoal:
        return CareerGoal(
            goal_id=row.id,
            title=row.title,
            description=row.description,
            target_year=row.target_year,
            status=row.status,
            progress=row.progress,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _count_goals(self, user_id: str) -> int:
        with SessionLocal() as db:
            return (
                db.scalar(
                    select(func.count()).select_from(CareerGoalModel).where(CareerGoalModel.user_id == user_id)
                )
                or 0
            )

    def create_goal(self, user_id: str, request: CareerGoalCreateRequest) -> CareerGoal:
        if not self.can_use_feature(user_id, "career_goals", self._count_goals(user_id)):
            self.record_event(user_id, "subscription_gate_hit", {"feature": "career_goals"})
            raise ApiException(402, "BIZ_402_UPGRADE_REQUIRED", "free tier career goal limit reached")
        with SessionLocal() as db:
            row = CareerGoalModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                title=request.title,
                description=request.description,
                target_year=request.target_year,
                status="ACTIVE",
                progress=0,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._goal(row)

    def list_goals(self, user_id: str) -> list[CareerGoal]:
        with SessionLocal() as db:
            rows = db.scalars(
                select(CareerGoalModel)
                .where(CareerGoalModel.user_id == user_id)
                .order_by(CareerGoalModel.created_at.desc())
            ).all()
            return [self._goal(r) for r in rows]

    def update_goal(self, user_id: str, goal_id: str, request: CareerGoalUpdateRequest) -> CareerGoal:
        with SessionLocal() as db:
            row = db.scalar(
                select(CareerGoalModel).where(
                    CareerGoalModel.id == goal_id, CareerGoalModel.user_id == user_id
                )
            )
            if row is None:
                raise KeyError("career goal not found")
            if request.title is not None:
                row.title = request.title
            if request.description is not None:
                row.description = request.description
            if request.target_year is not None:
                row.target_year = request.target_year
            if request.status is not None:
                if request.status not in {"ACTIVE", "COMPLETED", "ARCHIVED"}:
                    raise ApiException(400, "VAL_400_INVALID_PARAM", "invalid goal status")
                row.status = request.status
            if request.progress is not None:
                row.progress = request.progress
            row.updated_at = utc_now()
            db.commit()
            db.refresh(row)
            return self._goal(row)

    def delete_goal(self, user_id: str, goal_id: str) -> None:
        with SessionLocal() as db:
            row = db.scalar(
                select(CareerGoalModel).where(
                    CareerGoalModel.id == goal_id, CareerGoalModel.user_id == user_id
                )
            )
            if row is None:
                raise KeyError("career goal not found")
            db.delete(row)
            db.commit()

    def get_career_advice(self, user_id: str) -> dict:
        goals = [g.model_dump(mode="json") for g in self.list_goals(user_id)]
        skills = [s.model_dump(mode="json") for s in self.list_skills(user_id)]
        applications = [a.model_dump(mode="json") for a in self.list_applications(user_id)]
        learning_items = [i.model_dump(mode="json") for i in self.list_learning_items(user_id)]
        advice = ai_pipeline.career_advice(goals, skills, applications, learning_items)
        return {"advice": advice}

    def admin_career_overview(self) -> dict:
        with SessionLocal() as db:
            goals_total = db.scalar(select(func.count()).select_from(CareerGoalModel)) or 0
            skills_total = db.scalar(select(func.count()).select_from(SkillModel)) or 0
            apps_total = db.scalar(select(func.count()).select_from(JobApplicationModel)) or 0
            learning_total = db.scalar(select(func.count()).select_from(LearningItemModel)) or 0
        return {
            "totals": {
                "career_goals": goals_total,
                "skills": skills_total,
                "job_applications": apps_total,
                "learning_items": learning_total,
            }
        }
