from __future__ import annotations

from datetime import date, timedelta

from conftest import make_headers


def _login(client, phone: str) -> str:
    resp = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": phone, "code": "123456", "device_id": "ios-device-hb"},
        headers=make_headers(idempotency_key=f"login-{phone}"),
    )
    assert resp.status_code == 200
    return resp.json()["data"]["access_token"]


def test_habit_checkin_and_streak(client):
    token = _login(client, "13800138300")
    r = client.post(
        "/api/v1/habits",
        json={"name": "早睡早起", "schedule": "22:30", "period_days": 30},
        headers=make_headers(idempotency_key="hb-1", token=token),
    )
    assert r.status_code == 200
    hid = r.json()["data"]["habit"]["habit_id"]

    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    r = client.post(
        f"/api/v1/habits/{hid}/checkin",
        json={"checkin_date": today},
        headers=make_headers(idempotency_key="hb-2", token=token),
    )
    assert r.status_code == 200
    assert r.json()["data"]["streak"] == 1

    r = client.post(
        f"/api/v1/habits/{hid}/checkin",
        json={"checkin_date": yesterday},
        headers=make_headers(idempotency_key="hb-3", token=token),
    )
    assert r.json()["data"]["streak"] == 2

    r = client.get("/api/v1/habits", headers=make_headers(token=token))
    assert r.json()["data"]["habits"][0]["streak"] == 2

    r = client.delete(f"/api/v1/habits/{hid}", headers=make_headers(idempotency_key="hb-4", token=token))
    assert r.status_code == 200


def test_workout_crud(client):
    token = _login(client, "13800138300")
    r = client.post(
        "/api/v1/workouts",
        json={"workout_type": "run", "duration_minutes": 30, "distance_km": 5, "workout_date": "2026-10-01"},
        headers=make_headers(idempotency_key="hb-5", token=token),
    )
    assert r.status_code == 200
    wid = r.json()["data"]["workout"]["workout_id"]

    r = client.get("/api/v1/workouts", headers=make_headers(token=token))
    assert len(r.json()["data"]["workouts"]) == 1

    r = client.delete(f"/api/v1/workouts/{wid}", headers=make_headers(idempotency_key="hb-6", token=token))
    assert r.status_code == 200
