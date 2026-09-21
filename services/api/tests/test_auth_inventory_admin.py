from __future__ import annotations

from conftest import make_headers
from core.store import store
from modules.inventory.domain.tasks import run_offline_replay_queue_task


def test_write_requires_idempotency_key(client):
    resp = client.post(
        "/api/v1/auth/sms/send",
        json={"phone": "13800138000", "purpose": "LOGIN"},
        headers=make_headers(idempotent=False),
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "VAL_400_INVALID_PARAM"


def test_login_and_inventory_flow(client):
    send_resp = client.post(
        "/api/v1/auth/sms/send",
        json={"phone": "13800138000", "purpose": "LOGIN"},
        headers=make_headers(idempotent=True),
    )
    assert send_resp.status_code == 200

    login_resp = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": "13800138000", "code": "123456", "device_id": "ios-device-001"},
        headers=make_headers(idempotent=True),
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["data"]["access_token"]

    list_resp = client.get("/api/v1/inventory/items", headers=make_headers(token=token))
    assert list_resp.status_code == 200
    assert len(list_resp.json()["data"]["items"]) == 6

    batch_resp = client.post(
        "/api/v1/inventory/operations/batch",
        json={
            "operations": [
                {
                    "item_key": "EGG",
                    "operation": "ADD",
                    "value": 3,
                    "unit": "个",
                    "source": "VOICE",
                }
            ]
        },
        headers=make_headers(idempotent=True, token=token),
    )
    assert batch_resp.status_code == 200
    assert batch_resp.json()["data"]["updated_items"][0]["server_version"] >= 2


def test_token_refresh_rotation_and_logout_flow(client):
    login_resp = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": "13800138011", "code": "123456", "device_id": "ios-device-011"},
        headers=make_headers(idempotent=True),
    )
    assert login_resp.status_code == 200
    login_data = login_resp.json()["data"]
    old_access = login_data["access_token"]
    old_refresh = login_data["refresh_token"]
    session_id = login_data["session_id"]

    refresh_resp = client.post(
        "/api/v1/auth/token/refresh",
        json={"refresh_token": old_refresh, "device_id": "ios-device-011"},
        headers=make_headers(idempotent=True),
    )
    assert refresh_resp.status_code == 200
    refresh_data = refresh_resp.json()["data"]
    new_access = refresh_data["access_token"]
    new_refresh = refresh_data["refresh_token"]
    new_session_id = refresh_data["session_id"]
    assert new_access != old_access
    assert new_refresh != old_refresh
    assert new_session_id == session_id

    old_access_resp = client.get("/api/v1/inventory/items", headers=make_headers(token=old_access))
    assert old_access_resp.status_code == 401
    assert old_access_resp.json()["code"] == "AUTH_401_TOKEN_EXPIRED"

    old_refresh_resp = client.post(
        "/api/v1/auth/token/refresh",
        json={"refresh_token": old_refresh, "device_id": "ios-device-011"},
        headers=make_headers(idempotent=True),
    )
    assert old_refresh_resp.status_code == 401
    assert old_refresh_resp.json()["code"] == "AUTH_401_TOKEN_EXPIRED"

    new_access_resp = client.get("/api/v1/inventory/items", headers=make_headers(token=new_access))
    assert new_access_resp.status_code == 200

    logout_resp = client.post(
        "/api/v1/auth/logout",
        json={"session_id": new_session_id},
        headers=make_headers(idempotent=True, token=new_access),
    )
    assert logout_resp.status_code == 200

    revoked_access_resp = client.get("/api/v1/inventory/items", headers=make_headers(token=new_access))
    assert revoked_access_resp.status_code == 401
    assert revoked_access_resp.json()["code"] == "AUTH_401_TOKEN_EXPIRED"


def test_logout_cannot_revoke_other_users_session(client):
    login_a = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": "13800138021", "code": "123456", "device_id": "ios-device-021"},
        headers=make_headers(idempotent=True),
    )
    assert login_a.status_code == 200
    data_a = login_a.json()["data"]
    token_a = data_a["access_token"]

    login_b = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": "13800138022", "code": "123456", "device_id": "ios-device-022"},
        headers=make_headers(idempotent=True),
    )
    assert login_b.status_code == 200
    data_b = login_b.json()["data"]
    token_b = data_b["access_token"]
    session_b = data_b["session_id"]

    malicious_logout = client.post(
        "/api/v1/auth/logout",
        json={"session_id": session_b},
        headers=make_headers(idempotent=True, token=token_a),
    )
    assert malicious_logout.status_code == 200
    assert malicious_logout.json()["data"]["success"] is False

    b_access_still_valid = client.get("/api/v1/inventory/items", headers=make_headers(token=token_b))
    assert b_access_still_valid.status_code == 200


