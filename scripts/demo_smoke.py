import json
from datetime import datetime, timezone

import httpx

BASE = "http://agint.sonmuu.com:8000/api/v1"
HDR = {"X-Request-Id": "demo-1", "X-App-Version": "1.1.0", "X-Platform": "web-admin"}


def req(method, path, token=None, body=None, idem=None):
    h = dict(HDR)
    if token:
        h["Authorization"] = f"Bearer {token}"
    if idem:
        h["Idempotency-Key"] = idem
    return httpx.request(method, BASE + path, headers=h, json=body, timeout=30)


def show(label, resp, key=None):
    status = resp.status_code
    try:
        payload = resp.json()
    except Exception:
        payload = {}
    extra = ""
    if key and status < 300:
        extra = json.dumps(payload.get("data", {}).get(key), ensure_ascii=False)[:120]
    else:
        extra = payload.get("code", "") if status >= 400 else ""
    print(f"{label}: HTTP {status} {extra}")


def main():
    # 1. login demo user
    r = req("POST", "/auth/sms/login", body={"phone": "13800138000", "code": "123456", "device_id": "demo-dev-1"}, idem="demo-login-1")
    d = r.json()["data"]
    token = d["access_token"]
    p = d["user_profile"]
    print(f"1 LOGIN: HTTP {r.status_code} tier={p['subscription_tier']} household={p['household_id'][:8]}...")

    # 2. categories
    r = req("GET", "/categories", token)
    cats = r.json()["data"]["categories"]
    print(f"2 CATEGORIES: HTTP {r.status_code} count={len(cats)} all_system={all(c['is_system'] for c in cats)}")

    # 3. create custom category
    r = req("POST", "/categories", token, {"name": "酸奶", "icon": "🥛", "unit_type": "盒"}, idem="demo-cat-1")
    print(f"3 CREATE CATEGORY: HTTP {r.status_code} name={r.json()['data']['category']['name']}")

    # 4. inventory
    r = req("GET", "/inventory/items", token)
    items = r.json()["data"]["items"]
    print(f"4 INVENTORY: HTTP {r.status_code} count={len(items)} has_酸奶={any(i['item_name'] == '酸奶' for i in items)}")

    # 5. add stock
    r = req("POST", "/inventory/operations/batch", token, {"operations": [{"item_key": "EGG", "operation": "ADD", "value": 10, "unit": "个", "source": "MANUAL"}]}, idem="demo-op-1")
    print(f"5 BATCH OP: HTTP {r.status_code}")

    # 6. monthly report
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    r = req("GET", f"/reports/consumption/monthly?month={month}", token)
    rep = r.json()["data"]["report"]
    print(f"6 REPORT: HTTP {r.status_code} month={rep['month']} consumed={rep['total_consumed_qty']} topN={len(rep['top_consumed'])}")

    # 7. category limit (free=3)
    for i in (2, 3):
        r = req("POST", "/categories", token, {"name": f"测试品{i}", "unit_type": "个"}, idem=f"demo-cat-{i}")
        print(f"7a CREATE CATEGORY #{i}: HTTP {r.status_code}")
    r = req("POST", "/categories", token, {"name": "超限品", "unit_type": "个"}, idem="demo-cat-4")
    print(f"7b 4TH CATEGORY (expect 402): HTTP {r.status_code} code={r.json().get('code')}")

    # 8. admin login + endpoints
    r = req("POST", "/auth/sms/login", body={"phone": "13900139000", "code": "123456", "device_id": "demo-admin"}, idem="demo-admin-login")
    atoken = r.json()["data"]["access_token"]
    r = req("GET", "/admin/households", atoken)
    print(f"8a ADMIN HOUSEHOLDS: HTTP {r.status_code} total={r.json()['data']['total']}")
    r = req("GET", "/admin/reports/overview", atoken)
    ov = r.json()["data"]
    print(f"8b ADMIN REPORTS: HTTP {r.status_code} total={ov['total']} first_report_count={ov['list'][0]['report_count'] if ov['list'] else '-'}")
    r = req("GET", "/admin/users", atoken)
    users = r.json()["data"]["list"]
    print(f"8c ADMIN USERS: HTTP {r.status_code} total={len(users)} first_tier={users[0]['subscription_tier'] if users else '-'}")


if __name__ == "__main__":
    main()
