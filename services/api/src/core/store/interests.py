from __future__ import annotations

import uuid

from sqlalchemy import func, select

from core.db import SessionLocal
from core.errors import ApiException
from core.models import InterestModel, LifeSkillModel
from core.schemas import Interest, InterestCreateRequest, LifeSkill, LifeSkillCreateRequest
from core.store.base import StoreBase


class InterestStoreMixin(StoreBase):
    def _interest(self, row: InterestModel) -> Interest:
        return Interest(
            interest_id=row.id,
            name=row.name,
            note=row.note,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _count_interests(self, user_id: str) -> int:
        with SessionLocal() as db:
            return (
                db.scalar(select(func.count()).select_from(InterestModel).where(InterestModel.user_id == user_id))
                or 0
            )

    def create_interest(self, user_id: str, request: InterestCreateRequest) -> Interest:
        if not self.can_use_feature(user_id, "interests", self._count_interests(user_id)):
            self.record_event(user_id, "subscription_gate_hit", {"feature": "interests"})
            raise ApiException(402, "BIZ_402_UPGRADE_REQUIRED", "free tier interest limit reached")
        with SessionLocal() as db:
            row = InterestModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                name=request.name,
                note=request.note,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._interest(row)

    def list_interests(self, user_id: str) -> list[Interest]:
        with SessionLocal() as db:
            rows = db.scalars(
                select(InterestModel).where(InterestModel.user_id == user_id).order_by(InterestModel.created_at.desc())
            ).all()
            return [self._interest(r) for r in rows]

    def delete_interest(self, user_id: str, interest_id: str) -> None:
        with SessionLocal() as db:
            row = db.scalar(
                select(InterestModel).where(InterestModel.id == interest_id, InterestModel.user_id == user_id)
            )
            if row is None:
                raise KeyError("interest not found")
            db.delete(row)
            db.commit()


class LifeSkillStoreMixin(StoreBase):
    def _life_skill(self, row: LifeSkillModel) -> LifeSkill:
        return LifeSkill(
            life_skill_id=row.id,
            name=row.name,
            level=row.level,
            note=row.note,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _count_life_skills(self, user_id: str) -> int:
        with SessionLocal() as db:
            return (
                db.scalar(select(func.count()).select_from(LifeSkillModel).where(LifeSkillModel.user_id == user_id))
                or 0
            )

    def create_life_skill(self, user_id: str, request: LifeSkillCreateRequest) -> LifeSkill:
        if not self.can_use_feature(user_id, "life_skills", self._count_life_skills(user_id)):
            self.record_event(user_id, "subscription_gate_hit", {"feature": "life_skills"})
            raise ApiException(402, "BIZ_402_UPGRADE_REQUIRED", "free tier life skill limit reached")
        with SessionLocal() as db:
            row = LifeSkillModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                name=request.name,
                level=request.level,
                note=request.note,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._life_skill(row)

    def list_life_skills(self, user_id: str) -> list[LifeSkill]:
        with SessionLocal() as db:
            rows = db.scalars(
                select(LifeSkillModel).where(LifeSkillModel.user_id == user_id).order_by(LifeSkillModel.created_at.desc())
            ).all()
            return [self._life_skill(r) for r in rows]

    def delete_life_skill(self, user_id: str, life_skill_id: str) -> None:
        with SessionLocal() as db:
            row = db.scalar(
                select(LifeSkillModel).where(LifeSkillModel.id == life_skill_id, LifeSkillModel.user_id == user_id)
            )
            if row is None:
                raise KeyError("life skill not found")
            db.delete(row)
            db.commit()
