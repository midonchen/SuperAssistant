from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select

from core.db import SessionLocal
from core.models import HouseholdMembershipModel, PushDeliveryModel, PushDeviceModel, PushPreferenceModel, UserModel
from core.schemas import utc_now
from core.store.base import StoreBase


class PushStoreMixin(StoreBase):
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
        household_ids = self.list_household_ids()
        for household_id in household_ids:
            # Use any household member with a push preference; default to enabled.
            with SessionLocal() as db:
                memberships = db.scalars(
                    select(HouseholdMembershipModel).where(HouseholdMembershipModel.household_id == household_id)
                ).all()
                member_ids = [member.user_id for member in memberships]
                preferences = db.scalars(
                    select(PushPreferenceModel).where(PushPreferenceModel.user_id.in_(member_ids))
                ).all()
                enabled = any(p.enabled for p in preferences) if preferences else True
                devices = db.scalars(
                    select(PushDeviceModel).where(PushDeviceModel.user_id.in_(member_ids))
                ).all()
                user_id = member_ids[0] if member_ids else None

            if not enabled:
                with SessionLocal() as db:
                    db.add(
                        PushDeliveryModel(
                            user_id=user_id or "",
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

            if not devices:
                with SessionLocal() as db:
                    db.add(
                        PushDeliveryModel(
                            user_id=user_id or "",
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

            suggestion = self.get_latest_suggestion(household_id) or self.build_suggestion(household_id, UUID(user_id), mode="AUTO")
            with SessionLocal() as db:
                db.add(
                    PushDeliveryModel(
                        user_id=user_id or "",
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

        return {"processed_households": len(household_ids), "sent": sent, "failed": failed, "skipped": skipped}

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
