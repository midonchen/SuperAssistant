from __future__ import annotations

from conftest import make_headers


def _login(client, phone: str) -> str:
    resp = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": phone, "code": "123456", "device_id": "ios-device-li"},
        headers=make_headers(idempotency_key=f"login-{phone}"),
    )
    assert resp.status_code == 200
    return resp.json()["data"]["access_token"]


def test_learning_item_crud(client):
    token = _login(client, "13800138300")
    r = client.post(
        "/api/v1/learning-items",
        json={"title": "系统设计面试", "item_type": "course"},
        headers=make_headers(idempotency_key="li-1", token=token),
    )
    assert r.status_code == 200
    it = r.json()["data"]["item"]
    assert it["title"] == "系统设计面试"
    assert it["item_type"] == "course"
    assert it["status"] == "TODO"
    iid = it["item_id"]

    r = client.get("/api/v1/learning-items", headers=make_headers(token=token))
    assert len(r.json()["data"]["items"]) == 1

    r = client.patch(
        f"/api/v1/learning-items/{iid}",
        json={"status": "IN_PROGRESS"},
        headers=make_headers(idempotency_key="li-2", token=token),
    )
    assert r.json()["data"]["item"]["status"] == "IN_PROGRESS"

    r = client.patch(
        f"/api/v1/learning-items/{iid}",
        json={"status": "DONE"},
        headers=make_headers(idempotency_key="li-3", token=token),
    )
    assert r.json()["data"]["item"]["status"] == "DONE"

    r = client.delete(f"/api/v1/learning-items/{iid}", headers=make_headers(idempotency_key="li-4", token=token))
    assert r.status_code == 200
    r = client.get("/api/v1/learning-items", headers=make_headers(token=token))
    assert len(r.json()["data"]["items"]) == 0


def test_learning_item_gate(client):
    token = _login(client, "13800138301")
    for i in range(20):
        r = client.post(
            "/api/v1/learning-items",
            json={"title": f"学习{i}"},
            headers=make_headers(idempotency_key=f"li-g{i}", token=token),
        )
        assert r.status_code == 200
    r = client.post(
        "/api/v1/learning-items",
        json={"title": "第21个"},
        headers=make_headers(idempotency_key="li-g21", token=token),
    )
    assert r.status_code == 402
    assert r.json()["code"] == "BIZ_402_UPGRADE_REQUIRED"
