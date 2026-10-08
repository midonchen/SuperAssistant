from __future__ import annotations

import calendar
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select

from core.db import SessionLocal
from core.errors import ApiException
from core.models import BillReminderModel, HealthReminderModel, PushDeliveryModel
from core.schemas import (
    BillReminder,
    BillReminderCreateRequest,
    BillReminderUpdateRequest,
    HealthReminder,
    HealthReminderCreateRequest,
    HealthReminderUpdateRequest,
    utc_now,
)
from core.store.base import StoreBase


def _add_months(d: date, months: int) -> date:
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(d.day, last))


class HealthReminderStoreMixin(StoreBase):
    def _health(self, row: HealthReminderModel) -> HealthReminder:
        return HealthReminder(
            reminder_id=row.id,
            household_id=row.household_id,
            member_name=row.member_name,
            reminder_type=row.reminder_type,
            title=row.title,
            period_days=row.period_days,
            next_due_at=row.next_due_at,
            enabled=row.enabled,
            notes=row.notes,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _require_reminder_write(self, user_id: str) -> str:
        household_id = self.get_user_household_id(user_id)
        if household_id is None:
            raise ApiException(403, "AUTH_403_FORBIDDEN", "user has no household")
        if not self.can_write_inventory(user_id, household_id):
            raise ApiException(403, "AUTH_403_FORBIDDEN", "insufficient household role")
        return household_id

    def _count_health(self, user_id: str) -> int:
        with SessionLocal() as db:
            return (
                db.scalar(
                    select(func.count())
                    .select_from(HealthReminderModel)
                    .where(HealthReminderModel.user_id == user_id)
                )
                or 0
            )

    def create_health_reminder(self, user_id: str, request: HealthReminderCreateRequest) -> HealthReminder:
        if not self.can_use_feature(user_id, "health_reminders", self._count_health(user_id)):
            self.record_event(user_id, "subscription_gate_hit", {"feature": "health_reminders"})
            raise ApiException(402, "BIZ_402_UPGRADE_REQUIRED", "free tier health reminder limit reached")
        if request.reminder_type not in {"medication", "checkup", "followup"}:
            raise ApiException(400, "VAL_400_INVALID_PARAM", "invalid reminder type")
        household_id = self._require_reminder_write(user_id)
        with SessionLocal() as db:
            row = HealthReminderModel(
                id=str(uuid.uuid4()),
                household_id=household_id,
                user_id=user_id,
                member_name=request.member_name,
                reminder_type=request.reminder_type,
                title=request.title,
                period_days=request.period_days,
                next_due_at=request.next_due_at or utc_now(),
                notes=request.notes,
                enabled=True,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._health(row)

    def list_health_reminders(self, user_id: str) -> list[HealthReminder]:
        household_id = self.get_user_household_id(user_id)
        if household_id is None:
            return []
        with SessionLocal() as db:
            rows = db.scalars(
                select(HealthReminderModel)
                .where(HealthReminderModel.household_id == household_id)
                .order_by(HealthReminderModel.created_at.desc())
            ).all()
            return [self._health(r) for r in rows]

    def update_health_reminder(self, user_id: str, reminder_id: str, request: HealthReminderUpdateRequest) -> HealthReminder:
        household_id = self._require_reminder_write(user_id)
        with SessionLocal() as db:
            row = db.scalar(
                select(HealthReminderModel).where(
                    HealthReminderModel.id == reminder_id,
                    HealthReminderModel.household_id == household_id,
                )
            )
            if row is None:
                raise KeyError("health reminder not found")
            if request.member_name is not None:
                row.member_name = request.member_name
            if request.reminder_type is not None:
                if request.reminder_type not in {"medication", "checkup", "followup"}:
                    raise ApiException(400, "VAL_400_INVALID_PARAM", "invalid reminder type")
                row.reminder_type = request.reminder_type
            if request.title is not None:
                row.title = request.title
            if request.period_days is not None:
                row.period_days = request.period_days
            if request.next_due_at is not None:
                row.next_due_at = request.next_due_at
            if request.enabled is not None:
                row.enabled = request.enabled
            if request.notes is not None:
                row.notes = request.notes
            row.updated_at = utc_now()
            db.commit()
            db.refresh(row)
            return self._health(row)

    def delete_health_reminder(self, user_id: str, reminder_id: str) -> None:
        household_id = self._require_reminder_write(user_id)
        with SessionLocal() as db:
            row = db.scalar(
                select(HealthReminderModel).where(
                    HealthReminderModel.id == reminder_id,
                    HealthReminderModel.household_id == household_id,
                )
            )
            if row is None:
                raise KeyError("health reminder not found")
            db.delete(row)
            db.commit()

    def run_health_reminders_for_all(self) -> dict:
        today = date.today()
        with SessionLocal() as db:
            rows = db.scalars(
                select(HealthReminderModel).where(
                    HealthReminderModel.enabled.is_(True),
                    HealthReminderModel.next_due_at.isnot(None),
                )
            ).all()
            sent = 0
            for row in rows:
                if row.next_due_at is None or row.next_due_at.date() > today:
                    continue
                db.add(
                    PushDeliveryModel(
                        user_id=row.user_id,
                        suggestion_id=None,
                        status="SENT",
                        attempt_count=1,
                        error_message=f"health reminder: {row.member_name} · {row.title}",
                        created_at=utc_now(),
                        delivered_at=utc_now(),
                    )
                )
                d = row.next_due_at.date()
                while d <= today:
                    d = d + timedelta(days=row.period_days)
                row.next_due_at = datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc)
                sent += 1
            db.commit()
        return {"sent": sent}


class BillReminderStoreMixin(StoreBase):
    def _bill(self, row: BillReminderModel) -> BillReminder:
        return BillReminder(
            reminder_id=row.id,
            household_id=row.household_id,
            name=row.name,
            amount=row.amount,
            period_months=row.period_months,
            next_due_at=row.next_due_at,
            enabled=row.enabled,
            notes=row.notes,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _count_bills(self, user_id: str) -> int:
        with SessionLocal() as db:
            return (
                db.scalar(
                    select(func.count())
                    .select_from(BillReminderModel)
                    .where(BillReminderModel.user_id == user_id)
                )
                or 0
            )

    def create_bill_reminder(self, user_id: str, request: BillReminderCreateRequest) -> BillReminder:
        if not self.can_use_feature(user_id, "bill_reminders", self._count_bills(user_id)):
            self.record_event(user_id, "subscription_gate_hit", {"feature": "bill_reminders"})
            raise ApiException(402, "BIZ_402_UPGRADE_REQUIRED", "free tier bill reminder limit reached")
        household_id = self._require_reminder_write(user_id)
        with SessionLocal() as db:
            row = BillReminderModel(
                id=str(uuid.uuid4()),
                household_id=household_id,
                user_id=user_id,
                name=request.name,
                amount=request.amount,
                period_months=request.period_months,
                next_due_at=request.next_due_at or utc_now(),
                notes=request.notes,
                enabled=True,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._bill(row)

    def list_bill_reminders(self, user_id: str) -> list[BillReminder]:
        household_id = self.get_user_household_id(user_id)
        if household_id is None:
            return []
        with SessionLocal() as db:
            rows = db.scalars(
                select(BillReminderModel)
                .where(BillReminderModel.household_id == household_id)
                .order_by(BillReminderModel.created_at.desc())
            ).all()
            return [self._bill(r) for r in rows]

    def update_bill_reminder(self, user_id: str, reminder_id: str, request: BillReminderUpdateRequest) -> BillReminder:
        household_id = self._require_reminder_write(user_id)
        with SessionLocal() as db:
            row = db.scalar(
                select(BillReminderModel).where(
                    BillReminderModel.id == reminder_id,
                    BillReminderModel.household_id == household_id,
                )
            )
            if row is None:
                raise KeyError("bill reminder not found")
            if request.name is not None:
                row.name = request.name
            if request.amount is not None:
                row.amount = request.amount
            if request.period_months is not None:
                row.period_months = request.period_months
            if request.next_due_at is not None:
                row.next_due_at = request.next_due_at
            if request.enabled is not None:
                row.enabled = request.enabled
            if request.notes is not None:
                row.notes = request.notes
            row.updated_at = utc_now()
            db.commit()
            db.refresh(row)
            return self._bill(row)

    def delete_bill_reminder(self, user_id: str, reminder_id: str) -> None:
        household_id = self._require_reminder_write(user_id)
        with SessionLocal() as db:
            row = db.scalar(
                select(BillReminderModel).where(
                    BillReminderModel.id == reminder_id,
                    BillReminderModel.household_id == household_id,
                )
            )
            if row is None:
                raise KeyError("bill reminder not found")
            db.delete(row)
            db.commit()

    def run_bill_reminders_for_all(self) -> dict:
        today = date.today()
        with SessionLocal() as db:
            rows = db.scalars(
                select(BillReminderModel).where(
                    BillReminderModel.enabled.is_(True),
                    BillReminderModel.next_due_at.isnot(None),
                )
            ).all()
            sent = 0
            for row in rows:
                if row.next_due_at is None or row.next_due_at.date() > today:
                    continue
                db.add(
                    PushDeliveryModel(
                        user_id=row.user_id,
                        suggestion_id=None,
                        status="SENT",
                        attempt_count=1,
                        error_message=f"bill reminder: {row.name}" + (f"（{row.amount:.0f}元）" if row.amount else ""),
                        created_at=utc_now(),
                        delivered_at=utc_now(),
                    )
                )
                d = row.next_due_at.date()
                while d <= today:
                    d = _add_months(d, row.period_months)
                row.next_due_at = datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc)
                sent += 1
            db.commit()
        return {"sent": sent}
