from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import select

from core.db import SessionLocal
from core.models import SuggestionItemModel, SuggestionModel
from core.schemas import PurchaseSuggestion, PurchaseSuggestionItem, utc_now
from core.store.base import StoreBase


class SuggestionStoreMixin(StoreBase):
    def build_suggestion(self, household_id: str, user_id: UUID, mode: str = "MANUAL") -> PurchaseSuggestion:
        suggestion_items: list[PurchaseSuggestionItem] = []
        for item in self.list_items(household_id):
            needed = (item.daily_avg_rate * 7.0) - item.current_stock + (item.daily_avg_rate * 7.0 * 0.2)
            if needed > 0:
                suggestion_items.append(
                    PurchaseSuggestionItem(
                        item_key=item.item_key,
                        suggested_qty=round(needed, 2),
                        unit=item.unit,
                        reason="预计7天消耗+20%安全余量",
                    )
                )

        suggestion_id = str(uuid4())
        now = utc_now()
        with SessionLocal() as db:
            suggestion_row = SuggestionModel(
                id=suggestion_id,
                household_id=household_id,
                user_id=str(user_id),
                generated_at=now,
                mode=mode,
                status="PENDING",
            )
            db.add(suggestion_row)
            for item in suggestion_items:
                db.add(
                    SuggestionItemModel(
                        suggestion_id=suggestion_id,
                        item_key=item.item_key,
                        suggested_qty=item.suggested_qty,
                        unit=item.unit,
                        reason=item.reason,
                    )
                )
            db.commit()
            rows = db.scalars(select(SuggestionItemModel).where(SuggestionItemModel.suggestion_id == suggestion_id)).all()
            return self._suggestion(suggestion_row, rows)

    def get_latest_suggestion(self, household_id: str) -> PurchaseSuggestion | None:
        with SessionLocal() as db:
            suggestion = db.scalar(
                select(SuggestionModel)
                .where(SuggestionModel.household_id == household_id)
                .order_by(SuggestionModel.generated_at.desc())
            )
            if suggestion is None:
                return None
            items = db.scalars(select(SuggestionItemModel).where(SuggestionItemModel.suggestion_id == suggestion.id)).all()
            return self._suggestion(suggestion, items)
