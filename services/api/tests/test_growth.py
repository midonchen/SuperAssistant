from __future__ import annotations

from conftest import make_headers


def _login(client, phone: str) -> str:
    resp = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": phone, "code": "123456", "device_id": "ios-device-gr"},
        headers=make_headers(idempotency_key=f"login-{phone}"),
    )
    assert resp.status_code == 200
    return resp.json()["data"]["access_token"]


def test_journal_crud(client):
    token = _login(client, "13800138300")
    r = client.post(
        "/api/v1/journal",
        json={"content": "今天读完了穷查理宝典第一章，收获很大", "mood": "平静"},
        headers=make_headers(idempotency_key="gr-1", token=token),
    )
    assert r.status_code == 200
    eid = r.json()["data"]["entry"]["entry_id"]

    r = client.get("/api/v1/journal", headers=make_headers(token=token))
    assert len(r.json()["data"]["entries"]) == 1

    r = client.delete(f"/api/v1/journal/{eid}", headers=make_headers(idempotency_key="gr-2", token=token))
    assert r.status_code == 200


def test_life_goal_crud(client):
    token = _login(client, "13800138300")
    r = client.post(
        "/api/v1/life-goals",
        json={"dimension": "career", "title": "做自己喜欢的事", "description": "找到想做的事"},
        headers=make_headers(idempotency_key="gr-3", token=token),
    )
    assert r.status_code == 200
    g = r.json()["data"]["goal"]
    assert g["dimension"] == "career"
    gid = g["goal_id"]

    r = client.get("/api/v1/life-goals", headers=make_headers(token=token))
    assert len(r.json()["data"]["goals"]) == 1

    r = client.patch(
        f"/api/v1/life-goals/{gid}",
        json={"title": "做自己喜欢的事（更新）"},
        headers=make_headers(idempotency_key="gr-4", token=token),
    )
    assert r.json()["data"]["goal"]["title"] == "做自己喜欢的事（更新）"

    r = client.delete(f"/api/v1/life-goals/{gid}", headers=make_headers(idempotency_key="gr-5", token=token))
    assert r.status_code == 200
