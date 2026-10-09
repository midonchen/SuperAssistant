from __future__ import annotations

from conftest import make_headers


def test_wechat_login_creates_and_reuses_user(client):
    r = client.post(
        "/api/v1/auth/wechat/login",
        json={"code": "test-code-1", "device_id": "wx-dev-1"},
        headers=make_headers(idempotency_key="wx-1"),
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["is_new_user"] is True
    assert data["user_profile"]["phone_masked"] == "微信用户"
    assert data["access_token"].startswith("access-")
    first_user_id = data["user_profile"]["user_id"]

    # same code → same openid → existing user, is_new_user False
    r2 = client.post(
        "/api/v1/auth/wechat/login",
        json={"code": "test-code-1", "device_id": "wx-dev-1"},
        headers=make_headers(idempotency_key="wx-2"),
    )
    assert r2.status_code == 200
    assert r2.json()["data"]["is_new_user"] is False
    assert r2.json()["data"]["user_profile"]["user_id"] == first_user_id

    # different code → different openid → new user
    r3 = client.post(
        "/api/v1/auth/wechat/login",
        json={"code": "test-code-2", "device_id": "wx-dev-1"},
        headers=make_headers(idempotency_key="wx-3"),
    )
    assert r3.json()["data"]["is_new_user"] is True
    assert r3.json()["data"]["user_profile"]["user_id"] != first_user_id