def test_session_limit_kicks_oldest_and_writes_security_event(client):
    phone = "13800138066"
    access_tokens: list[str] = []
    user_id = ""

    for index in range(4):
        login_resp = client.post(
            "/api/v1/auth/sms/login",
            json={"phone": phone, "code": "123456", "device_id": f"ios-device-limit-{index + 1}"},
            headers=make_headers(idempotent=True),
        )
        assert login_resp.status_code == 200
        data = login_resp.json()["data"]
        access_tokens.append(data["access_token"])
        user_id = data["user_profile"]["user_id"]

    oldest_access = access_tokens[0]
    newest_access = access_tokens[-1]

    oldest_resp = client.get("/api/v1/inventory/items", headers=make_headers(token=oldest_access))
    assert oldest_resp.status_code == 401
    assert oldest_resp.json()["code"] == "AUTH_401_TOKEN_EXPIRED"

    newest_resp = client.get("/api/v1/inventory/items", headers=make_headers(token=newest_access))
    assert newest_resp.status_code == 200

    events = store.list_security_events(user_id)
    assert any(event["event_type"] == "SESSION_EVICTED" for event in events)
    eviction = next(event for event in events if event["event_type"] == "SESSION_EVICTED")
    assert eviction["details"]["reason"] == "MAX_ACTIVE_SESSIONS"
    assert eviction["details"]["max_active_sessions"] == 3


def test_admin_endpoints_require_admin_role(client):
    login_resp = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": "13800138033", "code": "123456", "device_id": "ios-device-033"},
        headers=make_headers(idempotent=True),
    )
    token = login_resp.json()["data"]["access_token"]

    dash = client.get("/api/v1/admin/dashboard/summary", headers=make_headers(token=token))
    assert dash.status_code == 403
    assert dash.json()["code"] == "AUTH_403_FORBIDDEN"


def test_admin_endpoints_exist_for_admin(client):
    login_resp = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": "13900139000", "code": "123456", "device_id": "ios-device-002"},
        headers=make_headers(idempotent=True),
    )
    admin_data = login_resp.json()["data"]
    token = admin_data["access_token"]
    admin_user_id = admin_data["user_profile"]["user_id"]

    dash = client.get("/api/v1/admin/dashboard/summary", headers=make_headers(token=token))
    assert dash.status_code == 200
    dash_data = dash.json()["data"]
    assert "ai_runtime" in dash_data
    assert "parser_provider" in dash_data["ai_runtime"]
    assert "parser_breaker_open" in dash_data["ai_runtime"]

    users = client.get("/api/v1/admin/users", headers=make_headers(token=token))
    assert users.status_code == 200

    tasks = client.get("/api/v1/admin/audit/tasks", headers=make_headers(token=token))
    assert tasks.status_code == 200

    target_login = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": "13800138077", "code": "123456", "device_id": "ios-device-077"},
        headers=make_headers(idempotent=True),
    )
    target_token = target_login.json()["data"]["access_token"]
    target_user_id = target_login.json()["data"]["user_profile"]["user_id"]

    revoke = client.post(
        f"/api/v1/admin/users/{target_user_id}/session/revoke",
        json={"reason": "security incident"},
        headers=make_headers(idempotent=True, token=token),
    )
    assert revoke.status_code == 200
    approval_request = revoke.json()["data"]["approval_request"]
    assert approval_request["status"] == "PENDING"
    approval_id = approval_request["approval_id"]

    target_before_approve = client.get("/api/v1/inventory/items", headers=make_headers(token=target_token))
    assert target_before_approve.status_code == 200

    reviewer_login = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": "13900139001", "code": "123456", "device_id": "web-auditor-002"},
        headers=make_headers(idempotent=True),
    )
    reviewer_user_id = reviewer_login.json()["data"]["user_profile"]["user_id"]
    reviewer_token = reviewer_login.json()["data"]["access_token"]

    approvals = client.get("/api/v1/admin/approvals", headers=make_headers(token=reviewer_token))
    assert approvals.status_code == 200
    assert approvals.json()["data"]["total"] >= 1

    review = client.post(
        f"/api/v1/admin/approvals/{approval_id}/review",
        json={"decision": "APPROVE", "comment": "approved"},
        headers=make_headers(idempotent=True, token=reviewer_token),
    )
    assert review.status_code == 200
    reviewed_approval = review.json()["data"]["approval_request"]
    assert reviewed_approval["status"] == "APPROVED"
    assert reviewed_approval["execution_result"]["revoked_sessions"] >= 1

    target_after_approve = client.get("/api/v1/inventory/items", headers=make_headers(token=target_token))
    assert target_after_approve.status_code == 401

    events = store.list_security_events(admin_user_id)
    assert any(event["event_type"] == "ADMIN_APPROVAL_REQUEST_CREATED" for event in events)
    reviewer_events = store.list_security_events(reviewer_user_id)
    assert any(event["event_type"] == "ADMIN_APPROVAL_REVIEWED" for event in reviewer_events)


