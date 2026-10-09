from __future__ import annotations

from conftest import make_headers


def _login(client, phone: str) -> str:
    resp = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": phone, "code": "123456", "device_id": "ios-device-fin"},
        headers=make_headers(idempotency_key=f"login-{phone}"),
    )
    assert resp.status_code == 200
    return resp.json()["data"]["access_token"]


def test_asset_crud_and_total(client):
    token = _login(client, "13800138300")
    r = client.post(
        "/api/v1/assets",
        json={"name": "银行存款", "category": "cash", "amount": 100000},
        headers=make_headers(idempotency_key="fin-1", token=token),
    )
    assert r.status_code == 200
    r = client.post(
        "/api/v1/assets",
        json={"name": "股票账户", "category": "stock", "amount": 50000},
        headers=make_headers(idempotency_key="fin-2", token=token),
    )
    aid = r.json()["data"]["asset"]["asset_id"]

    r = client.get("/api/v1/assets", headers=make_headers(token=token))
    assert r.json()["data"]["total"] == 150000
    assert len(r.json()["data"]["assets"]) == 2

    r = client.delete(f"/api/v1/assets/{aid}", headers=make_headers(idempotency_key="fin-3", token=token))
    assert r.status_code == 200


def test_investment_crud(client):
    token = _login(client, "13800138300")
    r = client.post(
        "/api/v1/investments",
        json={"name": "指数基金", "amount": 10000, "return_rate": 8.5},
        headers=make_headers(idempotency_key="fin-4", token=token),
    )
    assert r.status_code == 200
    iid = r.json()["data"]["investment"]["investment_id"]

    r = client.get("/api/v1/investments", headers=make_headers(token=token))
    assert len(r.json()["data"]["investments"]) == 1

    r = client.delete(f"/api/v1/investments/{iid}", headers=make_headers(idempotency_key="fin-5", token=token))
    assert r.status_code == 200
