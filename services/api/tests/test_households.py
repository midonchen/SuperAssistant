import pytest
from fastapi.testclient import TestClient

from core.models import CategoryModel, InventoryItemModel
from conftest import make_headers


@pytest.fixture
def alice_client(client: TestClient) -> tuple[TestClient, str, str, str]:
    """Register and return (client, token, user_id, household_id)."""
    resp = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": "+8613800000001", "code": "123456", "device_id": "device-alice"},
        headers=make_headers(idempotency_key="alice-login"),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    profile = data["user_profile"]
    return client, data["access_token"], profile["user_id"], profile["household_id"]


@pytest.fixture
def bob_client(client: TestClient) -> tuple[TestClient, str, str, str]:
    resp = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": "+8613800000002", "code": "123456", "device_id": "device-bob"},
        headers=make_headers(idempotency_key="bob-login"),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    profile = data["user_profile"]
    return client, data["access_token"], profile["user_id"], profile["household_id"]


def test_user_gets_personal_household(alice_client):
    client, token, user_id, household_id = alice_client
    assert household_id
    resp = client.get("/api/v1/households/me", headers=make_headers(token=token))
    assert resp.status_code == 200
    data = resp.json()["data"]["household"]
    assert data["household_id"] == household_id
    assert "OWNER" in [m["role"] for m in data["members"]]


def test_household_member_can_read_inventory(alice_client):
    client, token, user_id, household_id = alice_client
    resp = client.get("/api/v1/inventory/items", headers=make_headers(token=token))
    assert resp.status_code == 200
    assert len(resp.json()["data"]["items"]) >= 1


def test_inventory_isolated_between_households(alice_client, bob_client):
    alice_client_obj, alice_token, alice_user, alice_hh = alice_client
    bob_client_obj, bob_token, bob_user, bob_hh = bob_client

    # Alice adds 5 eggs.
    resp = alice_client_obj.post(
        "/api/v1/inventory/operations/batch",
        json={
            "operations": [
                {"item_key": "EGG", "operation": "ADD", "value": 5, "unit": "piece", "source": "MANUAL"}
            ]
        },
        headers=make_headers(token=alice_token, idempotent=True),
    )
    assert resp.status_code == 200

    # Bob should not see Alice's eggs.
    resp = alice_client_obj.get("/api/v1/inventory/items", headers=make_headers(token=alice_token))
    assert resp.status_code == 200
    alice_items = {item["item_key"]: item for item in resp.json()["data"]["items"]}
    alice_egg_stock = alice_items["EGG"]["current_stock"]

    resp = bob_client_obj.get("/api/v1/inventory/items", headers=make_headers(token=bob_token))
    assert resp.status_code == 200
    bob_items = {item["item_key"]: item for item in resp.json()["data"]["items"]}
    assert bob_items["EGG"]["current_stock"] != alice_egg_stock


def test_invitation_flow(alice_client, bob_client):
    client_a, token_a, user_a, hh_a = alice_client
    client_b, token_b, user_b, hh_b = bob_client

    # Alice invites Bob.
    resp = client_a.post(
        "/api/v1/households/invitations",
        json={"role": "MEMBER"},
        headers=make_headers(token=token_a, idempotency_key="invite-bob-member"),
    )
    assert resp.status_code == 200
    invite_code = resp.json()["data"]["invitation"]["invite_code"]

    # Bob joins using the code.
    resp = client_b.post(
        "/api/v1/households/join",
        json={"invite_code": invite_code},
        headers=make_headers(token=token_b, idempotency_key="bob-join-flow"),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["household"]["household_id"] == hh_a

    # Bob now sees Alice's household inventory.
    resp = client_b.get("/api/v1/households/me", headers=make_headers(token=token_b))
    assert resp.status_code == 200
    assert resp.json()["data"]["household"]["household_id"] == hh_a


def test_viewer_cannot_write_inventory(alice_client, bob_client):
    client_a, token_a, user_a, hh_a = alice_client
    client_b, token_b, user_b, hh_b = bob_client

    resp = client_a.post(
        "/api/v1/households/invitations",
        json={"role": "VIEWER"},
        headers=make_headers(token=token_a, idempotency_key="invite-bob-viewer"),
    )
    assert resp.status_code == 200
    invite_code = resp.json()["data"]["invitation"]["invite_code"]

    resp = client_b.post(
        "/api/v1/households/join",
        json={"invite_code": invite_code},
        headers=make_headers(token=token_b, idempotency_key="bob-join-viewer"),
    )
    assert resp.status_code == 200

    resp = client_b.post(
        "/api/v1/inventory/operations/batch",
        json={
            "operations": [
                {"item_key": "EGG", "operation": "ADD", "value": 1, "unit": "piece", "source": "MANUAL"}
            ]
        },
        headers=make_headers(token=token_b, idempotent=True),
    )
    assert resp.status_code == 403


def test_invitation_expired_or_invalid(bob_client):
    client_b, token_b, user_b, hh_b = bob_client
    resp = client_b.post(
        "/api/v1/households/join",
        json={"invite_code": "INVALID"},
        headers=make_headers(token=token_b, idempotency_key="bob-join-invalid"),
    )
    assert resp.status_code == 404


def test_categories_shared_within_household(alice_client, bob_client):
    client_a, token_a, user_a, hh_a = alice_client
    client_b, token_b, user_b, hh_b = bob_client

    # Invite Bob as member.
    resp = client_a.post(
        "/api/v1/households/invitations",
        json={"role": "MEMBER"},
        headers=make_headers(token=token_a, idempotency_key="invite-bob-cat"),
    )
    invite_code = resp.json()["data"]["invitation"]["invite_code"]
    client_b.post(
        "/api/v1/households/join",
        json={"invite_code": invite_code},
        headers=make_headers(token=token_b, idempotency_key="bob-join-cat"),
    )

    # Alice creates a custom category.
    resp = client_a.post(
        "/api/v1/categories",
        json={"name": "Test Fruit", "item_key": "TEST_FRUIT", "icon": "🍎", "unit_type": "piece"},
        headers=make_headers(token=token_a, idempotency_key="alice-create-cat"),
    )
    assert resp.status_code == 200

    # Bob should see it.
    resp = client_b.get("/api/v1/categories", headers=make_headers(token=token_b))
    assert resp.status_code == 200
    names = {c["name"] for c in resp.json()["data"]["categories"]}
    assert "Test Fruit" in names
