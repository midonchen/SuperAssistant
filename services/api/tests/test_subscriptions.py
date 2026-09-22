from __future__ import annotations

from conftest import make_headers


def _login(client, phone: str) -> str:
    resp = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": phone, "code": "123456", "device_id": "ios-device-sub"},
        headers=make_headers(idempotency_key=f"login-{phone}"),
    )
    assert resp.status_code == 200
    return resp.json()["data"]["access_token"]


def test_profile_reports_free_tier(client):
    resp = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": "13800138520", "code": "123456", "device_id": "ios-device-sub"},
        headers=make_headers(idempotency_key="login-13800138520"),
    )
    assert resp.status_code == 200
    profile = resp.json()["data"]["user_profile"]
    assert profile["subscription_tier"] == "free"


def test_free_tier_custom_category_limit(client):
    token = _login(client, "13800138521")
    names = ["苹果", "香蕉", "橙子", "西瓜"]
    for index, name in enumerate(names):
        resp = client.post(
            "/api/v1/categories",
            json={"name": name, "icon": "🍎", "unit_type": "个"},
            headers=make_headers(idempotency_key=f"cat-{index}", token=token),
        )
        if index < 3:
            assert resp.status_code == 200, resp.json()
        else:
            assert resp.status_code == 402
            assert resp.json()["code"] == "BIZ_402_UPGRADE_REQUIRED"


def test_free_tier_household_member_limit(client):
    alice_token = _login(client, "13800138530")
    bob_token = _login(client, "13800138531")

    invite = client.post(
        "/api/v1/households/invitations",
        json={"role": "MEMBER"},
        headers=make_headers(idempotency_key="invite-bob-sub", token=alice_token),
    )
    assert invite.status_code == 200
    code = invite.json()["data"]["invitation"]["invite_code"]

    join = client.post(
        "/api/v1/households/join",
        json={"invite_code": code},
        headers=make_headers(idempotency_key="bob-join-sub", token=bob_token),
    )
    assert join.status_code == 200

    invite2 = client.post(
        "/api/v1/households/invitations",
        json={"role": "MEMBER"},
        headers=make_headers(idempotency_key="invite-second-sub", token=alice_token),
    )
    assert invite2.status_code == 402
    assert invite2.json()["code"] == "BIZ_402_UPGRADE_REQUIRED"


def _free_limits(**overrides) -> dict:
    base = {"custom_categories": 3, "household_members": 2, "tasks": 20, "meetings": 10, "weekly_reports": 5}
    base.update(overrides)
    return base


def test_free_tier_task_limit(client, monkeypatch):
    from core.store import subscriptions as sub_mod

    monkeypatch.setattr(sub_mod, "DEFAULT_FREE_LIMITS", _free_limits(tasks=3))
    token = _login(client, "13800138540")
    for i in range(3):
        r = client.post("/api/v1/tasks", json={"title": f"任务{i}"}, headers=make_headers(idempotency_key=f"gt-{i}", token=token))
        assert r.status_code == 200, r.json()
    r = client.post("/api/v1/tasks", json={"title": "超限"}, headers=make_headers(idempotency_key="gt-3", token=token))
    assert r.status_code == 402
    assert r.json()["code"] == "BIZ_402_UPGRADE_REQUIRED"


def test_free_tier_meeting_limit(client, monkeypatch):
    from core.store import subscriptions as sub_mod

    monkeypatch.setattr(sub_mod, "DEFAULT_FREE_LIMITS", _free_limits(meetings=1))
    token = _login(client, "13800138541")
    r = client.post("/api/v1/meetings", json={"title": "会议1", "transcript": "内容"}, headers=make_headers(idempotency_key="gm-1", token=token))
    assert r.status_code == 200, r.json()
    r = client.post("/api/v1/meetings", json={"title": "会议2", "transcript": "内容"}, headers=make_headers(idempotency_key="gm-2", token=token))
    assert r.status_code == 402
    assert r.json()["code"] == "BIZ_402_UPGRADE_REQUIRED"


def test_free_tier_weekly_report_limit(client, monkeypatch):
    from core.store import subscriptions as sub_mod

    monkeypatch.setattr(sub_mod, "DEFAULT_FREE_LIMITS", _free_limits(weekly_reports=1))
    token = _login(client, "13800138542")
    r = client.post("/api/v1/weekly-reports/generate", headers=make_headers(idempotency_key="wr-1", token=token))
    assert r.status_code == 200
    week = r.json()["data"]["report"]["week_start"]
    r = client.post(f"/api/v1/weekly-reports/generate?week_start={week}", headers=make_headers(idempotency_key="wr-2", token=token))
    assert r.status_code == 200  # upsert same week allowed
    r = client.post("/api/v1/weekly-reports/generate?week_start=2020-01-06", headers=make_headers(idempotency_key="wr-3", token=token))
    assert r.status_code == 402
    assert r.json()["code"] == "BIZ_402_UPGRADE_REQUIRED"
