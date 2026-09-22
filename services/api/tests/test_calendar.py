from __future__ import annotations

from datetime import datetime, timedelta, timezone

from conftest import make_headers


def _login(client, phone: str) -> str:
    resp = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": phone, "code": "123456", "device_id": "ios-device-cal"},
        headers=make_headers(idempotency_key=f"login-{phone}"),
    )
    assert resp.status_code == 200
    return resp.json()["data"]["access_token"]


def test_calendar_aggregates_task_deadlines(client):
    token = _login(client, "13800138600")
    now = datetime.now(timezone.utc)
    client.post(
        "/api/v1/tasks",
        json={"title": "明天交报告", "due_at": (now + timedelta(days=1)).isoformat(), "priority": 2},
        headers=make_headers(idempotency_key="c-1", token=token),
    )
    client.post("/api/v1/tasks", json={"title": "无截止", "priority": 3}, headers=make_headers(idempotency_key="c-2", token=token))
    client.post(
        "/api/v1/tasks",
        json={"title": "下月任务", "due_at": (now + timedelta(days=60)).isoformat(), "priority": 3},
        headers=make_headers(idempotency_key="c-3", token=token),
    )

    start = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    end = (now + timedelta(days=7)).strftime("%Y-%m-%d")
    r = client.get(f"/api/v1/calendar/events?start_date={start}&end_date={end}", headers=make_headers(token=token))
    assert r.status_code == 200
    events = r.json()["data"]["events"]
    assert len(events) == 1
    assert events[0]["title"] == "明天交报告"
    assert events[0]["source"] == "task"
    assert events[0]["task_id"]
    assert events[0]["start_at"]


def test_calendar_excludes_done_tasks(client):
    token = _login(client, "13800138601")
    now = datetime.now(timezone.utc)
    r = client.post(
        "/api/v1/tasks",
        json={"title": "已完成", "due_at": (now + timedelta(days=1)).isoformat()},
        headers=make_headers(idempotency_key="c-4", token=token),
    )
    task_id = r.json()["data"]["task"]["task_id"]
    client.patch(f"/api/v1/tasks/{task_id}", json={"status": "DONE"}, headers=make_headers(idempotency_key="c-5", token=token))

    start = now.strftime("%Y-%m-%d")
    end = (now + timedelta(days=7)).strftime("%Y-%m-%d")
    r = client.get(f"/api/v1/calendar/events?start_date={start}&end_date={end}", headers=make_headers(token=token))
    assert r.status_code == 200
    assert r.json()["data"]["events"] == []


def test_calendar_ical_export(client):
    token = _login(client, "13800138602")
    now = datetime.now(timezone.utc)
    client.post(
        "/api/v1/tasks",
        json={"title": "交报告", "due_at": (now + timedelta(days=1)).isoformat()},
        headers=make_headers(idempotency_key="i-1", token=token),
    )
    r = client.get("/api/v1/calendar/ical", headers=make_headers(token=token))
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/calendar")
    assert "BEGIN:VCALENDAR" in r.text
    assert "SUMMARY:交报告" in r.text
