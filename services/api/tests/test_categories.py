from __future__ import annotations

from conftest import make_headers


def _login(client, phone: str) -> str:
    resp = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": phone, "code": "123456", "device_id": "ios-device-cat"},
        headers=make_headers(idempotent=True),
    )
    assert resp.status_code == 200
    return resp.json()["data"]["access_token"]


def test_categories_list_includes_system_defaults(client):
    token = _login(client, "13800138500")
    resp = client.get("/api/v1/categories", headers=make_headers(token=token))
    assert resp.status_code == 200
    data = resp.json()["data"]
    names = {category["name"] for category in data["categories"]}
    assert len(names) == 6
    assert "鸡蛋" in names
    assert "牛奶" in names
    assert all(category["is_system"] for category in data["categories"])


def test_create_custom_category(client):
    token = _login(client, "13800138501")
    create_resp = client.post(
        "/api/v1/categories",
        json={"name": "苹果", "icon": "🍎", "unit_type": "个"},
        headers=make_headers(idempotent=True, token=token),
    )
    assert create_resp.status_code == 200
    category = create_resp.json()["data"]["category"]
    assert category["name"] == "苹果"
    assert category["unit_type"] == "个"
    assert category["is_system"] is False

    list_resp = client.get("/api/v1/categories", headers=make_headers(token=token))
    names = {c["name"] for c in list_resp.json()["data"]["categories"]}
    assert "苹果" in names


def test_create_custom_category_also_creates_inventory_item(client):
    token = _login(client, "13800138507")
    create_resp = client.post(
        "/api/v1/categories",
        json={"name": "葡萄", "unit_type": "串"},
        headers=make_headers(idempotent=True, token=token),
    )
    assert create_resp.status_code == 200

    items_resp = client.get("/api/v1/inventory/items", headers=make_headers(token=token))
    assert items_resp.status_code == 200
    item_names = {item["item_name"] for item in items_resp.json()["data"]["items"]}
    assert "葡萄" in item_names


def test_update_custom_category(client):
    token = _login(client, "13800138502")
    create_resp = client.post(
        "/api/v1/categories",
        json={"name": "香梨", "unit_type": "个"},
        headers=make_headers(idempotent=True, token=token),
    )
    category_id = create_resp.json()["data"]["category"]["category_id"]

    update_resp = client.patch(
        f"/api/v1/categories/{category_id}",
        json={"name": "新疆香梨", "unit_type": "kg"},
        headers=make_headers(idempotent=True, token=token),
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()["data"]["category"]
    assert updated["name"] == "新疆香梨"
    assert updated["unit_type"] == "kg"


def test_cannot_update_system_category(client):
    token = _login(client, "13800138503")
    list_resp = client.get("/api/v1/categories", headers=make_headers(token=token))
    system_category = next(c for c in list_resp.json()["data"]["categories"] if c["is_system"])

    update_resp = client.patch(
        f"/api/v1/categories/{system_category['category_id']}",
        json={"name": "被篡改"},
        headers=make_headers(idempotent=True, token=token),
    )
    assert update_resp.status_code == 403
    assert update_resp.json()["code"] == "AUTH_403_FORBIDDEN"


def test_delete_custom_category(client):
    token = _login(client, "13800138504")
    create_resp = client.post(
        "/api/v1/categories",
        json={"name": "蓝莓", "unit_type": "盒"},
        headers=make_headers(idempotent=True, token=token),
    )
    category_id = create_resp.json()["data"]["category"]["category_id"]

    delete_resp = client.delete(f"/api/v1/categories/{category_id}", headers=make_headers(idempotent=True, token=token))
    assert delete_resp.status_code == 200

    list_resp = client.get("/api/v1/categories", headers=make_headers(token=token))
    ids = {c["category_id"] for c in list_resp.json()["data"]["categories"]}
    assert category_id not in ids


def test_cannot_delete_system_category(client):
    token = _login(client, "13800138505")
    list_resp = client.get("/api/v1/categories", headers=make_headers(token=token))
    system_category = next(c for c in list_resp.json()["data"]["categories"] if c["is_system"])

    delete_resp = client.delete(f"/api/v1/categories/{system_category['category_id']}", headers=make_headers(idempotent=True, token=token))
    assert delete_resp.status_code == 403
    assert delete_resp.json()["code"] == "AUTH_403_FORBIDDEN"


def test_cannot_delete_category_in_use(client):
    token = _login(client, "13800138506")
    create_resp = client.post(
        "/api/v1/categories",
        json={"name": "橙子", "unit_type": "个"},
        headers=make_headers(idempotent=True, token=token),
    )
    category_id = create_resp.json()["data"]["category"]["category_id"]

    # Find the auto-created inventory item and perform an operation to create activity history.
    items_resp = client.get("/api/v1/inventory/items", headers=make_headers(token=token))
    custom_item = next(item for item in items_resp.json()["data"]["items"] if item["item_name"] == "橙子")
    batch_resp = client.post(
        "/api/v1/inventory/operations/batch",
        json={
            "operations": [
                {
                    "item_key": custom_item["item_key"],
                    "operation": "ADD",
                    "value": 1,
                    "unit": "个",
                    "source": "MANUAL",
                }
            ]
        },
        headers=make_headers(idempotent=True, token=token),
    )
    assert batch_resp.status_code == 200

    delete_resp = client.delete(f"/api/v1/categories/{category_id}", headers=make_headers(idempotent=True, token=token))
    assert delete_resp.status_code == 409
    assert delete_resp.json()["code"] == "BIZ_409_CONFLICT"


def test_category_isolation(client):
    token_a = _login(client, "13800138510")
    token_b = _login(client, "13800138511")

    create_a = client.post(
        "/api/v1/categories",
        json={"name": "樱桃", "unit_type": "盒"},
        headers=make_headers(idempotent=True, token=token_a),
    )
    category_id_a = create_a.json()["data"]["category"]["category_id"]

    list_b = client.get("/api/v1/categories", headers=make_headers(token=token_b))
    ids_b = {c["category_id"] for c in list_b.json()["data"]["categories"]}
    assert category_id_a not in ids_b

    patch_b = client.patch(
        f"/api/v1/categories/{category_id_a}",
        json={"name": "盆栽"},
        headers=make_headers(idempotent=True, token=token_b),
    )
    assert patch_b.status_code == 404


def test_custom_category_can_be_used_in_inventory_batch(client):
    token = _login(client, "13800138512")
    create_resp = client.post(
        "/api/v1/categories",
        json={"name": "芒果", "unit_type": "支"},
        headers=make_headers(idempotent=True, token=token),
    )
    assert create_resp.status_code == 200

    # Find the inventory item that was auto-created for the new category.
    items_resp = client.get("/api/v1/inventory/items", headers=make_headers(token=token))
    custom_item = next(item for item in items_resp.json()["data"]["items"] if item["item_name"] == "芒果")

    batch_resp = client.post(
        "/api/v1/inventory/operations/batch",
        json={
            "operations": [
                {
                    "item_key": custom_item["item_key"],
                    "operation": "ADD",
                    "value": 5,
                    "unit": "支",
                    "source": "MANUAL",
                }
            ]
        },
        headers=make_headers(idempotent=True, token=token),
    )
    assert batch_resp.status_code == 200
    updated = batch_resp.json()["data"]["updated_items"][0]
    assert updated["item_key"] == custom_item["item_key"]
    assert updated["server_version"] >= 2
