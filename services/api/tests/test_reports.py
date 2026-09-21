from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from conftest import make_headers
from core.store import store


def _current_month() -> str:
    now = datetime.now(timezone.utc)
    return f"{now.year:04d}-{now.month:02d}"


@pytest.fixture
def alice(client: TestClient) -> tuple[TestClient, str, str, str]:
    resp = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": "+861****0001", "code": "123456", "device_id": "device-alice"},
        headers=make_headers(idempotency_key="alice-login"),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    profile = data["user_profile"]
    return client, data["access_token"], profile["user_id"], profile["household_id"]


def test_monthly_report_structure(alice):
    client, token, user_id, household_id = alice
    resp = client.get("/api/v1/reports/consumption/monthly", headers=make_headers(token=token))
    assert resp.status_code == 200
    report = resp.json()["data"]["report"]
    assert report["household_id"] == household_id
    assert report["month"]
    assert "top_consumed" in report
    assert "wasted" in report
    assert "turnover" in report
    assert "suggested_purchase" in report


def test_report_reflects_consumption(alice):
    client, token, user_id, household_id = alice
    client.post(
        "/api/v1/inventory/operations/batch",
        json={"operations": [{"item_key": "EGG", "operation": "SUBTRACT", "value": 3, "unit": "piece", "source": "MANUAL"}]},
        headers=make_headers(token=token, idempotent=True),
    )
    resp = client.get(
        f"/api/v1/reports/consumption/monthly?month={_current_month()}",
        headers=make_headers(token=token),
    )
    assert resp.status_code == 200
    report = resp.json()["data"]["report"]
    egg = next(e for e in report["top_consumed"] if e["item_key"] == "EGG")
    assert egg["consumed_qty"] >= 3.0
    assert report["total_consumed_qty"] >= 3.0


def test_report_reflects_waste(alice):
    client, token, user_id, household_id = alice
    store.run_auto_decay_for_all()
    resp = client.get(
        f"/api/v1/reports/consumption/monthly?month={_current_month()}",
        headers=make_headers(token=token),
    )
    assert resp.status_code == 200
    report = resp.json()["data"]["report"]
    assert report["total_wasted_qty"] > 0
    assert any(e["wasted_qty"] > 0 for e in report["wasted"])


def test_report_snapshot_reused(alice):
    client, token, user_id, household_id = alice
    month = _current_month()
    first = client.get(f"/api/v1/reports/consumption/monthly?month={month}", headers=make_headers(token=token))
    second = client.get(f"/api/v1/reports/consumption/monthly?month={month}", headers=make_headers(token=token))
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["data"]["report"]["report_id"] == second.json()["data"]["report"]["report_id"]


def test_invalid_month(alice):
    client, token, user_id, household_id = alice
    resp = client.get("/api/v1/reports/consumption/monthly?month=2026-13", headers=make_headers(token=token))
    assert resp.status_code == 400


def test_admin_report_overview(client):
    alice_resp = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": "+861****0001", "code": "123456", "device_id": "device-alice-reports-admin"},
        headers=make_headers(idempotency_key="alice-login-reports-admin"),
    )
    alice_token = alice_resp.json()["data"]["access_token"]
    month = _current_month()
    client.get(f"/api/v1/reports/consumption/monthly?month={month}", headers=make_headers(token=alice_token))

    admin_login = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": "13900139000", "code": "123456", "device_id": "web-admin-reports"},
        headers=make_headers(idempotency_key="admin-login-reports"),
    )
    admin_token = admin_login.json()["data"]["access_token"]

    resp = client.get("/api/v1/admin/reports/overview", headers=make_headers(token=admin_token))
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 1
    assert any(row["report_count"] >= 1 for row in data["list"])
    for row in data["list"]:
        assert "household_id" in row
        assert "member_count" in row
        assert "total_consumed_qty" in row
        assert "total_wasted_qty" in row


def test_non_admin_cannot_view_report_overview(client):
    alice_resp = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": "+861****0001", "code": "123456", "device_id": "device-alice-reports-nonadmin"},
        headers=make_headers(idempotency_key="alice-login-reports-nonadmin"),
    )
    token = alice_resp.json()["data"]["access_token"]
    resp = client.get("/api/v1/admin/reports/overview", headers=make_headers(token=token))
    assert resp.status_code == 403
    assert resp.json()["code"] == "AUTH_403_FORBIDDEN"
