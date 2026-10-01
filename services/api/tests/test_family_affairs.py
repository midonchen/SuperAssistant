from __future__ import annotations

from datetime import datetime, timedelta, timezone

from conftest import make_headers


def _login(client, phone: str) -> str:
    resp = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": phone, "code": "123456", "device_id": "ios-device-fa"},
        headers=make_headers(idempotency_key=f"login-{phone}"),
    )
    assert resp.status_code == 200
    return resp.json()["data"]["access_token"]


def test_family_affairs_crud_and_calendar(client):
    token = _login(client, "13800138200")
    now = datetime.now(timezone.utc)
    r = client.post(
        "/api/v1/family-affairs",
        json={"title": "交物业费", "assignee": "我", "due_at": (now + timedelta(days=2)).isoformat()},
        headers=make_headers(idempotency_key="fa-1", token=token),
    )
    assert r.status_code == 200
    aid = r.json()["data"]["affair"]["affair_id"]

    r = client.get("/api/v1/family-affairs", headers=make_headers(token=token))
    assert len(r.json()["data"]["affairs"]) == 1

    r = client.patch(f"/api/v1/family-affairs/{aid}", json={"status": "DONE"}, headers=make_headers(idempotency_key="fa-2", token=token))
    assert r.status_code == 200
    assert r.json()["data"]["affair"]["status"] == "DONE"

    start = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    end = (now + timedelta(days=7)).strftime("%Y-%m-%d")
    r = client.get(f"/api/v1/calendar/events?start_date={start}&end_date={end}", headers=make_headers(token=token))
    family_events = [e for e in r.json()["data"]["events"] if e["source"] == "family"]
    assert len(family_events) == 0  # DONE filtered out

    client.post("/api/v1/family-affairs", json={"title": "换水", "due_at": (now + timedelta(days=3)).isoformat()}, headers=make_headers(idempotency_key="fa-3", token=token))
    r = client.get(f"/api/v1/calendar/events?start_date={start}&end_date={end}", headers=make_headers(token=token))
    family_events = [e for e in r.json()["data"]["events"] if e["source"] == "family"]
    assert len(family_events) == 1
    assert family_events[0]["title"] == "换水"
