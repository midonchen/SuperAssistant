from __future__ import annotations

from datetime import datetime, timedelta, timezone

from conftest import make_headers


def _login(client, phone: str) -> str:
    resp = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": phone, "code": "123456", "device_id": "ios-device-ct"},
        headers=make_headers(idempotency_key=f"login-{phone}"),
    )
    assert resp.status_code == 200
    return resp.json()["data"]["access_token"]


def test_contact_crud_and_birthday_occasion(client):
    token = _login(client, "13800138300")
    r = client.post(
        "/api/v1/contacts",
        json={"name": "妈妈", "relationship": "母亲", "birthday": "05-20"},
        headers=make_headers(idempotency_key="ct-1", token=token),
    )
    assert r.status_code == 200
    c = r.json()["data"]["contact"]
    assert c["name"] == "妈妈"
    assert c["birthday"] == "05-20"
    cid = c["contact_id"]

    r = client.get(f"/api/v1/contacts/{cid}/occasions", headers=make_headers(token=token))
    occs = r.json()["data"]["occasions"]
    assert len(occs) == 1
    assert occs[0]["name"] == "生日"
    assert occs[0]["month"] == 5
    assert occs[0]["day"] == 20

    r = client.patch(f"/api/v1/contacts/{cid}", json={"relationship": "妈妈"}, headers=make_headers(idempotency_key="ct-2", token=token))
    assert r.status_code == 200

    r = client.delete(f"/api/v1/contacts/{cid}", headers=make_headers(idempotency_key="ct-3", token=token))
    assert r.status_code == 200
    r = client.get("/api/v1/contacts", headers=make_headers(token=token))
    assert r.json()["data"]["contacts"] == []


def test_occasion_in_calendar(client):
    token = _login(client, "13800138301")
    now = datetime.now(timezone.utc)
    target = (now + timedelta(days=2)).strftime("%m-%d")
    client.post(
        "/api/v1/contacts",
        json={"name": "朋友", "birthday": target},
        headers=make_headers(idempotency_key="ct-4", token=token),
    )
    start = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    end = (now + timedelta(days=7)).strftime("%Y-%m-%d")
    r = client.get(f"/api/v1/calendar/events?start_date={start}&end_date={end}", headers=make_headers(token=token))
    events = r.json()["data"]["events"]
    occasion_events = [e for e in events if e["source"] == "occasion"]
    assert len(occasion_events) == 1
    assert "朋友" in occasion_events[0]["title"]


def test_contact_subscription_gate(client, monkeypatch):
    from core.store import subscriptions as sub_mod

    monkeypatch.setattr(
        sub_mod,
        "DEFAULT_FREE_LIMITS",
        {"custom_categories": 3, "household_members": 2, "tasks": 20, "meetings": 10, "weekly_reports": 5, "contacts": 2, "occasions": 10},
    )
    token = _login(client, "13800138302")
    for i in range(2):
        r = client.post("/api/v1/contacts", json={"name": f"人{i}"}, headers=make_headers(idempotency_key=f"ct-{i+10}", token=token))
        assert r.status_code == 200, r.json()
    r = client.post("/api/v1/contacts", json={"name": "超限"}, headers=make_headers(idempotency_key="ct-99", token=token))
    assert r.status_code == 402
    assert r.json()["code"] == "BIZ_402_UPGRADE_REQUIRED"
