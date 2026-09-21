from __future__ import annotations

from datetime import datetime, timedelta, timezone

from conftest import make_headers


def _login(client, phone: str) -> str:
    resp = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": phone, "code": "123456", "device_id": "ios-device-meet"},
        headers=make_headers(idempotency_key=f"login-{phone}"),
    )
    assert resp.status_code == 200
    return resp.json()["data"]["access_token"]


def test_meeting_create_with_summary_and_action_items(client, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)  # force heuristic fallback
    token = _login(client, "13800138500")
    transcript = "讨论了下季度计划。\n待办：张三负责采购\n行动项：李四写报告\n"
    r = client.post(
        "/api/v1/meetings",
        json={"title": "季度规划会", "transcript": transcript},
        headers=make_headers(idempotency_key="m-1", token=token),
    )
    assert r.status_code == 200
    meeting = r.json()["data"]["meeting"]
    assert meeting["title"] == "季度规划会"
    assert meeting["summary"]
    assert len(meeting["action_items"]) == 2
    texts = [i["text"] for i in meeting["action_items"]]
    assert "张三负责采购" in texts
    assert "李四写报告" in texts


def test_meeting_crud_and_action_item_404(client):
    token = _login(client, "13800138501")
    r = client.post(
        "/api/v1/meetings",
        json={"title": "例会", "transcript": "讨论产品进展。"},
        headers=make_headers(idempotency_key="m-2", token=token),
    )
    meeting_id = r.json()["data"]["meeting"]["meeting_id"]

    r = client.get("/api/v1/meetings", headers=make_headers(token=token))
    assert len(r.json()["data"]["meetings"]) == 1

    r = client.get(f"/api/v1/meetings/{meeting_id}", headers=make_headers(token=token))
    assert r.status_code == 200
    assert r.json()["data"]["meeting"]["meeting_id"] == meeting_id

    r = client.patch(
        "/api/v1/meetings/action-items/nonexistent",
        json={"done": True},
        headers=make_headers(idempotency_key="m-3", token=token),
    )
    assert r.status_code == 404


def test_meeting_in_calendar(client):
    token = _login(client, "13800138502")
    now = datetime.now(timezone.utc)
    r = client.post(
        "/api/v1/meetings",
        json={"title": "周会", "transcript": "复盘", "started_at": (now + timedelta(days=1)).isoformat()},
        headers=make_headers(idempotency_key="m-4", token=token),
    )
    assert r.status_code == 200
    start = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    end = (now + timedelta(days=7)).strftime("%Y-%m-%d")
    r = client.get(f"/api/v1/calendar/events?start_date={start}&end_date={end}", headers=make_headers(token=token))
    events = r.json()["data"]["events"]
    meeting_events = [e for e in events if e["source"] == "meeting"]
    assert len(meeting_events) == 1
    assert meeting_events[0]["title"] == "周会"
    assert meeting_events[0]["meeting_id"]
