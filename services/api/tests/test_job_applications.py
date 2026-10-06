from __future__ import annotations

from conftest import make_headers


def _login(client, phone: str) -> str:
    resp = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": phone, "code": "123456", "device_id": "ios-device-ja"},
        headers=make_headers(idempotency_key=f"login-{phone}"),
    )
    assert resp.status_code == 200
    return resp.json()["data"]["access_token"]


def test_job_application_crud(client):
    token = _login(client, "13800138300")
    r = client.post(
        "/api/v1/job-applications",
        json={"company": "字节跳动", "position": "高级后端工程师"},
        headers=make_headers(idempotency_key="ja-1", token=token),
    )
    assert r.status_code == 200
    a = r.json()["data"]["application"]
    assert a["company"] == "字节跳动"
    assert a["position"] == "高级后端工程师"
    assert a["status"] == "APPLIED"
    aid = a["application_id"]

    r = client.get("/api/v1/job-applications", headers=make_headers(token=token))
    assert len(r.json()["data"]["applications"]) == 1

    r = client.patch(
        f"/api/v1/job-applications/{aid}",
        json={"status": "INTERVIEW", "notes": "一面通过，约二面"},
        headers=make_headers(idempotency_key="ja-2", token=token),
    )
    assert r.status_code == 200
    assert r.json()["data"]["application"]["status"] == "INTERVIEW"

    r = client.patch(
        f"/api/v1/job-applications/{aid}",
        json={"status": "OFFER"},
        headers=make_headers(idempotency_key="ja-3", token=token),
    )
    assert r.json()["data"]["application"]["status"] == "OFFER"

    r = client.delete(f"/api/v1/job-applications/{aid}", headers=make_headers(idempotency_key="ja-4", token=token))
    assert r.status_code == 200
    r = client.get("/api/v1/job-applications", headers=make_headers(token=token))
    assert len(r.json()["data"]["applications"]) == 0


def test_job_application_gate(client):
    token = _login(client, "13800138301")
    for i in range(20):
        r = client.post(
            "/api/v1/job-applications",
            json={"company": f"公司{i}", "position": "岗位"},
            headers=make_headers(idempotency_key=f"ja-g{i}", token=token),
        )
        assert r.status_code == 200
    r = client.post(
        "/api/v1/job-applications",
        json={"company": "公司21", "position": "岗位"},
        headers=make_headers(idempotency_key="ja-g21", token=token),
    )
    assert r.status_code == 402
    assert r.json()["code"] == "BIZ_402_UPGRADE_REQUIRED"
