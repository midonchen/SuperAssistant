from __future__ import annotations

from conftest import make_headers


def _login(client, phone: str, device: str = "ios-device-an") -> str:
    resp = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": phone, "code": "123456", "device_id": device},
        headers=make_headers(idempotency_key=f"login-{phone}-{device}"),
    )
    assert resp.status_code == 200
    return resp.json()["data"]["access_token"]


def test_events_recorded_and_admin_readable(client):
    token = _login(client, "13800138600")

    client.post(
        "/api/v1/categories",
        json={"name": "苹果", "unit_type": "个"},
        headers=make_headers(idempotency_key="an-cat-1", token=token),
    )
    client.get("/api/v1/reports/consumption/monthly", headers=make_headers(token=token))

    admin_token = _login(client, "13900139000", "ios-device-an-admin")
    resp = client.get("/api/v1/admin/analytics", headers=make_headers(token=admin_token))
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["summary"].get("category_created", 0) >= 1
    assert data["summary"].get("report_viewed", 0) >= 1
    assert data["total"] >= 2


def test_non_admin_cannot_read_analytics(client):
    token = _login(client, "13800138601")
    resp = client.get("/api/v1/admin/analytics", headers=make_headers(token=token))
    assert resp.status_code == 403
    assert resp.json()["code"] == "AUTH_403_FORBIDDEN"


def test_subscription_gate_hit_recorded(client):
    token = _login(client, "13800138602")
    names = ["苹果", "香蕉", "橙子", "西瓜"]
    for index, name in enumerate(names):
        resp = client.post(
            "/api/v1/categories",
            json={"name": name, "unit_type": "个"},
            headers=make_headers(idempotency_key=f"an-gate-{index}", token=token),
        )
        if index == 3:
            assert resp.status_code == 402

    admin_token = _login(client, "13900139000", "ios-device-an-gate")
    resp = client.get("/api/v1/admin/analytics", headers=make_headers(token=admin_token))
    assert resp.status_code == 200
    assert resp.json()["data"]["summary"].get("subscription_gate_hit", 0) >= 1
