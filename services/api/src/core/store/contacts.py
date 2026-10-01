from __future__ import annotations

import uuid
from datetime import date, datetime, time, timezone

from sqlalchemy import delete, func, select

from core.db import SessionLocal
from core.errors import ApiException
from core.models import ContactModel, OccasionModel, PushDeliveryModel
from core.schemas import (
    CalendarEvent,
    Contact,
    ContactCreateRequest,
    ContactUpdateRequest,
    Occasion,
    OccasionCreateRequest,
    utc_now,
)
from core.store.base import StoreBase


def next_occurrence(month: int, day: int, today: date) -> date:
    def _d(year: int) -> date:
        try:
            return date(year, month, day)
        except ValueError:
            return date(year, month, 28)

    result = _d(today.year)
    if result < today:
        result = _d(today.year + 1)
    return result


class ContactStoreMixin(StoreBase):
    def _contact(self, row: ContactModel) -> Contact:
        return Contact(
            contact_id=row.id,
            name=row.name,
            relationship=row.relationship,
            birthday=row.birthday,
            preferences=row.preferences,
            notes=row.notes,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _occasion(self, row: OccasionModel) -> Occasion:
        return Occasion(
            occasion_id=row.id,
            contact_id=row.contact_id,
            name=row.name,
            month=row.month,
            day=row.day,
            is_lunar=row.is_lunar,
            remind_days_before=row.remind_days_before,
        )

    def _count_contacts(self, user_id: str) -> int:
        with SessionLocal() as db:
            return db.scalar(select(func.count()).select_from(ContactModel).where(ContactModel.user_id == user_id)) or 0

    def _count_occasions(self, user_id: str) -> int:
        with SessionLocal() as db:
            return db.scalar(select(func.count()).select_from(OccasionModel).where(OccasionModel.user_id == user_id)) or 0

    def create_contact(self, user_id: str, request: ContactCreateRequest) -> Contact:
        if not self.can_use_feature(user_id, "contacts", self._count_contacts(user_id)):
            self.record_event(user_id, "subscription_gate_hit", {"feature": "contacts"})
            raise ApiException(402, "BIZ_402_UPGRADE_REQUIRED", "free tier contact limit reached")
        with SessionLocal() as db:
            contact = ContactModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                name=request.name,
                relationship=request.relationship,
                birthday=request.birthday,
                preferences=request.preferences,
                notes=request.notes,
            )
            db.add(contact)
            db.flush()
            if request.birthday:
                month, day = (int(x) for x in request.birthday.split("-"))
                db.add(
                    OccasionModel(
                        id=str(uuid.uuid4()),
                        contact_id=contact.id,
                        user_id=user_id,
                        name="生日",
                        month=month,
                        day=day,
                        is_lunar=False,
                        remind_days_before=3,
                    )
                )
            db.commit()
            db.refresh(contact)
            return self._contact(contact)

    def list_contacts(self, user_id: str) -> list[Contact]:
        with SessionLocal() as db:
            rows = db.scalars(
                select(ContactModel).where(ContactModel.user_id == user_id).order_by(ContactModel.created_at.desc())
            ).all()
            return [self._contact(r) for r in rows]

    def get_contact(self, user_id: str, contact_id: str) -> Contact:
        with SessionLocal() as db:
            row = db.scalar(select(ContactModel).where(ContactModel.id == contact_id, ContactModel.user_id == user_id))
            if row is None:
                raise KeyError("contact not found")
            return self._contact(row)

    def update_contact(self, user_id: str, contact_id: str, request: ContactUpdateRequest) -> Contact:
        with SessionLocal() as db:
            row = db.scalar(select(ContactModel).where(ContactModel.id == contact_id, ContactModel.user_id == user_id))
            if row is None:
                raise KeyError("contact not found")
            if request.name is not None:
                row.name = request.name
            if request.relationship is not None:
                row.relationship = request.relationship
            if request.birthday is not None:
                row.birthday = request.birthday
            if request.preferences is not None:
                row.preferences = request.preferences
            if request.notes is not None:
                row.notes = request.notes
            row.updated_at = utc_now()
            db.commit()
            db.refresh(row)
            return self._contact(row)

    def delete_contact(self, user_id: str, contact_id: str) -> None:
        with SessionLocal() as db:
            row = db.scalar(select(ContactModel).where(ContactModel.id == contact_id, ContactModel.user_id == user_id))
            if row is None:
                raise KeyError("contact not found")
            db.execute(delete(OccasionModel).where(OccasionModel.contact_id == contact_id))
            db.delete(row)
            db.commit()

    def create_occasion(self, user_id: str, contact_id: str, request: OccasionCreateRequest) -> Occasion:
        if not self.can_use_feature(user_id, "occasions", self._count_occasions(user_id)):
            self.record_event(user_id, "subscription_gate_hit", {"feature": "occasions"})
            raise ApiException(402, "BIZ_402_UPGRADE_REQUIRED", "free tier occasion limit reached")
        with SessionLocal() as db:
            contact = db.scalar(select(ContactModel).where(ContactModel.id == contact_id, ContactModel.user_id == user_id))
            if contact is None:
                raise KeyError("contact not found")
            occasion = OccasionModel(
                id=str(uuid.uuid4()),
                contact_id=contact_id,
                user_id=user_id,
                name=request.name,
                month=request.month,
                day=request.day,
                is_lunar=request.is_lunar,
                remind_days_before=request.remind_days_before,
            )
            db.add(occasion)
            db.commit()
            db.refresh(occasion)
            return self._occasion(occasion)

    def list_occasions(self, user_id: str, contact_id: str | None = None) -> list[Occasion]:
        with SessionLocal() as db:
            stmt = select(OccasionModel).where(OccasionModel.user_id == user_id)
            if contact_id:
                stmt = stmt.where(OccasionModel.contact_id == contact_id)
            stmt = stmt.order_by(OccasionModel.month.asc(), OccasionModel.day.asc())
            return [self._occasion(r) for r in db.scalars(stmt).all()]

    def delete_occasion(self, user_id: str, occasion_id: str) -> None:
        with SessionLocal() as db:
            row = db.scalar(select(OccasionModel).where(OccasionModel.id == occasion_id, OccasionModel.user_id == user_id))
            if row is None:
                raise KeyError("occasion not found")
            db.delete(row)
            db.commit()

    def occasion_events(self, user_id: str, start: datetime, end: datetime) -> list[CalendarEvent]:
        with SessionLocal() as db:
            occasions = db.scalars(select(OccasionModel).where(OccasionModel.user_id == user_id)).all()
            contacts = {c.id: c.name for c in db.scalars(select(ContactModel).where(ContactModel.user_id == user_id)).all()}
        events: list[CalendarEvent] = []
        for year in range(start.year, end.year + 1):
            for occ in occasions:
                try:
                    d = date(year, occ.month, occ.day)
                except ValueError:
                    continue
                dt = datetime.combine(d, time.min, tzinfo=timezone.utc)
                if start <= dt < end:
                    events.append(
                        CalendarEvent(
                            event_id=f"occasion:{occ.id}:{year}",
                            source="occasion",
                            title=f"{occ.name} · {contacts.get(occ.contact_id, '')}",
                            start_at=dt,
                            end_at=None,
                            task_id=None,
                            meeting_id=None,
                            status=None,
                            priority=None,
                        )
                    )
        return events

    def run_occasion_reminders_for_all(self) -> dict:
        today = date.today()
        due = []
        with SessionLocal() as db:
            occasions = db.scalars(select(OccasionModel)).all()
            contacts = {c.id: c.name for c in db.scalars(select(ContactModel)).all()}
        for occ in occasions:
            nxt = next_occurrence(occ.month, occ.day, today)
            days_left = (nxt - today).days
            if 0 <= days_left <= occ.remind_days_before:
                due.append({"user_id": occ.user_id, "name": occ.name, "contact": contacts.get(occ.contact_id, "")})
        with SessionLocal() as db:
            for item in due:
                db.add(
                    PushDeliveryModel(
                        user_id=item["user_id"],
                        suggestion_id=None,
                        status="SENT",
                        attempt_count=1,
                        error_message=f"occasion reminder: {item['name']} · {item['contact']}",
                        created_at=utc_now(),
                        delivered_at=utc_now(),
                    )
                )
            db.commit()
        return {"sent": len(due)}
