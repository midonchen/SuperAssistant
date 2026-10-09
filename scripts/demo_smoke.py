import json
import time
from datetime import datetime, timedelta, timezone

import httpx

BASE = "http://agint.sonmuu.com:8000/api/v1"
HDR = {"X-Request-Id": "demo-1", "X-App-Version": "1.1.0", "X-Platform": "web-admin"}

RUN_ID = str(int(time.time()))
PHONE = f"138{RUN_ID[-8:]}"


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
    print(f"RUN phone={PHONE}")

    # 1. login demo user
    r = req("POST", "/auth/sms/login", body={"phone": PHONE, "code": "123456", "device_id": "demo-dev-1"}, idem=f"demo-login-{RUN_ID}")
    d = r.json()["data"]
    token = d["access_token"]
    p = d["user_profile"]
    print(f"1 LOGIN: HTTP {r.status_code} tier={p['subscription_tier']} household={p['household_id'][:8]}...")

    # 2. categories
    r = req("GET", "/categories", token)
    cats = r.json()["data"]["categories"]
    print(f"2 CATEGORIES: HTTP {r.status_code} count={len(cats)} all_system={all(c['is_system'] for c in cats)}")

    # 3. create custom category
    r = req("POST", "/categories", token, {"name": "酸奶", "icon": "🥛", "unit_type": "盒"}, idem=f"demo-cat-{RUN_ID}-1")
    print(f"3 CREATE CATEGORY: HTTP {r.status_code} name={r.json()['data']['category']['name']}")

    # 4. inventory
    r = req("GET", "/inventory/items", token)
    items = r.json()["data"]["items"]
    print(f"4 INVENTORY: HTTP {r.status_code} count={len(items)} has_酸奶={any(i['item_name'] == '酸奶' for i in items)}")

    # 5. add stock
    r = req("POST", "/inventory/operations/batch", token, {"operations": [{"item_key": "EGG", "operation": "ADD", "value": 10, "unit": "个", "source": "MANUAL"}]}, idem=f"demo-op-{RUN_ID}-1")
    print(f"5 BATCH OP: HTTP {r.status_code}")

    # 6. monthly report
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    r = req("GET", f"/reports/consumption/monthly?month={month}", token)
    rep = r.json()["data"]["report"]
    print(f"6 REPORT: HTTP {r.status_code} month={rep['month']} consumed={rep['total_consumed_qty']} topN={len(rep['top_consumed'])}")

    # 7. category limit (free=3)
    for i in (2, 3):
        r = req("POST", "/categories", token, {"name": f"测试品{i}", "unit_type": "个"}, idem=f"demo-cat-{RUN_ID}-{i}")
        print(f"7a CREATE CATEGORY #{i}: HTTP {r.status_code}")
    r = req("POST", "/categories", token, {"name": "超限品", "unit_type": "个"}, idem=f"demo-cat-{RUN_ID}-4")
    print(f"7b 4TH CATEGORY (expect 402): HTTP {r.status_code} code={r.json().get('code')}")

    # 8. admin login + endpoints
    r = req("POST", "/auth/sms/login", body={"phone": "13900139000", "code": "123456", "device_id": "demo-admin"}, idem=f"demo-admin-{RUN_ID}")
    atoken = r.json()["data"]["access_token"]
    r = req("GET", "/admin/households", atoken)
    print(f"8a ADMIN HOUSEHOLDS: HTTP {r.status_code} total={r.json()['data']['total']}")
    r = req("GET", "/admin/reports/overview", atoken)
    ov = r.json()["data"]
    print(f"8b ADMIN REPORTS: HTTP {r.status_code} total={ov['total']}")
    r = req("GET", "/admin/users", atoken)
    users = r.json()["data"]["list"]
    print(f"8c ADMIN USERS: HTTP {r.status_code} total={len(users)} first_tier={users[0]['subscription_tier'] if users else '-'}")
    r = req("GET", "/admin/analytics", atoken)
    an = r.json()["data"]
    print(f"8d ADMIN ANALYTICS: HTTP {r.status_code} summary={an['summary']}")

    # 9. v2.0 tasks + AI prioritization
    req("POST", "/tasks", token, {"title": "交水电费", "priority": 2}, idem=f"demo-task-{RUN_ID}-1")
    req("POST", "/tasks", token, {"title": "写周报", "priority": 3}, idem=f"demo-task-{RUN_ID}-2")
    r = req("POST", "/tasks/prioritize", token, idem=f"demo-prio-{RUN_ID}")
    pt = r.json()["data"]
    print(f"9 TASKS PRIORITIZE: HTTP {r.status_code} method={pt['method']} order={[t['title'] for t in pt['tasks']]}")

    # 10. v2.0 meeting summary + action items
    r = req("POST", "/meetings", token, {"title": "家庭采购会", "transcript": "讨论下周采购。待办：采购鸡蛋和牛奶"}, idem=f"demo-meet-{RUN_ID}")
    mt = r.json()["data"]["meeting"]
    print(f"10 MEETING: HTTP {r.status_code} summary={mt['summary'][:36]} action_items={len(mt['action_items'])}")

    # 11. v2.0 calendar + iCal
    start = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    r = req("GET", f"/calendar/events?start_date={start}", token)
    ev = r.json()["data"]["events"]
    print(f"11 CALENDAR: HTTP {r.status_code} events={len(ev)} sources={[e['source'] for e in ev]}")
    r = req("GET", "/calendar/ical", token)
    print(f"11b ICAL: HTTP {r.status_code} type={r.headers.get('content-type')} vcal={'BEGIN:VCALENDAR' in r.text}")

    # 12. v2.0 weekly report
    r = req("POST", "/weekly-reports/generate", token, idem=f"demo-wr-{RUN_ID}")
    wr = r.json()["data"]["report"]
    print(f"12 WEEKLY REPORT: HTTP {r.status_code} week={wr['week_start']} head={wr['content'][:36]}")

    # 13. v3.0 relationships
    r = req("POST", "/contacts", token, {"name": "妈妈", "relationship": "母亲", "birthday": "10-04"}, idem=f"demo-ct-{RUN_ID}")
    cid = r.json()["data"]["contact"]["contact_id"]
    print(f"13 CONTACT: HTTP {r.status_code} name={r.json()['data']['contact']['name']}")
    r = req("GET", f"/contacts/{cid}/occasions", token)
    oid = r.json()["data"]["occasions"][0]["occasion_id"]
    print(f"13b OCCASION: HTTP {r.status_code} name={r.json()['data']['occasions'][0]['name']}")
    r = req("POST", f"/contacts/{cid}/gifts", token, {"occasion_id": oid, "budget": 300}, idem=f"demo-gift-{RUN_ID}")
    print(f"13c GIFT: HTTP {r.status_code} content={r.json()['data']['suggestion']['content'][:40]}")
    r = req("POST", "/family-affairs", token, {"title": "交物业费", "due_at": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()}, idem=f"demo-fa-{RUN_ID}")
    print(f"13d FAMILY AFFAIR: HTTP {r.status_code}")

    # 14. v3.x career
    r = req("POST", "/career-goals", token, {"title": "晋升高级工程师", "target_year": 2027}, idem=f"demo-cg-{RUN_ID}")
    print(f"14 CAREER GOAL: HTTP {r.status_code} title={r.json()['data']['goal']['title']}")
    r = req("POST", "/skills", token, {"name": "Python", "level": 3, "target_level": 5}, idem=f"demo-sk-{RUN_ID}")
    print(f"14b SKILL: HTTP {r.status_code} name={r.json()['data']['skill']['name']}")
    r = req("POST", "/job-applications", token, {"company": "字节跳动", "position": "后端工程师"}, idem=f"demo-ja-{RUN_ID}")
    print(f"14c APPLICATION: HTTP {r.status_code} company={r.json()['data']['application']['company']}")
    r = req("POST", "/learning-items", token, {"title": "系统设计", "item_type": "course"}, idem=f"demo-li-{RUN_ID}")
    print(f"14d LEARNING: HTTP {r.status_code} title={r.json()['data']['item']['title']}")
    r = req("POST", "/career/advice", token, idem=f"demo-advice-{RUN_ID}")
    print(f"14e CAREER ADVICE: HTTP {r.status_code} head={r.json()['data']['advice'][:40]}")

    # 15. v3.1 growth (成长方向)
    r = req("POST", "/thinking-models", token, {"name": "多元思维模型", "description": "用不同学科思维模型看问题"}, idem=f"demo-tm-{RUN_ID}")
    print(f"15 THINKING MODEL: HTTP {r.status_code} name={r.json()['data']['entry']['name']}")
    r = req("POST", "/value-principles", token, {"name": "成长放首位", "description": "成长优先于短期利益"}, idem=f"demo-vp-{RUN_ID}")
    print(f"15b VALUE PRINCIPLE: HTTP {r.status_code} name={r.json()['data']['entry']['name']}")
    r = req("POST", "/habits", token, {"name": "早睡早起", "schedule": "22:30"}, idem=f"demo-hb-{RUN_ID}")
    hid = r.json()["data"]["habit"]["habit_id"]
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    r = req("POST", f"/habits/{hid}/checkin", token, {"checkin_date": today}, idem=f"demo-hc-{RUN_ID}")
    print(f"15c HABIT CHECKIN: HTTP {r.status_code} streak={r.json()['data']['streak']}")
    r = req("POST", "/workouts", token, {"workout_type": "run", "duration_minutes": 30, "distance_km": 5, "workout_date": today}, idem=f"demo-wk-{RUN_ID}")
    print(f"15d WORKOUT: HTTP {r.status_code} type={r.json()['data']['workout']['workout_type']}")
    req("POST", "/assets", token, {"name": "银行存款", "category": "cash", "amount": 100000}, idem=f"demo-as-{RUN_ID}")
    req("POST", "/assets", token, {"name": "股票账户", "category": "stock", "amount": 50000}, idem=f"demo-as2-{RUN_ID}")
    r = req("GET", "/assets", token)
    print(f"15e ASSETS: HTTP {r.status_code} total={r.json()['data']['total']}")
    r = req("POST", "/investments", token, {"name": "指数基金", "amount": 10000, "return_rate": 8.5}, idem=f"demo-iv-{RUN_ID}")
    print(f"15f INVESTMENT: HTTP {r.status_code} name={r.json()['data']['investment']['name']}")
    r = req("POST", "/journal", token, {"content": "今日感悟：知易行难，重在坚持"}, idem=f"demo-jn-{RUN_ID}")
    print(f"15g JOURNAL: HTTP {r.status_code}")
    r = req("POST", "/life-goals", token, {"dimension": "health", "title": "保持身体健康"}, idem=f"demo-lg-{RUN_ID}")
    print(f"15h LIFE GOAL: HTTP {r.status_code} title={r.json()['data']['goal']['title']}")
    r = req("GET", "/admin/growth/overview", atoken)
    gtot = r.json()["data"]["totals"]
    print(f"15i ADMIN GROWTH: HTTP {r.status_code} totals={gtot}")


if __name__ == "__main__":
    main()
