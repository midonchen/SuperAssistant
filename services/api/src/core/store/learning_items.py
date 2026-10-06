from __future__ import annotations

import uuid

from sqlalchemy import func, select

from core.db import SessionLocal
from core.errors import ApiException
from core.models import LearningItemModel
from core.schemas import LearningItem, LearningItemCreateRequest, LearningItemUpdateRequest, utc_now
from core.store.base import StoreBase


class LearningItemStoreMixin(StoreBase):
    def _learning_item(self, row: LearningItemModel) -> LearningItem:
        return LearningItem(
            item_id=row.id,
            title=row.title,
            item_type=row.item_type,
            status=row.status,
            notes=row.notes,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _count_learning_items(self, user_id: str) -> int:
        with SessionLocal() as db:
            return (
                db.scalar(
                    select(func.count())
                    .select_from(LearningItemModel)
                    .where(LearningItemModel.user_id == user_id)
                )
                or 0
            )

    def create_learning_item(self, user_id: str, request: LearningItemCreateRequest) -> LearningItem:
        if not self.can_use_feature(user_id, "learning_items", self._count_learning_items(user_id)):
            self.record_event(user_id, "subscription_gate_hit", {"feature": "learning_items"})
            raise ApiException(402, "BIZ_402_UPGRADE_REQUIRED", "free tier learning item limit reached")
        if request.item_type not in {"course", "book", "cert"}:
            raise ApiException(400, "VAL_400_INVALID_PARAM", "invalid item type")
        with SessionLocal() as db:
            row = LearningItemModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                title=request.title,
                item_type=request.item_type,
                notes=request.notes,
                status="TODO",
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._learning_item(row)

    def list_learning_items(self, user_id: str) -> list[LearningItem]:
        with SessionLocal() as db:
            rows = db.scalars(
                select(LearningItemModel)
                .where(LearningItemModel.user_id == user_id)
                .order_by(LearningItemModel.created_at.desc())
            ).all()
            return [self._learning_item(r) for r in rows]

    def update_learning_item(
        self, user_id: str, item_id: str, request: LearningItemUpdateRequest
    ) -> LearningItem:
        with SessionLocal() as db:
            row = db.scalar(
                select(LearningItemModel).where(
                    LearningItemModel.id == item_id, LearningItemModel.user_id == user_id
                )
            )
            if row is None:
                raise KeyError("learning item not found")
            if request.title is not None:
                row.title = request.title
            if request.item_type is not None:
                if request.item_type not in {"course", "book", "cert"}:
                    raise ApiException(400, "VAL_400_INVALID_PARAM", "invalid item type")
                row.item_type = request.item_type
            if request.status is not None:
                if request.status not in {"TODO", "IN_PROGRESS", "DONE"}:
                    raise ApiException(400, "VAL_400_INVALID_PARAM", "invalid item status")
                row.status = request.status
            if request.notes is not None:
                row.notes = request.notes
            row.updated_at = utc_now()
            db.commit()
            db.refresh(row)
            return self._learning_item(row)

    def delete_learning_item(self, user_id: str, item_id: str) -> None:
        with SessionLocal() as db:
            row = db.scalar(
                select(LearningItemModel).where(
                    LearningItemModel.id == item_id, LearningItemModel.user_id == user_id
                )
            )
            if row is None:
                raise KeyError("learning item not found")
            db.delete(row)
            db.commit()
