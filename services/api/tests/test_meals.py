from __future__ import annotations

from conftest import make_headers


def _login(client, phone: str) -> str:
    resp = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": phone, "code": "123456", "device_id": "ios-device-meal"},
        headers=make_headers(idempotency_key=f"login-{phone}"),
    )
    assert resp.status_code == 200
    return resp.json()["data"]["access_token"]


def test_meal_suggest_empty_inventory(client):
    token = _login(client, "13800138300")
    r = client.post("/api/v1/meals/suggest", headers=make_headers(idempotency_key="meal-1", token=token))
    assert r.status_code == 200
    d = r.json()["data"]
    assert "suggestion" in d
    assert "available_items" in d
    assert "今晚推荐" in d["suggestion"]
