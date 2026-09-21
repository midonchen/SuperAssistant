from __future__ import annotations

import os
from uuid import UUID

from core.models import (
    ActivityLogModel,
    CategoryModel,
    InventoryItemModel,
    SuggestionItemModel,
    SuggestionModel,
    UserModel,
)
from core.schemas import (
    ActionType,
    ActivityLog,
    Category,
    InventoryItem,
    InventoryStatus,
    ItemKey,
    Operation,
    PurchaseSuggestion,
    PurchaseSuggestionItem,
    UserProfile,
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


class StoreBase:
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
            household_id=user.household_id,
            onboarded=user.onboarded,
        )

    def _inventory_item(self, row: InventoryItemModel) -> InventoryItem:
        return InventoryItem(
            household_id=row.household_id,
            item_key=row.item_key,
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
            household_id=row.household_id,
            item_key=row.item_key,
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
            household_id=suggestion.household_id,
            generated_at=suggestion.generated_at,
            mode=suggestion.mode,
            status=suggestion.status,
            items=[
                PurchaseSuggestionItem(
                    item_key=item.item_key,
                    suggested_qty=item.suggested_qty,
                    unit=item.unit,
                    reason=item.reason,
                )
                for item in items
            ],
        )

    def _category(self, row: CategoryModel) -> Category:
        return Category(
            category_id=row.id,
            name=row.name,
            icon=row.icon,
            unit_type=row.unit_type,
            decay_template=row.decay_template,
            is_system=row.is_system,
            created_at=row.created_at,
        )

    def _status_for(self, current_stock: float, warning_threshold: float) -> str:
        if current_stock <= 0:
            return InventoryStatus.EMPTY.value
        if current_stock <= warning_threshold:
            return InventoryStatus.CRITICAL.value
        if current_stock <= warning_threshold * 2:
            return InventoryStatus.WARNING.value
        return InventoryStatus.PLENTY.value