def test_admin_cannot_self_approve_request(client):
    admin_login = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": "13900139000", "code": "123456", "device_id": "web-admin-approval"},
        headers=make_headers(idempotent=True),
    )
    admin_token = admin_login.json()["data"]["access_token"]

    target_login = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": "13800138088", "code": "123456", "device_id": "ios-device-088"},
        headers=make_headers(idempotent=True),
    )
    target_user_id = target_login.json()["data"]["user_profile"]["user_id"]

    create_req = client.post(
        f"/api/v1/admin/users/{target_user_id}/session/revoke",
        json={"reason": "test self-approve"},
        headers=make_headers(idempotent=True, token=admin_token),
    )
    assert create_req.status_code == 200
    approval_id = create_req.json()["data"]["approval_request"]["approval_id"]

    self_review = client.post(
        f"/api/v1/admin/approvals/{approval_id}/review",
        json={"decision": "APPROVE"},
        headers=make_headers(idempotent=True, token=admin_token),
    )
    assert self_review.status_code == 403
    assert self_review.json()["code"] == "AUTH_403_FORBIDDEN"


def test_auditor_permissions_for_admin_module(client):
    login_resp = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": "13900139001", "code": "123456", "device_id": "web-auditor-001"},
        headers=make_headers(idempotent=True),
    )
    token = login_resp.json()["data"]["access_token"]

    dash = client.get("/api/v1/admin/dashboard/summary", headers=make_headers(token=token))
    assert dash.status_code == 403
    assert dash.json()["code"] == "AUTH_403_FORBIDDEN"

    users = client.get("/api/v1/admin/users", headers=make_headers(token=token))
    assert users.status_code == 403
    assert users.json()["code"] == "AUTH_403_FORBIDDEN"

    tasks = client.get("/api/v1/admin/audit/tasks", headers=make_headers(token=token))
    assert tasks.status_code == 200
    approvals = client.get("/api/v1/admin/approvals", headers=make_headers(token=token))
    assert approvals.status_code == 200


def test_security_events_endpoint_requires_reviewer_role(client):
    login_resp = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": "13800138044", "code": "123456", "device_id": "ios-device-044"},
        headers=make_headers(idempotent=True),
    )
    token = login_resp.json()["data"]["access_token"]

    resp = client.get("/api/v1/admin/security/events", headers=make_headers(token=token))
    assert resp.status_code == 403
    assert resp.json()["code"] == "AUTH_403_FORBIDDEN"


