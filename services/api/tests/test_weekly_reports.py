from __future__ import annotations

from datetime import datetime, timedelta, timezone

from conftest import make_headers


def _login(client, phone: str) -> str:
    resp = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": phone, "code": "123456", "device_id": "ios-device-wr"},
        headers=make_headers(idempotency_key=f"login-{phone}"),
    )
    assert resp.status_code == 200
    return resp.json()["data"]["access_token"]


def test_weekly_report_generate_and_get(client, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)  # heuristic fallback
    token = _login(client, "13800138400")
    now = datetime.now(timezone.utc)
    r = client.post("/api/v1/tasks", json={"title": "完成的任务", "priority": 2}, headers=make_headers(idempotency_key="w-1", token=token))
    task_id = r.json()["data"]["task"]["task_id"]
    client.patch(f"/api/v1/tasks/{task_id}", json={"status": "DONE"}, headers=make_headers(idempotency_key="w-2", token=token))
    client.post("/api/v1/tasks", json={"title": "逾期任务", "due_at": (now - timedelta(days=1)).isoformat()}, headers=make_headers(idempotency_key="w-3", token=token))
    client.post("/api/v1/tasks", json={"title": "进行中任务", "due_at": (now + timedelta(days=2)).isoformat()}, headers=make_headers(idempotency_key="w-4", token=token))

    r = client.post("/api/v1/weekly-reports/generate", headers=make_headers(idempotency_key="w-5", token=token))
    assert r.status_code == 200
    report = r.json()["data"]["report"]
    assert report["week_start"]
    content = report["content"]
    assert "完成的任务" in content
    assert "逾期任务" in content
    assert "进行中任务" in content

    r = client.get(f"/api/v1/weekly-reports/{report['week_start']}", headers=make_headers(token=token))
    assert r.status_code == 200
    assert r.json()["data"]["report"]["report_id"] == report["report_id"]

    r = client.get("/api/v1/weekly-reports", headers=make_headers(token=token))
    assert len(r.json()["data"]["reports"]) == 1


def test_weekly_report_regenerate_is_idempotent(client, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    token = _login(client, "13800138401")
    client.post("/api/v1/tasks", json={"title": "任务A"}, headers=make_headers(idempotency_key="w-6", token=token))
    r1 = client.post("/api/v1/weekly-reports/generate", headers=make_headers(idempotency_key="w-7", token=token))
    id1 = r1.json()["data"]["report"]["report_id"]
    r2 = client.post("/api/v1/weekly-reports/generate", headers=make_headers(idempotency_key="w-8", token=token))
    id2 = r2.json()["data"]["report"]["report_id"]
    assert id1 == id2
    r = client.get("/api/v1/weekly-reports", headers=make_headers(token=token))
    assert len(r.json()["data"]["reports"]) == 1
