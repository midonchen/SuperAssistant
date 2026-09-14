from __future__ import annotations

from dataclasses import dataclass
import os
from uuid import UUID, uuid4

from sqlalchemy import Select, func, select

from core.db import SessionLocal
from core.errors import ApiException
from core.models import (
    ActivityLogModel,
    AuditTaskModel,
    InventoryItemModel,
    PushDeliveryModel,
    PushDeviceModel,
    PushPreferenceModel,
    SecurityEventModel,
    SessionModel,
    SuggestionItemModel,
    SuggestionModel,
    UserModel,
)
from core.offline_queue import offline_replay_queue
from core.schemas import (
    ActionType,
    ActivityLog,
    InventoryItem,
    InventoryStatus,
    ItemKey,
    Operation,
    ParsedEntity,
    PurchaseSuggestion,
    PurchaseSuggestionItem,
    UserProfile,
    utc_now,
)


ITEM_META = {
    ItemKey.EGG: ("鸡蛋", "个", 30.0, 6.0),
    ItemKey.MILK: ("牛奶", "L", 4.0, 1.0),
    ItemKey.MANTOU: ("馒头", "个", 20.0, 4.0),
    ItemKey.RICE: ("大米", "kg", 10.0, 2.0),
    ItemKey.PORK: ("猪肉", "g", 1500.0, 300.0),
    ItemKey.VEG: ("蔬菜", "份", 7.0, 2.0),
}

DEFAULT_ADMIN_PHONES = "13900139000"
ADMIN_PHONE_ALLOWLIST = {
    phone.strip()
    for phone in os.getenv("SUPERASSISTANT_ADMIN_PHONES", DEFAULT_ADMIN_PHONES).split(",")
    if phone.strip()
}
DEFAULT_AUDITOR_PHONES = "13900139001"
AUDITOR_PHONE_ALLOWLIST = {
    phone.strip()
    for phone in os.getenv("SUPERASSISTANT_AUDITOR_PHONES", DEFAULT_AUDITOR_PHONES).split(",")
    if phone.strip()
}
DEFAULT_MAX_ACTIVE_SESSIONS = 3
try:
    MAX_ACTIVE_SESSIONS = max(1, int(os.getenv("SUPERASSISTANT_MAX_ACTIVE_SESSIONS", str(DEFAULT_MAX_ACTIVE_SESSIONS))))
except ValueError:
    MAX_ACTIVE_SESSIONS = DEFAULT_MAX_ACTIVE_SESSIONS

