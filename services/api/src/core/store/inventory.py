from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select

from core.db import SessionLocal
from core.errors import ApiException
from core.models import ActivityLogModel, InventoryItemModel
from core.offline_queue import offline_replay_queue
from core.schemas import (
    ActionType,
    ActivityLog,
    InventoryItem,
    Operation,
    utc_now,
)
from core.store.base import StoreBase


class InventoryStoreMixin(StoreBase):
    def list_items(self, user_id: UUID, status: str | None = None) -> list[InventoryItem]:
        with SessionLocal() as db:
            stmt = select(InventoryItemModel).where(InventoryItemModel.user_id == str(user_id))
            if status:
                stmt = stmt.where(InventoryItemModel.status == status)
            rows = db.scalars(stmt).all()
            return [self._inventory_item(row) for row in rows]

    def get_item(self, user_id: UUID, item_key: str) -> InventoryItem:
        with SessionLocal() as db:
            row = db.scalar(
                select(InventoryItemModel).where(
                    InventoryItemModel.user_id == str(user_id),
                    InventoryItemModel.item_key == item_key,
                )
            )
            if row is None:
                raise KeyError("item not found")
            return self._inventory_item(row)

    def apply_operation(self, user_id: UUID, item_key: str, op: Operation, value: float, source: ActionType) -> ActivityLog:
        with SessionLocal() as db:
            row = db.scalar(
                select(InventoryItemModel).where(
                    InventoryItemModel.user_id == str(user_id),
                    InventoryItemModel.item_key == item_key,
                )
            )
            if row is None:
                raise KeyError("item not found")

            before = row.current_stock
            if op == Operation.ADD:
                after = before + value
            elif op == Operation.SET:
                after = value
            elif op == Operation.SUBTRACT:
                after = max(0.0, before - value)
            else:
                after = 0.0

            row.current_stock = round(after, 3)
            row.last_updated = utc_now()
            row.server_version += 1
            row.status = self._status_for(row.current_stock, row.warning_threshold)

            log_row = ActivityLogModel(
                user_id=str(user_id),
                item_key=item_key,
                action_type=source.value,
                operation=op.value,
                delta_value=round(after - before, 3),
                before_value=round(before, 3),
                after_value=round(after, 3),
                timestamp=utc_now(),
            )
            db.add(log_row)
            db.commit()
            db.refresh(log_row)
            return self._activity(log_row)

    def apply_batch_operations(self, user_id: UUID, operations: list[dict], from_replay: bool = False) -> dict:
        updated: dict[str, dict] = {}
        activity_ids: list[str] = []

        for raw in operations:
            op_id = raw.get("op_id")
            if op_id and offline_replay_queue.is_processed(op_id):
                continue

            item_key = raw["item_key"]
            operation = raw["operation"] if isinstance(raw["operation"], Operation) else Operation(raw["operation"])
            source = raw["source"] if isinstance(raw["source"], ActionType) else ActionType(raw["source"])
            value = float(raw["value"])
            client_version = raw.get("client_version")

            if client_version is not None:
                item = self.get_item(user_id, item_key)
                if item.server_version != int(client_version):
                    raise ApiException(
                        409,
                        "BIZ_409_CONFLICT",
                        "inventory version conflict",
                        details={
                            "item_key": item_key,
                            "server_version": item.server_version,
                            "client_version": int(client_version),
                        },
                        retriable=True,
                    )

            log = self.apply_operation(user_id, item_key, operation, value, source)
            activity_ids.append(str(log.activity_id))
            item = self.get_item(user_id, item_key)
            updated[item_key] = {
                "item_key": item.item_key,
                "current_stock": item.current_stock,
                "status": item.status,
                "server_version": item.server_version,
            }

            if op_id:
                offline_replay_queue.mark_processed(op_id)

        return {"updated_items": list(updated.values()), "activity_ids": activity_ids}

    def run_auto_decay_for_all(self) -> dict:
        user_ids = self.list_user_ids()
        affected_items = 0
        for user_id in user_ids:
            for item in self.list_items(user_id):
                before = item.current_stock
                decay = max(0.0, item.daily_avg_rate)
                after = max(0.0, round(before - decay, 3))
                with SessionLocal() as db:
                    row = db.scalar(
                        select(InventoryItemModel).where(
                            InventoryItemModel.user_id == str(user_id),
                            InventoryItemModel.item_key == item.item_key,
                        )
                    )
                    if row is None:
                        continue
                    row.current_stock = after
                    row.last_updated = utc_now()
                    row.server_version += 1
                    row.status = self._status_for(after, row.warning_threshold)
                    db.add(
                        ActivityLogModel(
                            user_id=str(user_id),
                            item_key=item.item_key,
                            action_type=ActionType.AUTO_DECAY.value,
                            operation=Operation.SUBTRACT.value,
                            delta_value=round(after - before, 3),
                            before_value=round(before, 3),
                            after_value=round(after, 3),
                            timestamp=utc_now(),
                        )
                    )
                    db.commit()
                    affected_items += 1
        return {"processed_users": len(user_ids), "affected_items": affected_items}

    def list_logs(self, user_id: UUID, page: int, page_size: int, item_key: str | None = None) -> tuple[list[ActivityLog], int]:
        with SessionLocal() as db:
            stmt = select(ActivityLogModel).where(ActivityLogModel.user_id == str(user_id))
            count_stmt = select(func.count()).select_from(ActivityLogModel).where(ActivityLogModel.user_id == str(user_id))
            if item_key is not None:
                stmt = stmt.where(ActivityLogModel.item_key == item_key)
                count_stmt = count_stmt.where(ActivityLogModel.item_key == item_key)
            stmt = stmt.order_by(ActivityLogModel.timestamp.desc()).offset((page - 1) * page_size).limit(page_size)
            rows = db.scalars(stmt).all()
            total = int(db.scalar(count_stmt) or 0)
            return [self._activity(row) for row in rows], total
