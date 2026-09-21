from __future__ import annotations

from datetime import datetime, timezone
import uuid

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    phone: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    phone_masked: Mapped[str] = mapped_column(String(32))
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Shanghai")
    shopping_day: Mapped[int] = mapped_column(Integer, default=6)
    shopping_cycle: Mapped[int] = mapped_column(Integer, default=7)
    role: Mapped[str] = mapped_column(String(16), default="USER", index=True)
    household_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("households.id"), nullable=True, index=True)
    subscription_tier_id: Mapped[str] = mapped_column(String(16), ForeignKey("subscription_tiers.id"), default="free", index=True)
    onboarded: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class SessionModel(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    access_token: Mapped[str] = mapped_column(String(96), unique=True, index=True)
    refresh_token: Mapped[str] = mapped_column(String(96), unique=True, index=True)
    device_id: Mapped[str] = mapped_column(String(128), default="unknown")
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class InventoryItemModel(Base):
    __tablename__ = "inventory_items"
    __table_args__ = (UniqueConstraint("household_id", "item_key", name="uq_inventory_household_item"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    household_id: Mapped[str] = mapped_column(String(36), ForeignKey("households.id"), index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    item_key: Mapped[str] = mapped_column(String(16), index=True)
    item_name: Mapped[str] = mapped_column(String(32))
    unit: Mapped[str] = mapped_column(String(16))
    current_stock: Mapped[float] = mapped_column(Float)
    max_stock: Mapped[float] = mapped_column(Float)
    warning_threshold: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(16))
    daily_avg_rate: Mapped[float] = mapped_column(Float)
    last_calibrated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    server_version: Mapped[int] = mapped_column(Integer, default=1)


class ActivityLogModel(Base):
    __tablename__ = "activity_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    household_id: Mapped[str] = mapped_column(String(36), ForeignKey("households.id"), index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    item_key: Mapped[str] = mapped_column(String(16), index=True)
    action_type: Mapped[str] = mapped_column(String(24))
    operation: Mapped[str] = mapped_column(String(16))
    delta_value: Mapped[float] = mapped_column(Float)
    before_value: Mapped[float] = mapped_column(Float)
    after_value: Mapped[float] = mapped_column(Float)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    operator_role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class SuggestionModel(Base):
    __tablename__ = "purchase_suggestions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    household_id: Mapped[str] = mapped_column(String(36), ForeignKey("households.id"), index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    mode: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="PENDING")


class SuggestionItemModel(Base):
    __tablename__ = "purchase_suggestion_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    suggestion_id: Mapped[str] = mapped_column(String(36), ForeignKey("purchase_suggestions.id"), index=True)
    item_key: Mapped[str] = mapped_column(String(16))
    suggested_qty: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(16))
    reason: Mapped[str] = mapped_column(String(256))


class AuditTaskModel(Base):
    __tablename__ = "audit_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    parse_session_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(16), default="PENDING", index=True)
    entities: Mapped[list[dict]] = mapped_column(JSON)
    review_action: Mapped[str | None] = mapped_column(String(16), nullable=True)
    corrected_entities: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PushDeviceModel(Base):
    __tablename__ = "push_devices"
    __table_args__ = (UniqueConstraint("user_id", "device_token", name="uq_push_device_user_token"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    platform: Mapped[str] = mapped_column(String(16))
    device_token: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class PushPreferenceModel(Base):
    __tablename__ = "push_preferences"
    __table_args__ = (UniqueConstraint("user_id", name="uq_push_preference_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_time: Mapped[str] = mapped_column(String(8), default="20:00")
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Shanghai")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class PushDeliveryModel(Base):
    __tablename__ = "push_deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    suggestion_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("purchase_suggestions.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(16), index=True)  # SENT/FAILED/SKIPPED
    attempt_count: Mapped[int] = mapped_column(Integer, default=1)
    error_message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SecurityEventModel(Base):
    __tablename__ = "security_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(32), index=True)
    details: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class ApprovalRequestModel(Base):
    __tablename__ = "approval_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    action_type: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(16), default="PENDING", index=True)
    target_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    requested_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    request_payload: Mapped[dict] = mapped_column(JSON)
    review_comment: Mapped[str | None] = mapped_column(String(255), nullable=True)
    execution_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)


class CategoryModel(Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("household_id", "item_key", name="uq_category_household_item_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    household_id: Mapped[str] = mapped_column(String(36), ForeignKey("households.id"), index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    item_key: Mapped[str] = mapped_column(String(16), index=True)
    name: Mapped[str] = mapped_column(String(32))
    icon: Mapped[str | None] = mapped_column(String(64), nullable=True)
    unit_type: Mapped[str] = mapped_column(String(16))
    decay_template: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class HouseholdModel(Base):
    __tablename__ = "households"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(64))
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class HouseholdMembershipModel(Base):
    __tablename__ = "household_memberships"
    __table_args__ = (UniqueConstraint("household_id", "user_id", name="uq_household_membership"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    household_id: Mapped[str] = mapped_column(String(36), ForeignKey("households.id"), index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(16), default="MEMBER")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class HouseholdInvitationModel(Base):
    __tablename__ = "household_invitations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    household_id: Mapped[str] = mapped_column(String(36), ForeignKey("households.id"), index=True)
    inviter_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    invite_code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(16), default="MEMBER")  # ADMIN, MEMBER, VIEWER
    status: Mapped[str] = mapped_column(String(16), default="PENDING")  # PENDING, ACCEPTED, EXPIRED
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ConsumptionReportModel(Base):
    __tablename__ = "consumption_reports"
    __table_args__ = (UniqueConstraint("household_id", "month", name="uq_consumption_report_household_month"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    household_id: Mapped[str] = mapped_column(String(36), ForeignKey("households.id"), index=True)
    month: Mapped[str] = mapped_column(String(7), index=True)  # YYYY-MM
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class SubscriptionTierModel(Base):
    __tablename__ = "subscription_tiers"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)  # "free", "pro"
    name: Mapped[str] = mapped_column(String(32))
    monthly_price: Mapped[float] = mapped_column(Float, default=0.0)
    limits: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # None = unlimited
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AnalyticsEventModel(Base):
    __tablename__ = "analytics_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    household_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    event_type: Mapped[str] = mapped_column(String(32), index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class TaskModel(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(128))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=3)  # 1=最高 ... 4=最低
    status: Mapped[str] = mapped_column(String(16), default="TODO", index=True)  # TODO/IN_PROGRESS/DONE
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class MeetingModel(Base):
    __tablename__ = "meetings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(256))
    transcript: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class MeetingActionItemModel(Base):
    __tablename__ = "meeting_action_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id: Mapped[str] = mapped_column(String(36), ForeignKey("meetings.id"), index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    assignee: Mapped[str | None] = mapped_column(String(128), nullable=True)
    done: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
