from __future__ import annotations

from dataclasses import dataclass

from core.store.audit import AuditStoreMixin
from core.store.analytics import AnalyticsStoreMixin
from core.store.calendar import CalendarStoreMixin
from core.store.categories import CategoryStoreMixin
from core.store.households import HouseholdStoreMixin
from core.store.inventory import InventoryStoreMixin
from core.store.meetings import MeetingStoreMixin
from core.store.offline import OfflineStoreMixin
from core.store.push import PushStoreMixin
from core.store.reports import ReportStoreMixin
from core.store.subscriptions import SubscriptionStoreMixin
from core.store.suggestions import SuggestionStoreMixin
from core.store.tasks import TaskStoreMixin
from core.store.users import UserStoreMixin
from core.store.weekly_reports import WeeklyReportStoreMixin


@dataclass
class Store(
    UserStoreMixin,
    InventoryStoreMixin,
    CategoryStoreMixin,
    HouseholdStoreMixin,
    OfflineStoreMixin,
    SuggestionStoreMixin,
    ReportStoreMixin,
    SubscriptionStoreMixin,
    AnalyticsStoreMixin,
    TaskStoreMixin,
    CalendarStoreMixin,
    MeetingStoreMixin,
    WeeklyReportStoreMixin,
    PushStoreMixin,
    AuditStoreMixin,
):
    pass


store = Store()
