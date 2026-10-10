from __future__ import annotations

from conftest import make_headers


def _login(client, phone: str) -> str:
    resp = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": phone, "code": "123456", "device_id": "ios-device-ia"},
        headers=make_headers(idempotency_key=f"login-{phone}"),
    )
    assert resp.status_code == 200
    return resp.json()["data"]["access_token"]


def test_work_reflection_crud(client):
    token = _login(client, "13800138300")
    r = client.post(
        "/api/v1/work-reflections",
        json={"title": "复盘：周会", "content": "本周学到的点"},
        headers=make_headers(idempotency_key="ia-1", token=token),
    )
    assert r.status_code == 200
    rid = r.json()["data"]["reflection"]["reflection_id"]
    r = client.get("/api/v1/work-reflections", headers=make_headers(token=token))
    assert len(r.json()["data"]["reflections"]) == 1
    r = client.delete(f"/api/v1/work-reflections/{rid}", headers=make_headers(idempotency_key="ia-2", token=token))
    assert r.status_code == 200


def test_startup_idea_and_notes(client):
    token = _login(client, "13800138300")
    r = client.post(
        "/api/v1/startup-ideas",
        json={"title": "做一个记账小程序", "description": "给年轻人的极简记账"},
        headers=make_headers(idempotency_key="ia-3", token=token),
    )
    assert r.status_code == 200
    iid = r.json()["data"]["idea"]["idea_id"]

    r = client.patch(f"/api/v1/startup-ideas/{iid}", json={"status": "research"}, headers=make_headers(idempotency_key="ia-4", token=token))
    assert r.json()["data"]["idea"]["status"] == "research"

    r = client.post(
        f"/api/v1/startup-ideas/{iid}/notes",
        json={"content": "调研了竞品", "note_type": "summary"},
        headers=make_headers(idempotency_key="ia-5", token=token),
    )
    assert r.status_code == 200
    r = client.get(f"/api/v1/startup-ideas/{iid}/notes", headers=make_headers(token=token))
    assert len(r.json()["data"]["notes"]) == 1

    r = client.delete(f"/api/v1/startup-ideas/{iid}", headers=make_headers(idempotency_key="ia-6", token=token))
    assert r.status_code == 200
    r = client.get("/api/v1/startup-ideas", headers=make_headers(token=token))
    assert len(r.json()["data"]["ideas"]) == 0


def test_interest_and_life_skill_crud(client):
    token = _login(client, "13800138300")
    r = client.post("/api/v1/interests", json={"name": "摄影"}, headers=make_headers(idempotency_key="ia-7", token=token))
    assert r.status_code == 200
    int_id = r.json()["data"]["interest"]["interest_id"]
    r = client.get("/api/v1/interests", headers=make_headers(token=token))
    assert len(r.json()["data"]["interests"]) == 1
    r = client.delete(f"/api/v1/interests/{int_id}", headers=make_headers(idempotency_key="ia-8", token=token))
    assert r.status_code == 200

    r = client.post("/api/v1/life-skills", json={"name": "烹饪", "level": 3}, headers=make_headers(idempotency_key="ia-9", token=token))
    assert r.status_code == 200
    sid = r.json()["data"]["life_skill"]["life_skill_id"]
    r = client.get("/api/v1/life-skills", headers=make_headers(token=token))
    assert len(r.json()["data"]["life_skills"]) == 1
    r = client.delete(f"/api/v1/life-skills/{sid}", headers=make_headers(idempotency_key="ia-10", token=token))
    assert r.status_code == 200
