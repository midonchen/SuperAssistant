from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ItemKey(str, Enum):
    EGG = "EGG"
    MILK = "MILK"
    MANTOU = "MANTOU"
    RICE = "RICE"
    PORK = "PORK"
    VEG = "VEG"


class InventoryStatus(str, Enum):
    PLENTY = "PLENTY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    EMPTY = "EMPTY"


class Operation(str, Enum):
    ADD = "ADD"
    SET = "SET"
    SUBTRACT = "SUBTRACT"
    CLEAR = "CLEAR"


class ActionType(str, Enum):
    OCR = "OCR"
    VOICE = "VOICE"
    MANUAL = "MANUAL"
    AUTO_DECAY = "AUTO_DECAY"
    CALIBRATE = "CALIBRATE"
    ADMIN_REVIEW = "ADMIN_REVIEW"


class ApiSuccess(BaseModel):
    code: str = "OK"
    message: str = "success"
    request_id: str
    timestamp: datetime
    data: dict[str, Any]


class ApiError(BaseModel):
    code: str
    message: str
    request_id: str
    timestamp: datetime
    details: dict[str, Any] | None = None
    retriable: bool = False


class UserProfile(BaseModel):
    user_id: UUID
    phone_masked: str
    timezone: str
    shopping_day: int
    shopping_cycle: int
    role: str
    onboarded: bool


class InventoryItem(BaseModel):
    item_key: ItemKey
    item_name: str
    unit: str
    current_stock: float
    max_stock: float
    warning_threshold: float
    status: InventoryStatus
    daily_avg_rate: float
    last_calibrated: datetime
    last_updated: datetime
    server_version: int = Field(ge=1)


class ActivityLog(BaseModel):
    activity_id: UUID
    item_key: ItemKey
    action_type: ActionType
    operation: Operation
    delta_value: float
    before_value: float
    after_value: float
    raw_text: str | None = None
    confidence: float | None = None
    operator_role: str | None = None
    timestamp: datetime


class ParsedEntity(BaseModel):
    item_key: ItemKey
    operation: Operation
    value: float
    unit: str
    normalized_value: float
    normalized_unit: str
    confidence: float
    parse_session_id: str


class PurchaseSuggestionItem(BaseModel):
    item_key: ItemKey
    suggested_qty: float
    unit: str
    reason: str


class PurchaseSuggestion(BaseModel):
    suggestion_id: UUID
    generated_at: datetime
    mode: str
    items: list[PurchaseSuggestionItem]
    status: str


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
