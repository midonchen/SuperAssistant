from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ItemKey:
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
    household_id: str | None = None
    subscription_tier: str = "free"
    onboarded: bool


class InventoryItem(BaseModel):
    household_id: str
    item_key: str
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
    household_id: str
    item_key: str
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
    item_key: str
    operation: Operation
    value: float
    unit: str
    normalized_value: float
    normalized_unit: str
    confidence: float
    parse_session_id: str


class PurchaseSuggestionItem(BaseModel):
    item_key: str
    suggested_qty: float
    unit: str
    reason: str


class PurchaseSuggestion(BaseModel):
    suggestion_id: UUID
    household_id: str
    generated_at: datetime
    mode: str
    items: list[PurchaseSuggestionItem]
    status: str


class MonthlyReportEntry(BaseModel):
    item_key: str
    item_name: str
    unit: str
    consumed_qty: float
    wasted_qty: float
    turnover_days: float | None = None


class ConsumptionReport(BaseModel):
    report_id: str
    household_id: str
    month: str
    generated_at: datetime
    total_consumed_qty: float
    total_wasted_qty: float
    top_consumed: list[MonthlyReportEntry]
    wasted: list[MonthlyReportEntry]
    turnover: list[MonthlyReportEntry]
    suggested_purchase: list[PurchaseSuggestionItem]


class Category(BaseModel):
    category_id: str
    name: str
    icon: str | None = None
    unit_type: str
    decay_template: dict[str, Any] | None = None
    is_system: bool
    created_at: datetime


class CategoryCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=32)
    icon: str | None = Field(default=None, max_length=64)
    unit_type: str = Field(..., min_length=1, max_length=16)
    decay_template: dict[str, Any] | None = None


class CategoryUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=32)
    icon: str | None = Field(default=None, max_length=64)
    unit_type: str | None = Field(default=None, min_length=1, max_length=16)
    decay_template: dict[str, Any] | None = None


class HouseholdMember(BaseModel):
    user_id: UUID
    phone_masked: str
    role: str
    joined_at: datetime


class Household(BaseModel):
    household_id: str
    name: str
    created_by: UUID
    members: list[HouseholdMember]
    created_at: datetime


class HouseholdInvitation(BaseModel):
    invitation_id: str
    household_id: str
    invite_code: str
    status: str
    expires_at: datetime
    created_at: datetime


class HouseholdCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)


class HouseholdInviteRequest(BaseModel):
    role: str = Field(default="MEMBER")


class HouseholdJoinRequest(BaseModel):
    invite_code: str = Field(..., min_length=4, max_length=16)


class Task(BaseModel):
    task_id: str
    title: str
    description: str | None = None
    due_at: datetime | None = None
    priority: int = 3
    status: str = "TODO"
    created_at: datetime
    updated_at: datetime


class TaskCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=128)
    description: str | None = None
    due_at: datetime | None = None
    priority: int = Field(default=3, ge=1, le=4)


class TaskUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = None
    due_at: datetime | None = None
    priority: int | None = Field(default=None, ge=1, le=4)
    status: str | None = None


class PrioritizedTask(BaseModel):
    task_id: str
    title: str
    priority: int
    due_at: datetime | None = None
    status: str
    score: float
    reason: str


class CalendarEvent(BaseModel):
    event_id: str
    source: str
    title: str
    start_at: datetime
    end_at: datetime | None = None
    task_id: str | None = None
    meeting_id: str | None = None
    status: str | None = None
    priority: int | None = None


class CalendarEventList(BaseModel):
    events: list[CalendarEvent]


class MeetingActionItem(BaseModel):
    action_item_id: str
    meeting_id: str
    text: str
    assignee: str | None = None
    done: bool = False


class Meeting(BaseModel):
    meeting_id: str
    title: str
    transcript: str
    summary: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    action_items: list[MeetingActionItem] = []
    created_at: datetime


class MeetingCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=256)
    transcript: str = Field(..., min_length=1)
    started_at: datetime | None = None
    ended_at: datetime | None = None


class MeetingActionItemUpdateRequest(BaseModel):
    done: bool = Field(...)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
