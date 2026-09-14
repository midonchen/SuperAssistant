from __future__ import annotations


def test_healthz_probe_without_custom_headers(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
