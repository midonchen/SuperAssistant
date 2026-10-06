from __future__ import annotations

import uuid

from sqlalchemy import func, select

from core.db import SessionLocal
from core.errors import ApiException
from core.models import SkillModel
from core.schemas import Skill, SkillCreateRequest, SkillUpdateRequest, utc_now
from core.store.base import StoreBase


class SkillStoreMixin(StoreBase):
    def _skill(self, row: SkillModel) -> Skill:
        return Skill(
            skill_id=row.id,
            name=row.name,
            category=row.category,
            level=row.level,
            target_level=row.target_level,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _count_skills(self, user_id: str) -> int:
        with SessionLocal() as db:
            return (
                db.scalar(
                    select(func.count()).select_from(SkillModel).where(SkillModel.user_id == user_id)
                )
                or 0
            )

    def create_skill(self, user_id: str, request: SkillCreateRequest) -> Skill:
        if not self.can_use_feature(user_id, "skills", self._count_skills(user_id)):
            self.record_event(user_id, "subscription_gate_hit", {"feature": "skills"})
            raise ApiException(402, "BIZ_402_UPGRADE_REQUIRED", "free tier skill limit reached")
        with SessionLocal() as db:
            row = SkillModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                name=request.name,
                category=request.category,
                level=request.level,
                target_level=request.target_level,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._skill(row)

    def list_skills(self, user_id: str) -> list[Skill]:
        with SessionLocal() as db:
            rows = db.scalars(
                select(SkillModel)
                .where(SkillModel.user_id == user_id)
                .order_by(SkillModel.created_at.desc())
            ).all()
            return [self._skill(r) for r in rows]

    def update_skill(self, user_id: str, skill_id: str, request: SkillUpdateRequest) -> Skill:
        with SessionLocal() as db:
            row = db.scalar(
                select(SkillModel).where(SkillModel.id == skill_id, SkillModel.user_id == user_id)
            )
            if row is None:
                raise KeyError("skill not found")
            if request.name is not None:
                row.name = request.name
            if request.category is not None:
                row.category = request.category
            if request.level is not None:
                row.level = request.level
            if request.target_level is not None:
                row.target_level = request.target_level
            row.updated_at = utc_now()
            db.commit()
            db.refresh(row)
            return self._skill(row)

    def delete_skill(self, user_id: str, skill_id: str) -> None:
        with SessionLocal() as db:
            row = db.scalar(
                select(SkillModel).where(SkillModel.id == skill_id, SkillModel.user_id == user_id)
            )
            if row is None:
                raise KeyError("skill not found")
            db.delete(row)
            db.commit()