def test_reviewer_can_query_security_events_with_filters(client):
    admin_login = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": "13900139000", "code": "123456", "device_id": "web-admin-030"},
        headers=make_headers(idempotent=True),
    )
    admin_token = admin_login.json()["data"]["access_token"]

    target_login = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": "13800138130", "code": "123456", "device_id": "ios-device-130"},
        headers=make_headers(idempotent=True),
    )
    target_user_id = target_login.json()["data"]["user_profile"]["user_id"]

    create_req = client.post(
        f"/api/v1/admin/users/{target_user_id}/session/revoke",
        json={"reason": "security query filter test"},
        headers=make_headers(idempotent=True, token=admin_token),
    )
    assert create_req.status_code == 200
    approval_id = create_req.json()["data"]["approval_request"]["approval_id"]

    reviewer_login = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": "13900139001", "code": "123456", "device_id": "web-auditor-030"},
        headers=make_headers(idempotent=True),
    )
    reviewer_token = reviewer_login.json()["data"]["access_token"]
    reviewer_user_id = reviewer_login.json()["data"]["user_profile"]["user_id"]

    review_req = client.post(
        f"/api/v1/admin/approvals/{approval_id}/review",
        json={"decision": "APPROVE", "comment": "approved for security list query"},
        headers=make_headers(idempotent=True, token=reviewer_token),
    )
    assert review_req.status_code == 200

    resp = client.get(
        f"/api/v1/admin/security/events?user_id={reviewer_user_id}&event_type=ADMIN_APPROVAL_REVIEWED&limit=5",
        headers=make_headers(token=reviewer_token),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 1
    row = data["list"][0]
    assert row["user_id"] == reviewer_user_id
    assert row["event_type"] == "ADMIN_APPROVAL_REVIEWED"
    assert "event_id" in row
    assert "created_at" in row


def test_suggestion_and_audit_db_flow(client):
    user_login_resp = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": "13700137000", "code": "123456", "device_id": "ios-device-003"},
        headers=make_headers(idempotent=True),
    )
    user_token = user_login_resp.json()["data"]["access_token"]

    gen = client.post(
        "/api/v1/suggestions/generate",
        json={"mode": "MANUAL"},
        headers=make_headers(idempotent=True, token=user_token),
    )
    assert gen.status_code == 200
    assert "suggestion_id" in gen.json()["data"]

    latest = client.get("/api/v1/suggestions/latest", headers=make_headers(token=user_token))
    assert latest.status_code == 200
    assert latest.json()["data"]["suggestion"]["mode"] in {"MANUAL", "AUTO"}

    # Create audit task via voice parse
    parse = client.post(
        "/api/v1/ai/voice/parse",
        json={"audio_url": "https://example.com/a.m4a", "locale": "zh-CN"},
        headers=make_headers(idempotent=True, token=user_token),
    )
    assert parse.status_code == 200

    admin_login_resp = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": "13900139000", "code": "123456", "device_id": "web-admin-001"},
        headers=make_headers(idempotent=True),
    )
    admin_data = admin_login_resp.json()["data"]
    admin_token = admin_data["access_token"]
    admin_user_id = admin_data["user_profile"]["user_id"]

    list_resp = client.get("/api/v1/admin/audit/tasks", headers=make_headers(token=admin_token))
    assert list_resp.status_code == 200
    assert list_resp.json()["data"]["total"] >= 1
    task_id = list_resp.json()["data"]["list"][0]["task_id"]

    review = client.post(
        f"/api/v1/admin/audit/tasks/{task_id}/review",
        json={"action": "APPROVE"},
        headers=make_headers(idempotent=True, token=admin_token),
    )
    assert review.status_code == 200
    assert review.json()["data"]["status"] == "DONE"

    events = store.list_security_events(admin_user_id)
    assert any(event["event_type"] == "ADMIN_AUDIT_REVIEW" and event["details"]["task_id"] == task_id for event in events)


def test_parse_confirm_returns_inventory_snapshot(client):
    login_resp = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": "13700137099", "code": "123456", "device_id": "ios-device-099"},
        headers=make_headers(idempotent=True),
    )
    token = login_resp.json()["data"]["access_token"]

    parse = client.post(
        "/api/v1/ai/ocr/parse",
        json={"image_urls": ["https://example.com/demo.jpg"]},
        headers=make_headers(idempotent=True, token=token),
    )
    assert parse.status_code == 200
    parse_data = parse.json()["data"]

    confirm = client.post(
        "/api/v1/ai/parse/confirm",
        json={"session_id": parse_data["session_id"], "entities": parse_data["entities"]},
        headers=make_headers(idempotent=True, token=token),
    )
    assert confirm.status_code == 200
    snapshot = confirm.json()["data"]["inventory_snapshot"]
    assert snapshot["updated_count"] == len(parse_data["entities"])
    assert len(snapshot["items"]) >= 1


def test_ai_parse_pipeline_session_and_entity_contract(client):
    login_resp = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": "13700137101", "code": "123456", "device_id": "ios-device-101"},
        headers=make_headers(idempotent=True),
    )
    token = login_resp.json()["data"]["access_token"]

    voice_1 = client.post(
        "/api/v1/ai/voice/parse",
        json={"audio_url": "https://example.com/voice-egg.m4a", "locale": "zh-CN"},
        headers=make_headers(idempotent=True, token=token),
    )
    assert voice_1.status_code == 200
    data_1 = voice_1.json()["data"]
    assert data_1["session_id"].startswith("parse-v-")
    assert data_1["confidence"] > 0
    assert all(entity["parse_session_id"] == data_1["session_id"] for entity in data_1["entities"])

    voice_2 = client.post(
        "/api/v1/ai/voice/parse",
        json={"audio_url": "https://example.com/voice-pork.m4a", "locale": "zh-CN"},
        headers=make_headers(idempotent=True, token=token),
    )
    assert voice_2.status_code == 200
    data_2 = voice_2.json()["data"]
    assert data_2["session_id"] != data_1["session_id"]

    ocr = client.post(
        "/api/v1/ai/ocr/parse",
        json={"image_urls": ["https://example.com/yogurt-ticket.jpg"]},
        headers=make_headers(idempotent=True, token=token),
    )
    assert ocr.status_code == 200
    ocr_data = ocr.json()["data"]
    assert ocr_data["session_id"].startswith("parse-o-")
    assert "unknown_items" in ocr_data
    assert all(entity["parse_session_id"] == ocr_data["session_id"] for entity in ocr_data["entities"])


