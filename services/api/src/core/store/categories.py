from __future__ import annotations

import re
import uuid
from uuid import UUID

from sqlalchemy import func, select

from core.db import SessionLocal
from core.errors import ApiException
from core.models import ActivityLogModel, CategoryModel, InventoryItemModel
from core.schemas import Category, CategoryCreateRequest, CategoryUpdateRequest, InventoryStatus, ItemKey, utc_now
from core.store.base import ITEM_META, StoreBase


class CategoryStoreMixin(StoreBase):
    def _ensure_system_categories(self, user_id: str) -> None:
        with SessionLocal() as db:
            existing = {
                row.item_key
                for row in db.scalars(
                    select(CategoryModel).where(CategoryModel.user_id == user_id)
                ).all()
            }
            for key, (name, unit, _max_stock, _warning) in ITEM_META.items():
                if key in existing:
                    continue
                db.add(
                    CategoryModel(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        item_key=key,
                        name=name,
                        icon=None,
                        unit_type=unit,
                        decay_template=None,
                        is_system=True,
                    )
                )
            db.commit()

    def list_categories(self, user_id: UUID) -> list[Category]:
        self._ensure_system_categories(str(user_id))
        with SessionLocal() as db:
            rows = db.scalars(
                select(CategoryModel)
                .where(CategoryModel.user_id == str(user_id))
                .order_by(CategoryModel.is_system.desc(), CategoryModel.name.asc())
            ).all()
            return [self._category(row) for row in rows]

    def get_category(self, user_id: UUID, category_id: str) -> Category:
        with SessionLocal() as db:
            row = db.scalar(
                select(CategoryModel).where(
                    CategoryModel.id == category_id,
                    CategoryModel.user_id == str(user_id),
                )
            )
            if row is None:
                raise KeyError("category not found")
            return self._category(row)

    def _derive_item_key(self, name: str) -> str:
        base = re.sub(r"[^\w\u4e00-\u9fff]+", "", name).upper()[:12]
        if not base:
            base = "CUSTOM"
        return f"{base}_{uuid.uuid4().hex[:6]}"

    def create_category(self, user_id: UUID, request: CategoryCreateRequest) -> Category:
        item_key = self._derive_item_key(request.name)
        with SessionLocal() as db:
            existing = db.scalar(
                select(CategoryModel).where(
                    CategoryModel.user_id == str(user_id),
                    CategoryModel.item_key == item_key,
                )
            )
            if existing is not None:
                raise ApiException(409, "BIZ_409_CONFLICT", "category item_key conflict", retriable=True)
            row = CategoryModel(
                id=str(uuid.uuid4()),
                user_id=str(user_id),
                item_key=item_key,
                name=request.name,
                icon=request.icon,
                unit_type=request.unit_type,
                decay_template=request.decay_template,
                is_system=False,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._category(row)

    def update_category(self, user_id: UUID, category_id: str, request: CategoryUpdateRequest) -> Category:
        with SessionLocal() as db:
            row = db.scalar(
                select(CategoryModel).where(
                    CategoryModel.id == category_id,
                    CategoryModel.user_id == str(user_id),
                )
            )
            if row is None:
                raise KeyError("category not found")
            if row.is_system:
                raise ApiException(403, "AUTH_403_FORBIDDEN", "system category cannot be modified")
            if request.name is not None:
                row.name = request.name
            if request.icon is not None:
                row.icon = request.icon
            if request.unit_type is not None:
                row.unit_type = request.unit_type
            if request.decay_template is not None:
                row.decay_template = request.decay_template
            row.updated_at = utc_now()
            db.commit()
            db.refresh(row)
            return self._category(row)

    def delete_category(self, user_id: UUID, category_id: str) -> None:
        with SessionLocal() as db:
            row = db.scalar(
                select(CategoryModel).where(
                    CategoryModel.id == category_id,
                    CategoryModel.user_id == str(user_id),
                )
            )
            if row is None:
                raise KeyError("category not found")
            if row.is_system:
                raise ApiException(403, "AUTH_403_FORBIDDEN", "system category cannot be deleted")
            activity_count = int(
                db.scalar(
                    select(func.count())
                    .select_from(ActivityLogModel)
                    .where(
                        ActivityLogModel.user_id == str(user_id),
                        ActivityLogModel.item_key == row.item_key,
                        ActivityLogModel.action_type != "AUTO_DECAY",
                    )
                )
                or 0
            )
            if activity_count > 0:
                raise ApiException(409, "BIZ_409_CONFLICT", "category has activity history and cannot be deleted", retriable=False)
            inventory_item = db.scalar(
                select(InventoryItemModel).where(
                    InventoryItemModel.user_id == str(user_id),
                    InventoryItemModel.item_key == row.item_key,
                )
            )
            if inventory_item is not None:
                db.delete(inventory_item)
            db.delete(row)
            db.commit()

    def get_category_meta(self, user_id: UUID, item_key: str) -> dict | None:
        with SessionLocal() as db:
            row = db.scalar(
                select(CategoryModel).where(
                    CategoryModel.user_id == str(user_id),
                    CategoryModel.item_key == item_key,
                )
            )
            if row is None:
                if item_key in ITEM_META:
                    name, unit, max_stock, warning = ITEM_META[item_key]
                    return {"name": name, "unit": unit, "max_stock": max_stock, "warning_threshold": warning}
                return None
            return {
                "name": row.name,
                "unit": row.unit_type,
                "max_stock": row.decay_template.get("max_stock", 100.0) if row.decay_template else 100.0,
                "warning_threshold": row.decay_template.get("warning_threshold", 10.0) if row.decay_template else 10.0,
            }

    def create_inventory_for_category(self, user_id: UUID, category_id: str) -> None:
        with SessionLocal() as db:
            category = db.scalar(
                select(CategoryModel).where(
                    CategoryModel.id == category_id,
                    CategoryModel.user_id == str(user_id),
                )
            )
            if category is None:
                raise KeyError("category not found")
            item_key = category.item_key
            meta = self.get_category_meta(user_id, item_key)
            if meta is None:
                raise KeyError("category meta not found")
            existing = db.scalar(
                select(InventoryItemModel).where(
                    InventoryItemModel.user_id == str(user_id),
                    InventoryItemModel.item_key == item_key,
                )
            )
            if existing is not None:
                return
            max_stock = meta["max_stock"]
            warning_threshold = meta["warning_threshold"]
            now = utc_now()
            db.add(
                InventoryItemModel(
                    user_id=str(user_id),
                    item_key=item_key,
                    item_name=meta["name"],
                    unit=meta["unit"],
                    current_stock=max_stock * 0.5,
                    max_stock=max_stock,
                    warning_threshold=warning_threshold,
                    status=InventoryStatus.WARNING.value,
                    daily_avg_rate=max_stock / 14.0,
                    last_calibrated=now,
                    last_updated=now,
                    server_version=1,
                )
            )
            db.commit()
