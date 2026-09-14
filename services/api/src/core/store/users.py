from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import Select, func, select

from core.db import SessionLocal
from core.models import (
    InventoryItemModel,
    SecurityEventModel,
    SessionModel,
    UserModel,
)
from core.schemas import (
    InventoryStatus,
    UserProfile,
    utc_now,
)
from core.store.base import ITEM_META, MAX_ACTIVE_SESSIONS, StoreBase


class UserStoreMixin(StoreBase):
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
