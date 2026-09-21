from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import delete, func, select

from core.db import SessionLocal
from core.errors import ApiException
from core.models import (
    HouseholdInvitationModel,
    HouseholdMembershipModel,
    HouseholdModel,
    UserModel,
)
from core.schemas import Household, HouseholdCreateRequest, HouseholdInvitation, HouseholdMember, utc_now
from core.store.base import StoreBase


def _naive_utc(dt: datetime) -> datetime:
    """SQLite may return naive datetimes; treat them as UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class HouseholdStoreMixin(StoreBase):
    def _require_household_role(self, user_id: str, household_id: str, allowed_roles: set[str]) -> None:
        with SessionLocal() as db:
            membership = db.scalar(
                select(HouseholdMembershipModel).where(
                    HouseholdMembershipModel.household_id == household_id,
                    HouseholdMembershipModel.user_id == user_id,
                )
            )
            if membership is None:
                raise ApiException(403, "AUTH_403_FORBIDDEN", "not a household member")
            if membership.role not in allowed_roles:
                raise ApiException(403, "AUTH_403_FORBIDDEN", "insufficient household role")

    def get_user_household_id(self, user_id: str) -> str | None:
        with SessionLocal() as db:
            user = db.scalar(select(UserModel).where(UserModel.id == user_id))
            return user.household_id if user else None

    def ensure_personal_household(self, user_id: str, phone_masked: str) -> str:
        with SessionLocal() as db:
            user = db.scalar(select(UserModel).where(UserModel.id == user_id))
            if user is None:
                raise KeyError("user not found")
            if user.household_id:
                return user.household_id
            household = HouseholdModel(
                id=str(uuid.uuid4()),
                name=f"{phone_masked}的家庭",
                created_by=user_id,
            )
            db.add(household)
            db.flush()
            membership = HouseholdMembershipModel(
                id=str(uuid.uuid4()),
                household_id=household.id,
                user_id=user_id,
                role="OWNER",
            )
            db.add(membership)
            user.household_id = household.id
            db.commit()
            return household.id

    def get_household(self, user_id: str) -> Household:
        household_id = self.get_user_household_id(user_id)
        if household_id is None:
            raise KeyError("household not found")
        with SessionLocal() as db:
            household = db.scalar(select(HouseholdModel).where(HouseholdModel.id == household_id))
            if household is None:
                raise KeyError("household not found")
            members = db.scalars(
                select(HouseholdMembershipModel).where(HouseholdMembershipModel.household_id == household_id)
            ).all()
            user_ids = [member.user_id for member in members]
            users = {
                row.id: row
                for row in db.scalars(select(UserModel).where(UserModel.id.in_(user_ids))).all()
            }
            return Household(
                household_id=household.id,
                name=household.name,
                created_by=UUID(household.created_by),
                members=[
                    HouseholdMember(
                        user_id=UUID(member.user_id),
                        phone_masked=users[member.user_id].phone_masked,
                        role=member.role,
                        joined_at=member.created_at,
                    )
                    for member in members
                    if member.user_id in users
                ],
                created_at=household.created_at,
            )

    def create_household(self, user_id: str, request: HouseholdCreateRequest) -> Household:
        current_household_id = self.get_user_household_id(user_id)
        if current_household_id is not None:
            existing = self.get_household(user_id)
            if len(existing.members) > 1:
                raise ApiException(409, "BIZ_409_CONFLICT", "leave current household before creating a new one")
        with SessionLocal() as db:
            user = db.scalar(select(UserModel).where(UserModel.id == user_id))
            if user is None:
                raise KeyError("user not found")
            household = HouseholdModel(
                id=str(uuid.uuid4()),
                name=request.name,
                created_by=user_id,
            )
            db.add(household)
            db.flush()
            # Remove existing single-member household membership if any.
            if current_household_id:
                db.execute(
                    delete(HouseholdMembershipModel).where(
                        HouseholdMembershipModel.household_id == current_household_id,
                        HouseholdMembershipModel.user_id == user_id,
                    )
                )
            membership = HouseholdMembershipModel(
                id=str(uuid.uuid4()),
                household_id=household.id,
                user_id=user_id,
                role="OWNER",
            )
            db.add(membership)
            user.household_id = household.id
            db.commit()
            return self.get_household(user_id)

    def create_invitation(self, user_id: str, role: str = "MEMBER") -> HouseholdInvitation:
        household_id = self.get_user_household_id(user_id)
        if household_id is None:
            raise KeyError("household not found")
        self._require_household_role(user_id, household_id, {"OWNER", "ADMIN"})
        if role not in {"ADMIN", "MEMBER", "VIEWER"}:
            raise ApiException(400, "VAL_400_INVALID_PARAM", "invalid household role")
        with SessionLocal() as db:
            invite_code = secrets.token_urlsafe(8)[:8].upper()
            while db.scalar(select(HouseholdInvitationModel).where(HouseholdInvitationModel.invite_code == invite_code)):
                invite_code = secrets.token_urlsafe(8)[:8].upper()
            invitation = HouseholdInvitationModel(
                id=str(uuid.uuid4()),
                household_id=household_id,
                inviter_id=user_id,
                invite_code=invite_code,
                role=role,
                status="PENDING",
                expires_at=utc_now() + timedelta(days=7),
            )
            db.add(invitation)
            db.commit()
            db.refresh(invitation)
            return self._invitation(invitation)

    def _invitation(self, row: HouseholdInvitationModel) -> HouseholdInvitation:
        return HouseholdInvitation(
            invitation_id=row.id,
            household_id=row.household_id,
            invite_code=row.invite_code,
            status=row.status,
            expires_at=row.expires_at,
            created_at=row.created_at,
        )

    def join_household(self, user_id: str, invite_code: str) -> Household:
        with SessionLocal() as db:
            invitation = db.scalar(
                select(HouseholdInvitationModel).where(
                    HouseholdInvitationModel.invite_code == invite_code.upper(),
                    HouseholdInvitationModel.status == "PENDING",
                )
            )
            if invitation is None:
                raise ApiException(404, "BIZ_404_NOT_FOUND", "invitation not found")
            if _naive_utc(invitation.expires_at) < utc_now():
                invitation.status = "EXPIRED"
                db.commit()
                raise ApiException(410, "BIZ_410_GONE", "invitation expired")
            user = db.scalar(select(UserModel).where(UserModel.id == user_id))
            if user is None:
                raise KeyError("user not found")
            # Leave current personal household if it has only this user.
            if user.household_id and user.household_id != invitation.household_id:
                current_members = int(
                    db.scalar(
                        select(func.count())
                        .select_from(HouseholdMembershipModel)
                        .where(HouseholdMembershipModel.household_id == user.household_id)
                    )
                    or 0
                )
                if current_members == 1:
                    db.execute(
                        delete(HouseholdMembershipModel).where(
                            HouseholdMembershipModel.household_id == user.household_id,
                            HouseholdMembershipModel.user_id == user_id,
                        )
                    )
            existing = db.scalar(
                select(HouseholdMembershipModel).where(
                    HouseholdMembershipModel.household_id == invitation.household_id,
                    HouseholdMembershipModel.user_id == user_id,
                )
            )
            if existing is None:
                db.add(
                    HouseholdMembershipModel(
                        id=str(uuid.uuid4()),
                        household_id=invitation.household_id,
                        user_id=user_id,
                        role=invitation.role,
                    )
                )
            user.household_id = invitation.household_id
            invitation.status = "ACCEPTED"
            db.commit()
            return self.get_household(user_id)

    def can_write_inventory(self, user_id: str, household_id: str) -> bool:
        with SessionLocal() as db:
            membership = db.scalar(
                select(HouseholdMembershipModel).where(
                    HouseholdMembershipModel.household_id == household_id,
                    HouseholdMembershipModel.user_id == user_id,
                )
            )
            if membership is None:
                return False
            return membership.role in {"OWNER", "ADMIN", "MEMBER"}

    def list_household_ids(self) -> list[str]:
        with SessionLocal() as db:
            rows = db.scalars(select(HouseholdModel.id)).all()
            return [str(row) for row in rows]