@dataclass
class Store:
    def _role_for_phone(self, phone: str) -> str:
        if phone in ADMIN_PHONE_ALLOWLIST:
            return "ADMIN"
        if phone in AUDITOR_PHONE_ALLOWLIST:
            return "AUDITOR"
        return "USER"

    def _profile(self, user: UserModel) -> UserProfile:
        return UserProfile(
            user_id=UUID(user.id),
            phone_masked=user.phone_masked,
            timezone=user.timezone,
            shopping_day=user.shopping_day,
            shopping_cycle=user.shopping_cycle,
            role=user.role,
            onboarded=user.onboarded,
        )

    def _inventory_item(self, row: InventoryItemModel) -> InventoryItem:
        return InventoryItem(
            item_key=ItemKey(row.item_key),
            item_name=row.item_name,
            unit=row.unit,
            current_stock=row.current_stock,
            max_stock=row.max_stock,
            warning_threshold=row.warning_threshold,
            status=InventoryStatus(row.status),
            daily_avg_rate=row.daily_avg_rate,
            last_calibrated=row.last_calibrated,
            last_updated=row.last_updated,
            server_version=row.server_version,
        )

    def _activity(self, row: ActivityLogModel) -> ActivityLog:
        return ActivityLog(
            activity_id=UUID(row.id),
            item_key=ItemKey(row.item_key),
            action_type=ActionType(row.action_type),
            operation=Operation(row.operation),
            delta_value=row.delta_value,
            before_value=row.before_value,
            after_value=row.after_value,
            raw_text=row.raw_text,
            confidence=row.confidence,
            operator_role=row.operator_role,
            timestamp=row.timestamp,
        )

    def _suggestion(self, suggestion: SuggestionModel, items: list[SuggestionItemModel]) -> PurchaseSuggestion:
        return PurchaseSuggestion(
            suggestion_id=UUID(suggestion.id),
            generated_at=suggestion.generated_at,
            mode=suggestion.mode,
            status=suggestion.status,
            items=[
                PurchaseSuggestionItem(
                    item_key=ItemKey(item.item_key),
                    suggested_qty=item.suggested_qty,
                    unit=item.unit,
                    reason=item.reason,
                )
                for item in items
            ],
        )

    def bootstrap_user(self, phone: str) -> tuple[UUID, UserProfile]:
        role = self._role_for_phone(phone)
        with SessionLocal() as db:
            user = db.scalar(select(UserModel).where(UserModel.phone == phone))
            if user is None:
                user = UserModel(
                    phone=phone,
                    phone_masked=f"{phone[:3]}****{phone[-4:]}",
                    timezone="Asia/Shanghai",
                    shopping_day=6,
                    shopping_cycle=7,
                    role=role,
                    onboarded=True,
                )
                db.add(user)
                db.flush()
                now = utc_now()
                for key, (name, unit, max_stock, warning_threshold) in ITEM_META.items():
                    db.add(
                        InventoryItemModel(
                            user_id=user.id,
                            item_key=key.value,
                            item_name=name,
                            unit=unit,
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
                db.refresh(user)
            elif user.role != role:
                user.role = role
                db.commit()
                db.refresh(user)
            return UUID(user.id), self._profile(user)

    def upsert_session(self, user_id: UUID, device_id: str = "unknown") -> tuple[str, str, str]:
        sid = str(uuid4())
        access = f"access-{uuid4()}"
        refresh = f"refresh-{uuid4()}"
        with SessionLocal() as db:
            active_sessions = db.scalars(
                select(SessionModel)
                .where(
                    SessionModel.user_id == str(user_id),
                    SessionModel.revoked.is_(False),
                )
                .order_by(SessionModel.created_at.asc())
            ).all()
            overflow = len(active_sessions) - MAX_ACTIVE_SESSIONS + 1
            if overflow > 0:
                for row in active_sessions[:overflow]:
                    row.revoked = True
                    db.add(
                        SecurityEventModel(
                            user_id=str(user_id),
                            event_type="SESSION_EVICTED",
                            details={
                                "evicted_session_id": row.id,
                                "reason": "MAX_ACTIVE_SESSIONS",
                                "max_active_sessions": MAX_ACTIVE_SESSIONS,
                                "new_device_id": device_id,
                            },
                            created_at=utc_now(),
                        )
                    )
            db.add(
                SessionModel(
                    id=sid,
                    user_id=str(user_id),
                    access_token=access,
                    refresh_token=refresh,
                    device_id=device_id,
                    revoked=False,
                )
            )
            db.commit()
        return sid, access, refresh

    def resolve_user_id_by_access(self, access_token: str) -> UUID | None:
        with SessionLocal() as db:
            row = db.scalar(
                select(SessionModel).where(
                    SessionModel.access_token == access_token,
                    SessionModel.revoked.is_(False),
                )
            )
            return UUID(row.user_id) if row else None

    def resolve_user_id_by_refresh(self, refresh_token: str) -> UUID | None:
        with SessionLocal() as db:
            row = db.scalar(
                select(SessionModel).where(
                    SessionModel.refresh_token == refresh_token,
                    SessionModel.revoked.is_(False),
                )
            )
            return UUID(row.user_id) if row else None

    def rotate_session_tokens_by_refresh(self, refresh_token: str, device_id: str = "unknown") -> tuple[str, str, str] | None:
        with SessionLocal() as db:
            row = db.scalar(
                select(SessionModel).where(
                    SessionModel.refresh_token == refresh_token,
                    SessionModel.revoked.is_(False),
                )
            )
            if row is None:
                return None

            row.access_token = f"access-{uuid4()}"
            row.refresh_token = f"refresh-{uuid4()}"
            row.device_id = device_id
            db.commit()
            return row.id, row.access_token, row.refresh_token

    def revoke_session(self, session_id: str) -> None:
        with SessionLocal() as db:
            row = db.scalar(select(SessionModel).where(SessionModel.id == session_id))
            if row:
                row.revoked = True
                db.commit()

    def revoke_session_owned(self, session_id: str, user_id: str) -> bool:
        with SessionLocal() as db:
            row = db.scalar(
                select(SessionModel).where(
                    SessionModel.id == session_id,
                    SessionModel.user_id == user_id,
                    SessionModel.revoked.is_(False),
                )
            )
            if row is None:
                return False
            row.revoked = True
            db.commit()
            return True

    def revoke_sessions_by_user(self, user_id: str) -> int:
        with SessionLocal() as db:
            rows = db.scalars(select(SessionModel).where(SessionModel.user_id == user_id, SessionModel.revoked.is_(False))).all()
            for row in rows:
                row.revoked = True
            db.commit()
            return len(rows)

    def is_admin_user(self, user_id: str) -> bool:
        return self.has_any_role(user_id, {"ADMIN"})

    def is_audit_reviewer(self, user_id: str) -> bool:
        return self.has_any_role(user_id, {"ADMIN", "AUDITOR"})

    def has_any_role(self, user_id: str, roles: set[str]) -> bool:
        with SessionLocal() as db:
            row = db.scalar(select(UserModel).where(UserModel.id == user_id))
            if row is None:
                return False
            return row.role in roles

    def list_security_events(self, user_id: UUID | str, limit: int = 20) -> list[dict]:
        uid = str(user_id)
        with SessionLocal() as db:
            rows = db.scalars(
                select(SecurityEventModel)
                .where(SecurityEventModel.user_id == uid)
                .order_by(SecurityEventModel.created_at.desc())
                .limit(limit)
            ).all()
            return [
                {
                    "event_type": row.event_type,
                    "details": row.details,
                    "created_at": row.created_at,
                }
                for row in rows
            ]

    def add_security_event(self, user_id: UUID | str, event_type: str, details: dict) -> None:
        uid = str(user_id)
        with SessionLocal() as db:
            db.add(
                SecurityEventModel(
                    user_id=uid,
                    event_type=event_type,
                    details=details,
                    created_at=utc_now(),
                )
            )
            db.commit()

    def count_users(self) -> int:
        with SessionLocal() as db:
            return int(db.scalar(select(func.count()).select_from(UserModel)) or 0)

    def count_audit_tasks(self) -> tuple[int, int]:
        with SessionLocal() as db:
            total = int(db.scalar(select(func.count()).select_from(AuditTaskModel)) or 0)
            pending = int(
                db.scalar(select(func.count()).select_from(AuditTaskModel).where(AuditTaskModel.status == "PENDING")) or 0
            )
            return total, pending

    def list_user_ids(self) -> list[UUID]:
        with SessionLocal() as db:
            rows = db.scalars(select(UserModel.id)).all()
            return [UUID(row) for row in rows]

    def list_users(self, phone: str | None = None, user_id_query: str | None = None) -> list[UserProfile]:
        with SessionLocal() as db:
            stmt: Select[tuple[UserModel]] = select(UserModel)
            if phone:
                stmt = stmt.where(UserModel.phone.like(f"{phone}%"))
            if user_id_query:
                stmt = stmt.where(UserModel.id == user_id_query)
            rows = db.scalars(stmt).all()
            return [self._profile(row) for row in rows]

    def get_user_profile(self, user_id: UUID) -> UserProfile:
        with SessionLocal() as db:
            row = db.scalar(select(UserModel).where(UserModel.id == str(user_id)))
            if row is None:
                raise KeyError("user not found")
            return self._profile(row)

    def list_items(self, user_id: UUID, status: str | None = None) -> list[InventoryItem]:
        with SessionLocal() as db:
            stmt = select(InventoryItemModel).where(InventoryItemModel.user_id == str(user_id))
            if status:
                stmt = stmt.where(InventoryItemModel.status == status)
            rows = db.scalars(stmt).all()
            return [self._inventory_item(row) for row in rows]

    def get_item(self, user_id: UUID, item_key: ItemKey) -> InventoryItem:
        with SessionLocal() as db:
            row = db.scalar(
                select(InventoryItemModel).where(
                    InventoryItemModel.user_id == str(user_id),
                    InventoryItemModel.item_key == item_key.value,
                )
            )
            if row is None:
                raise KeyError("item not found")
            return self._inventory_item(row)

    def _status_for(self, current_stock: float, warning_threshold: float) -> str:
        if current_stock <= 0:
            return InventoryStatus.EMPTY.value
        if current_stock <= warning_threshold:
            return InventoryStatus.CRITICAL.value
        if current_stock <= warning_threshold * 2:
            return InventoryStatus.WARNING.value
        return InventoryStatus.PLENTY.value

    def apply_operation(self, user_id: UUID, item_key: ItemKey, op: Operation, value: float, source: ActionType) -> ActivityLog:
        with SessionLocal() as db:
            row = db.scalar(
                select(InventoryItemModel).where(
                    InventoryItemModel.user_id == str(user_id),
                    InventoryItemModel.item_key == item_key.value,
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
                item_key=item_key.value,
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

            item_key = raw["item_key"] if isinstance(raw["item_key"], ItemKey) else ItemKey(raw["item_key"])
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
                            "item_key": item_key.value,
                            "server_version": item.server_version,
                            "client_version": int(client_version),
                        },
                        retriable=True,
                    )

            log = self.apply_operation(user_id, item_key, operation, value, source)
            activity_ids.append(str(log.activity_id))
            item = self.get_item(user_id, item_key)
            updated[item_key.value] = {
                "item_key": item.item_key,
                "current_stock": item.current_stock,
                "status": item.status,
                "server_version": item.server_version,
            }

            if op_id:
                offline_replay_queue.mark_processed(op_id)

        return {"updated_items": list(updated.values()), "activity_ids": activity_ids}

    def enqueue_offline_replay_ops(self, user_id: UUID, offline_ops: list[dict]) -> dict:
        queued = 0
        for row in offline_ops:
            payload = {
                "job_id": row.get("op_id", str(uuid4())),
                "user_id": str(user_id),
                "created_at": row.get("created_at"),
                "retry_count": int(row.get("retry_count", 0)),
                "payload": row.get("payload", {}),
            }
            offline_replay_queue.enqueue(payload)
            queued += 1
        return {"queued_count": queued, "queue_depth": offline_replay_queue.size()}

    def process_offline_replay_queue(self, max_jobs: int = 100) -> dict:
        jobs = offline_replay_queue.pop_many(max_jobs=max_jobs)
        processed = 0
        applied_ops = 0
        conflicts = 0
        failed = 0
        retried = 0

        for job in jobs:
            try:
                user_id = UUID(job["user_id"])
                payload = job.get("payload", {})
                operations = payload.get("operations", [])
                result = self.apply_batch_operations(user_id, operations, from_replay=True)
                processed += 1
                applied_ops += len(result["activity_ids"])
            except ApiException as exc:
                if exc.detail.get("code") == "BIZ_409_CONFLICT":
                    conflicts += 1
                    processed += 1
                    continue
                failed += 1
            except Exception:
                retry_count = int(job.get("retry_count", 0))
                if retry_count < 5:
                    job["retry_count"] = retry_count + 1
                    offline_replay_queue.enqueue(job)
                    retried += 1
                else:
                    failed += 1

        return {
            "processed_jobs": processed,
            "applied_ops": applied_ops,
            "conflicts": conflicts,
            "failed": failed,
            "retried": retried,
            "queue_depth": offline_replay_queue.size(),
        }

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
                            InventoryItemModel.item_key == item.item_key.value,
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
                            item_key=item.item_key.value,
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

    def list_logs(self, user_id: UUID, page: int, page_size: int, item_key: ItemKey | None = None) -> tuple[list[ActivityLog], int]:
        with SessionLocal() as db:
            stmt = select(ActivityLogModel).where(ActivityLogModel.user_id == str(user_id))
            count_stmt = select(func.count()).select_from(ActivityLogModel).where(ActivityLogModel.user_id == str(user_id))
            if item_key is not None:
                stmt = stmt.where(ActivityLogModel.item_key == item_key.value)
                count_stmt = count_stmt.where(ActivityLogModel.item_key == item_key.value)
            stmt = stmt.order_by(ActivityLogModel.timestamp.desc()).offset((page - 1) * page_size).limit(page_size)
            rows = db.scalars(stmt).all()
            total = int(db.scalar(count_stmt) or 0)
            return [self._activity(row) for row in rows], total

    def build_suggestion(self, user_id: UUID, mode: str = "MANUAL") -> PurchaseSuggestion:
        suggestion_items: list[PurchaseSuggestionItem] = []
        for item in self.list_items(user_id):
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
                        item_key=item.item_key.value,
                        suggested_qty=item.suggested_qty,
                        unit=item.unit,
                        reason=item.reason,
                    )
                )
            db.commit()
            rows = db.scalars(select(SuggestionItemModel).where(SuggestionItemModel.suggestion_id == suggestion_id)).all()
            return self._suggestion(suggestion_row, rows)

    def get_latest_suggestion(self, user_id: UUID) -> PurchaseSuggestion | None:
        with SessionLocal() as db:
            suggestion = db.scalar(
                select(SuggestionModel)
                .where(SuggestionModel.user_id == str(user_id))
                .order_by(SuggestionModel.generated_at.desc())
            )
            if suggestion is None:
                return None
            items = db.scalars(select(SuggestionItemModel).where(SuggestionItemModel.suggestion_id == suggestion.id)).all()
            return self._suggestion(suggestion, items)

    def register_push_device(self, user_id: UUID, platform: str, device_token: str) -> bool:
        with SessionLocal() as db:
            row = db.scalar(
                select(PushDeviceModel).where(
                    PushDeviceModel.user_id == str(user_id),
                    PushDeviceModel.device_token == device_token,
                )
            )
            if row is not None:
                return False
            db.add(
                PushDeviceModel(
                    user_id=str(user_id),
                    platform=platform,
                    device_token=device_token,
                    created_at=utc_now(),
                )
            )
            db.commit()
            return True

    def upsert_push_preference(self, user_id: UUID, enabled: bool, notify_time: str) -> dict:
        with SessionLocal() as db:
            profile = db.scalar(select(UserModel).where(UserModel.id == str(user_id)))
            if profile is None:
                raise KeyError("user not found")
            row = db.scalar(select(PushPreferenceModel).where(PushPreferenceModel.user_id == str(user_id)))
            if row is None:
                row = PushPreferenceModel(
                    user_id=str(user_id),
                    enabled=enabled,
                    notify_time=notify_time,
                    timezone=profile.timezone,
                    updated_at=utc_now(),
                )
                db.add(row)
            else:
                row.enabled = enabled
                row.notify_time = notify_time
                row.updated_at = utc_now()
            db.commit()
            return {"enabled": row.enabled, "notify_time": row.notify_time, "timezone": row.timezone}

    def get_push_preference(self, user_id: UUID) -> dict:
        with SessionLocal() as db:
            profile = db.scalar(select(UserModel).where(UserModel.id == str(user_id)))
            if profile is None:
                raise KeyError("user not found")
            row = db.scalar(select(PushPreferenceModel).where(PushPreferenceModel.user_id == str(user_id)))
            if row is None:
                return {"enabled": True, "notify_time": "20:00", "timezone": profile.timezone}
            return {"enabled": row.enabled, "notify_time": row.notify_time, "timezone": row.timezone}

    def run_purchase_reminders_for_all(self) -> dict:
        sent = 0
        failed = 0
        skipped = 0
        user_ids = self.list_user_ids()
        for user_id in user_ids:
            preference = self.get_push_preference(user_id)
            if not preference["enabled"]:
                with SessionLocal() as db:
                    db.add(
                        PushDeliveryModel(
                            user_id=str(user_id),
                            suggestion_id=None,
                            status="SKIPPED",
                            attempt_count=1,
                            error_message="preference disabled",
                            created_at=utc_now(),
                            delivered_at=None,
                        )
                    )
                    db.commit()
                skipped += 1
                continue

            with SessionLocal() as db:
                devices = db.scalars(select(PushDeviceModel).where(PushDeviceModel.user_id == str(user_id))).all()
            if not devices:
                with SessionLocal() as db:
                    db.add(
                        PushDeliveryModel(
                            user_id=str(user_id),
                            suggestion_id=None,
                            status="FAILED",
                            attempt_count=1,
                            error_message="no registered device",
                            created_at=utc_now(),
                            delivered_at=None,
                        )
                    )
                    db.commit()
                failed += 1
                continue

            suggestion = self.get_latest_suggestion(user_id) or self.build_suggestion(user_id, mode="AUTO")
            with SessionLocal() as db:
                db.add(
                    PushDeliveryModel(
                        user_id=str(user_id),
                        suggestion_id=str(suggestion.suggestion_id),
                        status="SENT",
                        attempt_count=1,
                        error_message=None,
                        created_at=utc_now(),
                        delivered_at=utc_now(),
                    )
                )
                db.commit()
            sent += 1

        return {"processed_users": len(user_ids), "sent": sent, "failed": failed, "skipped": skipped}

    def get_push_delivery_stats(self) -> dict:
        with SessionLocal() as db:
            sent = int(db.scalar(select(func.count()).select_from(PushDeliveryModel).where(PushDeliveryModel.status == "SENT")) or 0)
            failed = int(
                db.scalar(select(func.count()).select_from(PushDeliveryModel).where(PushDeliveryModel.status == "FAILED")) or 0
            )
            skipped = int(
                db.scalar(select(func.count()).select_from(PushDeliveryModel).where(PushDeliveryModel.status == "SKIPPED")) or 0
            )
            return {"sent": sent, "failed": failed, "skipped": skipped}

    def add_audit_task(self, parse_session_id: str, entities: list[ParsedEntity]) -> None:
        with SessionLocal() as db:
            db.add(
                AuditTaskModel(
                    parse_session_id=parse_session_id,
                    status="PENDING",
                    entities=[entity.model_dump(mode="json") for entity in entities],
                    created_at=utc_now(),
                )
            )
            db.commit()

    def list_audit_tasks(self) -> list[dict]:
        with SessionLocal() as db:
            rows = db.scalars(select(AuditTaskModel).order_by(AuditTaskModel.created_at.desc())).all()
            return [
                {
                    "task_id": row.id,
                    "parse_session_id": row.parse_session_id,
                    "status": row.status,
                    "entities": row.entities,
                    "review_action": row.review_action,
                    "corrected_entities": row.corrected_entities,
                    "created_at": row.created_at.isoformat(),
                    "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
                }
                for row in rows
            ]

    def review_audit_task(self, task_id: str, action: str, corrected_entities: list[dict] | None = None) -> bool:
        with SessionLocal() as db:
            row = db.scalar(select(AuditTaskModel).where(AuditTaskModel.id == task_id))
            if row is None:
                return False
            row.status = "DONE"
            row.review_action = action
            row.corrected_entities = corrected_entities or []
            row.reviewed_at = utc_now()
            db.commit()
            return True


store = Store()
