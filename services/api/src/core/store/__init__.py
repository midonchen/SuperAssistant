from __future__ import annotations

from dataclasses import dataclass

from core.store.audit import AuditStoreMixin
from core.store.inventory import InventoryStoreMixin
from core.store.offline import OfflineStoreMixin
from core.store.push import PushStoreMixin
from core.store.suggestions import SuggestionStoreMixin
from core.store.users import UserStoreMixin


@dataclass
class Store(
    UserStoreMixin,
    InventoryStoreMixin,
    OfflineStoreMixin,
    SuggestionStoreMixin,
    PushStoreMixin,
    AuditStoreMixin,
):
    pass


store = Store()
