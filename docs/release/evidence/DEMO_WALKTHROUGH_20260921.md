# SuperAssistant 闭环演示走查（staging）

> 生成时间：2026-09-21
> 目标环境：http://agint.sonmuu.com:8000（API）、http://agint.sonmuu.com:3000（Admin，需安全组放行 3000）
> 一键脚本：`scripts/demo_smoke.py`（本地 `python scripts/demo_smoke.py` 即可复现）

## 走查闭环

录入 → 库存 → 采购建议 → 月度报告 → 权益门控 → Admin 治理

## 实测输出（2026-09-21，真实执行）

```
1 LOGIN: HTTP 200 tier=free household=7e66e774...
2 CATEGORIES: HTTP 200 count=6 all_system=True
3 CREATE CATEGORY: HTTP 200 name=酸奶
4 INVENTORY: HTTP 200 count=7 has_酸奶=True
5 BATCH OP: HTTP 200
6 REPORT: HTTP 200 month=2026-09 consumed=0.0 topN=0
7a CREATE CATEGORY #2: HTTP 200
7a CREATE CATEGORY #3: HTTP 200
7b 4TH CATEGORY (expect 402): HTTP 402 code=BIZ_402_UPGRADE_REQUIRED
8a ADMIN HOUSEHOLDS: HTTP 200 total=1
8b ADMIN REPORTS: HTTP 200 total=1 first_report_count=1
8c ADMIN USERS: HTTP 200 total=2 first_tier=free
```

## 逐步说明

1. 登录（模拟短信码 123456）→ 自动创建个人家庭（OWNER），订阅等级 free。
2. `GET /categories` → 6 个系统品类。
3. `POST /categories` → 创建自定义品类「酸奶」，自动生成库存占位。
4. `GET /inventory/items` → 7 项（6 系统 + 酸奶）。
5. `POST /inventory/operations/batch` → 入库 10 个鸡蛋。
6. `GET /reports/consumption/monthly?month=2026-09` → 月度报告（消耗按 SUBTRACT 聚合；本例仅入库故为 0，做一次消耗操作即产生 Top 消耗）。
7. 免费权益门控：第 4 个自定义品类返回 `402 BIZ_402_UPGRADE_REQUIRED`。
8. Admin 登录 → `GET /admin/households`、`GET /admin/reports/overview`、`GET /admin/users`（含订阅等级）全部 200。

## 家庭协作补充走查（可选）

- OWNER 生成邀请码：`POST /households/invitations` → `invite_code`
- 被邀请人：`POST /households/join` → 加入后共享库存
- VIEWER 只读：`POST /inventory/operations/batch` 返回 403
- 免费版成员上限 2：第 3 人邀请返回 `402 BIZ_402_UPGRADE_REQUIRED`

## 待办（演示外）

- Admin 网页外部访问：需在阿里云安全组放行 3000 端口（当前仅服务器内 localhost:3000 可达）。
- 报告导出/分享、iOS Widget、移动端升级提示与埋点（见 IMPLEMENTATION_STATUS.md）。
