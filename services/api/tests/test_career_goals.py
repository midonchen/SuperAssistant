from __future__ import annotations

from conftest import make_headers


def _login(client, phone: str) -> str:
    resp = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": phone, "code": "123456", "device_id": "ios-device-cg"},
        headers=make_headers(idempotency_key=f"login-{phone}"),
    )
    assert resp.status_code == 200
    return resp.json()["data"]["access_token"]


def test_career_goal_crud(client):
    token = _login(client, "13800138300")
    r = client.post(
        "/api/v1/career-goals",
        json={"title": "晋升为高级工程师", "target_year": 2027},
        headers=make_headers(idempotency_key="cg-1", token=token),
    )
    assert r.status_code == 200
    g = r.json()["data"]["goal"]
    assert g["title"] == "晋升为高级工程师"
    assert g["target_year"] == 2027
    assert g["progress"] == 0
    gid = g["goal_id"]

    r = client.get("/api/v1/career-goals", headers=make_headers(token=token))
    assert len(r.json()["data"]["goals"]) == 1

    r = client.patch(
        f"/api/v1/career-goals/{gid}",
        json={"progress": 40},
        headers=make_headers(idempotency_key="cg-2", token=token),
    )
    assert r.status_code == 200
    assert r.json()["data"]["goal"]["progress"] == 40

    r = client.patch(
        f"/api/v1/career-goals/{gid}",
        json={"status": "COMPLETED"},
        headers=make_headers(idempotency_key="cg-3", token=token),
    )
    assert r.json()["data"]["goal"]["status"] == "COMPLETED"

    r = client.delete(f"/api/v1/career-goals/{gid}", headers=make_headers(idempotency_key="cg-4", token=token))
    assert r.status_code == 200
    r = client.get("/api/v1/career-goals", headers=make_headers(token=token))
    assert len(r.json()["data"]["goals"]) == 0


def test_career_goal_gate(client):
    token = _login(client, "13800138301")
    for i in range(5):
        r = client.post(
            "/api/v1/career-goals",
            json={"title": f"目标{i}"},
            headers=make_headers(idempotency_key=f"cg-g{i}", token=token),
        )
        assert r.status_code == 200
    r = client.post(
        "/api/v1/career-goals",
        json={"title": "第6个"},
        headers=make_headers(idempotency_key="cg-g6", token=token),
    )
    assert r.status_code == 402
    assert r.json()["code"] == "BIZ_402_UPGRADE_REQUIRED"