def test_push_preference_and_jobs(client):
    login_resp = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": "13600136000", "code": "123456", "device_id": "ios-device-004"},
        headers=make_headers(idempotent=True),
    )
    token = login_resp.json()["data"]["access_token"]
    register = client.post(
        "/api/v1/push/device/register",
        json={"platform": "ios", "device_token": "token-abc-001"},
        headers=make_headers(idempotent=True, token=token),
    )
    assert register.status_code == 200
    assert register.json()["data"]["registered"] is True

    pref = client.put(
        "/api/v1/push/preference",
        json={"enabled": True, "notify_time": "20:00"},
        headers=make_headers(idempotent=True, token=token),
    )
    assert pref.status_code == 200
    assert pref.json()["data"]["preference"]["enabled"] is True

    decay_result = store.run_auto_decay_for_all()
    assert decay_result["processed_households"] >= 1

    reminder_result = store.run_purchase_reminders_for_all()
    assert reminder_result["processed_households"] >= 1

    stats = store.get_push_delivery_stats()
    assert stats["sent"] + stats["failed"] + stats["skipped"] >= 1


def test_inventory_conflict_response(client):
    login_resp = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": "13500135000", "code": "123456", "device_id": "ios-device-005"},
        headers=make_headers(idempotent=True),
    )
    token = login_resp.json()["data"]["access_token"]
    items_resp = client.get("/api/v1/inventory/items", headers=make_headers(token=token))
    egg = next(item for item in items_resp.json()["data"]["items"] if item["item_key"] == "EGG")
    server_version = egg["server_version"]

    ok = client.post(
        "/api/v1/inventory/operations/batch",
        json={
            "operations": [
                {
                    "item_key": "EGG",
                    "operation": "ADD",
                    "value": 1,
                    "unit": "个",
                    "source": "MANUAL",
                    "client_version": server_version,
                    "op_id": "op-conflict-ok",
                }
            ]
        },
        headers=make_headers(idempotent=True, token=token),
    )
    assert ok.status_code == 200

    conflict = client.post(
        "/api/v1/inventory/operations/batch",
        json={
            "operations": [
                {
                    "item_key": "EGG",
                    "operation": "ADD",
                    "value": 1,
                    "unit": "个",
                    "source": "MANUAL",
                    "client_version": server_version,
                    "op_id": "op-conflict-fail",
                }
            ]
        },
        headers=make_headers(idempotent=True, token=token),
    )
    assert conflict.status_code == 409
    body = conflict.json()
    assert body["code"] == "BIZ_409_CONFLICT"
    assert body["retriable"] is True
    assert body["details"]["item_key"] == "EGG"


def test_offline_replay_queue_flow(client):
    login_resp = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": "13400134000", "code": "123456", "device_id": "ios-device-006"},
        headers=make_headers(idempotent=True),
    )
    token = login_resp.json()["data"]["access_token"]

    items_resp = client.get("/api/v1/inventory/items", headers=make_headers(token=token))
    egg_before = next(item for item in items_resp.json()["data"]["items"] if item["item_key"] == "EGG")

    enqueue_resp = client.post(
        "/api/v1/inventory/offline/replay",
        json={
            "offline_ops": [
                {
                    "op_id": "offline-op-0001",
                    "created_at": "2026-03-31T13:20:00Z",
                    "retry_count": 0,
                    "payload": {
                        "operations": [
                            {
                                "item_key": "EGG",
                                "operation": "ADD",
                                "value": 2,
                                "unit": "个",
                                "source": "MANUAL",
                                "client_version": egg_before["server_version"],
                                "op_id": "offline-op-0001",
                            }
                        ]
                    },
                }
            ]
        },
        headers=make_headers(idempotent=True, token=token),
    )
    assert enqueue_resp.status_code == 200
    assert enqueue_resp.json()["data"]["queued_count"] == 1

    task_result = run_offline_replay_queue_task()
    assert task_result["processed_jobs"] >= 1

    items_after_resp = client.get("/api/v1/inventory/items", headers=make_headers(token=token))
    egg_after = next(item for item in items_after_resp.json()["data"]["items"] if item["item_key"] == "EGG")
    assert egg_after["current_stock"] == egg_before["current_stock"] + 2
