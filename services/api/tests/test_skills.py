from __future__ import annotations

from conftest import make_headers


def _login(client, phone: str) -> str:
    resp = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": phone, "code": "123456", "device_id": "ios-device-sk"},
        headers=make_headers(idempotency_key=f"login-{phone}"),
    )
    assert resp.status_code == 200
    return resp.json()["data"]["access_token"]


def test_skill_crud(client):
    token = _login(client, "13800138300")
    r = client.post(
        "/api/v1/skills",
        json={"name": "Python", "category": "编程", "level": 2, "target_level": 4},
        headers=make_headers(idempotency_key="sk-1", token=token),
    )
    assert r.status_code == 200
    s = r.json()["data"]["skill"]
    assert s["name"] == "Python"
    assert s["level"] == 2
    assert s["target_level"] == 4
    sid = s["skill_id"]

    r = client.get("/api/v1/skills", headers=make_headers(token=token))
    assert len(r.json()["data"]["skills"]) == 1

    r = client.patch(
        f"/api/v1/skills/{sid}",
        json={"level": 3},
        headers=make_headers(idempotency_key="sk-2", token=token),
    )
    assert r.status_code == 200
    assert r.json()["data"]["skill"]["level"] == 3

    r = client.delete(f"/api/v1/skills/{sid}", headers=make_headers(idempotency_key="sk-3", token=token))
    assert r.status_code == 200
    r = client.get("/api/v1/skills", headers=make_headers(token=token))
    assert len(r.json()["data"]["skills"]) == 0


def test_skill_gate(client):
    token = _login(client, "13800138301")
    for i in range(20):
        r = client.post(
            "/api/v1/skills",
            json={"name": f"技能{i}"},
            headers=make_headers(idempotency_key=f"sk-g{i}", token=token),
        )
        assert r.status_code == 200
    r = client.post(
        "/api/v1/skills",
        json={"name": "第21个"},
        headers=make_headers(idempotency_key="sk-g21", token=token),
    )
    assert r.status_code == 402
    assert r.json()["code"] == "BIZ_402_UPGRADE_REQUIRED"
