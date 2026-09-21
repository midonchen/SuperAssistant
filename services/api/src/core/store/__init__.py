from __future__ import annotations

from dataclasses import dataclass

from core.store.audit import AuditStoreMixin
from core.store.categories import CategoryStoreMixin
from core.store.households import HouseholdStoreMixin
from core.store.inventory import InventoryStoreMixin
from core.store.offline import OfflineStoreMixin
from core.store.push import PushStoreMixin
from core.store.reports import ReportStoreMixin
from core.store.suggestions import SuggestionStoreMixin
from core.store.users import UserStoreMixin


@dataclass
class Store(
    UserStoreMixin,
    InventoryStoreMixin,
    CategoryStoreMixin,
    HouseholdStoreMixin,
    OfflineStoreMixin,
    SuggestionStoreMixin,
    ReportStoreMixin,
    PushStoreMixin,
    AuditStoreMixin,
):
    pass


store = Store()
