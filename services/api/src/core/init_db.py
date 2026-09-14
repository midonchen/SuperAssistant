from __future__ import annotations

from core.db import engine
from core.models import Base


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
