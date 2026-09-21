from __future__ import annotations

import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

TEST_DB = ROOT / "test_superassistant.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"

from fastapi.testclient import TestClient
import pytest

from core.db import engine
from core.models import Base
from core.offline_queue import offline_replay_queue
from main import app


HEADERS = {
    "X-Request-Id": "test-request-id",
    "X-App-Version": "1.1.0",
    "X-Platform": "ios",
}


def make_headers(idempotent: bool = False, token: str | None = None, idempotency_key: str | None = None) -> dict[str, str]:
    headers = dict(HEADERS)
    if idempotent or idempotency_key:
        headers["Idempotency-Key"] = idempotency_key or "test-idempotency-key"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


@pytest.fixture
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    offline_replay_queue.clear()
    with TestClient(app) as test_client:
        yield test_client
