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
