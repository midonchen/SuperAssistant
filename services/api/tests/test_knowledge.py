from __future__ import annotations

from conftest import make_headers


def _login(client, phone: str) -> str:
    resp = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": phone, "code": "123456", "device_id": "ios-device-kb"},
        headers=make_headers(idempotency_key=f"login-{phone}"),
    )
    assert resp.status_code == 200
    return resp.json()["data"]["access_token"]


def test_thinking_model_presets_and_crud(client):
    token = _login(client, "13800138300")
    r = client.get("/api/v1/thinking-models", headers=make_headers(token=token))
    assert r.status_code == 200
    entries = r.json()["data"]["entries"]
    assert len(entries) == 8
    names = [e["name"] for e in entries]
    assert "多元思维模型" in names
    assert "长线思维" in names

    r = client.post(
        "/api/v1/thinking-models",
        json={"name": "复利思维", "description": "时间>金额，复利积累"},
        headers=make_headers(idempotency_key="kb-1", token=token),
    )
    assert r.status_code == 200
    eid = r.json()["data"]["entry"]["entry_id"]

    r = client.patch(
        f"/api/v1/thinking-models/{eid}",
        json={"description": "更新后的描述"},
        headers=make_headers(idempotency_key="kb-2", token=token),
    )
    assert r.json()["data"]["entry"]["description"] == "更新后的描述"

    r = client.delete(f"/api/v1/thinking-models/{eid}", headers=make_headers(idempotency_key="kb-3", token=token))
    assert r.status_code == 200


def test_value_principle_presets(client):
    token = _login(client, "13800138300")
    r = client.get("/api/v1/value-principles", headers=make_headers(token=token))
    assert r.status_code == 200
    entries = r.json()["data"]["entries"]
    assert len(entries) == 8
    names = [e["name"] for e in entries]
    assert "理性" in names
    assert "工匠精神" in names
    assert "严于律己宽以待人" in names
