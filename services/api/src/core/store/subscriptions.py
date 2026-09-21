from __future__ import annotations

from sqlalchemy import select

from core.db import SessionLocal
from core.models import SubscriptionTierModel, UserModel
from core.store.base import StoreBase


DEFAULT_FREE_LIMITS: dict = {"custom_categories": 3, "household_members": 2}


class SubscriptionStoreMixin(StoreBase):
    def get_subscription_tier(self, user_id: str) -> str:
        with SessionLocal() as db:
            user = db.scalar(select(UserModel).where(UserModel.id == user_id))
            return user.subscription_tier_id if (user and user.subscription_tier_id) else "free"

    def get_tier_limits(self, user_id: str) -> dict | None:
        """Return the tier's feature limits, or None when unlimited (Pro)."""
        tier_id = self.get_subscription_tier(user_id)
        with SessionLocal() as db:
            tier = db.scalar(select(SubscriptionTierModel).where(SubscriptionTierModel.id == tier_id))
            if tier is None:
                return DEFAULT_FREE_LIMITS
            return tier.limits

    def can_use_feature(self, user_id: str, feature: str, current_count: int) -> bool:
        """True when the user's tier allows one more use of `feature` (given `current_count`)."""
        limits = self.get_tier_limits(user_id)
        if limits is None:
            return True
        limit = limits.get(feature)
        if limit is None:
            return True
        return current_count < limit
