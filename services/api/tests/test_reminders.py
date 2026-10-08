from __future__ import annotations

from datetime import datetime, timedelta, timezone

from conftest import make_headers


def _login(client, phone: str) -> str:
    resp = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": phone, "code": "123456", "device_id": "ios-device-rem"},
        headers=make_headers(idempotency_key=f"login-{phone}"),
    )
    assert resp.status_code == 200
    return resp.json()["data"]["access_token"]


def test_health_reminder_crud(client):
    token = _login(client, "13800138300")
    r = client.post(
        "/api/v1/health-reminders",
        json={"member_name": "妈妈", "reminder_type": "medication", "title": "降压药", "period_days": 1},
        headers=make_headers(idempotency_key="hr-1", token=token),
    )
    assert r.status_code == 200
    rem = r.json()["data"]["reminder"]
    assert rem["member_name"] == "妈妈"
    assert rem["reminder_type"] == "medication"
    rid = rem["reminder_id"]

    r = client.get("/api/v1/health-reminders", headers=make_headers(token=token))
    assert len(r.json()["data"]["reminders"]) == 1

    r = client.patch(
        f"/api/v1/health-reminders/{rid}",
        json={"period_days": 7},
        headers=make_headers(idempotency_key="hr-2", token=token),
    )
    assert r.json()["data"]["reminder"]["period_days"] == 7

    r = client.delete(f"/api/v1/health-reminders/{rid}", headers=make_headers(idempotency_key="hr-3", token=token))
    assert r.status_code == 200
    r = client.get("/api/v1/health-reminders", headers=make_headers(token=token))
    assert len(r.json()["data"]["reminders"]) == 0


def test_bill_reminder_crud(client):
    token = _login(client, "13800138300")
    r = client.post(
        "/api/v1/bill-reminders",
        json={"name": "水费", "amount": 80, "period_months": 1},
        headers=make_headers(idempotency_key="br-1", token=token),
    )
    assert r.status_code == 200
    rem = r.json()["data"]["reminder"]
    assert rem["name"] == "水费"
    assert rem["amount"] == 80
    rid = rem["reminder_id"]

    r = client.get("/api/v1/bill-reminders", headers=make_headers(token=token))
    assert len(r.json()["data"]["reminders"]) == 1

    r = client.patch(
        f"/api/v1/bill-reminders/{rid}",
        json={"enabled": False},
        headers=make_headers(idempotency_key="br-2", token=token),
    )
    assert r.json()["data"]["reminder"]["enabled"] is False

    r = client.delete(f"/api/v1/bill-reminders/{rid}", headers=make_headers(idempotency_key="br-3", token=token))
    assert r.status_code == 200


def test_reminder_due_task(client):
    token = _login(client, "13800138300")
    now = datetime.now(timezone.utc)
    client.post(
        "/api/v1/health-reminders",
        json={"member_name": "爸爸", "reminder_type": "checkup", "title": "复诊", "period_days": 30, "next_due_at": (now - timedelta(days=1)).isoformat()},
        headers=make_headers(idempotency_key="hr-due", token=token),
    )
    client.post(
        "/api/v1/bill-reminders",
        json={"name": "电费", "amount": 120, "period_months": 1, "next_due_at": (now - timedelta(days=2)).isoformat()},
        headers=make_headers(idempotency_key="br-due", token=token),
    )
    from core.store import store

    assert store.run_health_reminders_for_all()["sent"] == 1
    assert store.run_bill_reminders_for_all()["sent"] == 1
    # next_due_at advanced to future
    rems = client.get("/api/v1/health-reminders", headers=make_headers(token=token)).json()["data"]["reminders"]
    due = datetime.fromisoformat(rems[0]["next_due_at"].replace("Z", "+00:00"))
    assert due.date() > now.date()
    bills = client.get("/api/v1/bill-reminders", headers=make_headers(token=token)).json()["data"]["reminders"]
    due2 = datetime.fromisoformat(bills[0]["next_due_at"].replace("Z", "+00:00"))
    assert due2.date() > now.date()
