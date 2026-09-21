from __future__ import annotations

from datetime import datetime, timedelta, timezone

from conftest import make_headers


def _login(client, phone: str) -> str:
    resp = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": phone, "code": "123456", "device_id": "ios-device-task"},
        headers=make_headers(idempotency_key=f"login-{phone}"),
    )
    assert resp.status_code == 200
    return resp.json()["data"]["access_token"]


def test_task_crud(client):
    token = _login(client, "13800138700")
    r = client.post("/api/v1/tasks", json={"title": "写周报", "priority": 2}, headers=make_headers(idempotency_key="task-1", token=token))
    assert r.status_code == 200
    task_id = r.json()["data"]["task"]["task_id"]
    assert r.json()["data"]["task"]["status"] == "TODO"

    r = client.get("/api/v1/tasks", headers=make_headers(token=token))
    assert r.status_code == 200
    assert len(r.json()["data"]["tasks"]) == 1

    r = client.patch(f"/api/v1/tasks/{task_id}", json={"status": "DONE"}, headers=make_headers(idempotency_key="task-2", token=token))
    assert r.status_code == 200
    assert r.json()["data"]["task"]["status"] == "DONE"

    r = client.delete(f"/api/v1/tasks/{task_id}", headers=make_headers(idempotency_key="task-3", token=token))
    assert r.status_code == 200
    r = client.get("/api/v1/tasks", headers=make_headers(token=token))
    assert len(r.json()["data"]["tasks"]) == 0


def test_task_isolation_between_users(client):
    token_a = _login(client, "13800138701")
    token_b = _login(client, "13800138702")
    r = client.post("/api/v1/tasks", json={"title": "A 的任务"}, headers=make_headers(idempotency_key="task-a", token=token_a))
    task_id = r.json()["data"]["task"]["task_id"]

    r = client.get("/api/v1/tasks", headers=make_headers(token=token_b))
    assert len(r.json()["data"]["tasks"]) == 0

    r = client.patch(f"/api/v1/tasks/{task_id}", json={"status": "DONE"}, headers=make_headers(idempotency_key="task-b", token=token_b))
    assert r.status_code == 404


def test_task_prioritization(client):
    token = _login(client, "13800138703")
    now = datetime.now(timezone.utc)
    client.post("/api/v1/tasks", json={"title": "逾期任务", "due_at": (now - timedelta(days=1)).isoformat(), "priority": 3}, headers=make_headers(idempotency_key="p-1", token=token))
    client.post("/api/v1/tasks", json={"title": "今天到期", "due_at": (now + timedelta(hours=2)).isoformat(), "priority": 3}, headers=make_headers(idempotency_key="p-2", token=token))
    client.post("/api/v1/tasks", json={"title": "高优先级", "priority": 1}, headers=make_headers(idempotency_key="p-3", token=token))

    r = client.post("/api/v1/tasks/prioritize", headers=make_headers(idempotency_key="p-4", token=token))
    assert r.status_code == 200
    assert r.json()["data"]["method"] == "heuristic"
    ranked = r.json()["data"]["tasks"]
    assert len(ranked) == 3
    assert ranked[0]["title"] == "逾期任务"
    assert ranked[0]["reason"] == "已逾期"
    assert ranked[0]["score"] > ranked[1]["score"] > ranked[2]["score"]


def test_ai_task_rank_fallback_and_success(monkeypatch):
    from core.ai_pipeline import ai_pipeline

    tasks = [
        {"task_id": "a", "title": "A", "due_at": None, "priority": 3, "status": "TODO", "score": 20.0, "reason": "x"},
        {"task_id": "b", "title": "B", "due_at": None, "priority": 1, "status": "TODO", "score": 40.0, "reason": "y"},
    ]
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    method, ranked = ai_pipeline.rank_tasks(tasks)
    assert method == "heuristic"
    assert [t["task_id"] for t in ranked] == ["a", "b"]

    monkeypatch.setattr(ai_pipeline, "_ai_rank", lambda ts: [("b", "B 更重要"), ("a", "A 次之")])
    method, ranked = ai_pipeline.rank_tasks(tasks)
    assert method == "ai"
    assert [t["task_id"] for t in ranked] == ["b", "a"]
    assert ranked[0]["reason"] == "B 更重要"


def test_invalid_task_status(client):
    token = _login(client, "13800138704")
    r = client.post("/api/v1/tasks", json={"title": "t"}, headers=make_headers(idempotency_key="s-1", token=token))
    task_id = r.json()["data"]["task"]["task_id"]
    r = client.patch(f"/api/v1/tasks/{task_id}", json={"status": "INVALID"}, headers=make_headers(idempotency_key="s-2", token=token))
    assert r.status_code == 400
    assert r.json()["code"] == "VAL_400_INVALID_PARAM"
