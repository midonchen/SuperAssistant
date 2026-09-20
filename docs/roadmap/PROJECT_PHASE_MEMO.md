# SuperAssistant 项目阶段备忘录

> 文档用途：回溯 MVP（Phase 1）完成情况，规划下一阶段（v1.5 / Phase 2）开发内容。
> 生成时间：2026-09-20（基于仓库当前 main 分支 HEAD `19c8139`）。

---

## 1. 项目总览

| 项目 | 说明 |
|------|------|
| 产品名 | LifeOS Assistant / SuperAssistant |
| 仓库 | `/Users/misu/Documents/SuperAssistant`（`git@github.com:midonchen/SuperAssistant.git`） |
| 当前分支 | `main`，与 `origin/main` 同步 |
| 当前 HEAD | `19c8139 feat(release): staging deployment + non-local gray waves complete (part 45)` |
| 产品阶段 | PRD v1.1 定义的 **MVP Phase 1（生活物资管理）已完成**；准备进入 **v1.5 Phase 2（物资模块深化）** |
| 实现阶段 | Phase 0–6 全部完成（`make phase-status`：phase=Phase 6, part=45, pending=0，最新报告 2026-09-20） |
| Staging | 已部署至阿里云 ECS：`http://agint.sonmuu.com:8000`，非本地灰度 WAVE 10/50/100 全部 PASS |

---

## 2. Phase 1（MVP · 生活物资管理）完成情况

### 2.1 范围与目标

依据 `SuperAssistant_PRD_v1.1.md`，MVP 聚焦三大痛点：

1. **录入繁琐** → 语音多实体录入 + OCR 小票识别；
2. **库存不清** → AI 自动衰减模型 + 用户随时校准；
3. **采购靠感觉** → 基于消耗模型的数据驱动采购建议。

### 2.2 已完成交付项

实现状态文档 `docs/roadmap/IMPLEMENTATION_STATUS.md` 共记录 **45 个 part**，覆盖：

- **Phase 0**：Monorepo 搭建、契约冻结、CI 门禁脚本；
- **Phase 1**：用户/会话/令牌/鉴权持久化、DB 迁移基座；
- **Phase 2**：库存/日志/AI 解析/采购建议/冲突处理/离线重放；
- **Phase 3**：Celery 定时任务（自动衰减、采购提醒）、Push 设备/偏好持久化；
- **Phase 4**：Admin Dashboard / Users / Audit / Approvals / Security Events；
- **Phase 5**：Flutter iOS 端全页面状态机 + API 集成 + 安全存储 + 离线重放 + 认证守卫；
- **Phase 6**：UAT/性能/灰度发布准备、staging 部署、非本地灰度证据、最终签核包。

### 2.3 关键质量证据

| 门禁 | 结果 |
|------|------|
| API 回归测试 | 26/26 PASS（`pytest -q services/api/tests`） |
| 治理门禁 | `npm run check:all` PASS（800 行上限、模块边界、架构评审） |
| Phase 5 验收 | `make phase5-accept` PASS |
| Phase 6 性能基线 | `make phase6-perf` PASS |
| Phase 6 外部压测 | `make phase6-load` PASS |
| Phase 6 发布包 | `make phase6-pack` PASS |
| 非本地灰度 | WAVE=10/50/100 decision=CONTINUE，`phase6-window-gate-live` PASS |

### 2.4 已知限制（MVP 明确不在范围）

- 真实 FCM/APNs 推送（当前仅记录 delivery，模拟触发）；
- 真实短信验证码通道（`/auth/sms/send` 为模拟实现）；
- 托管数据库/多副本高可用（staging 用容器内 Postgres）；
- 自定义品类、家庭共享、消费报告、暗色模式、Widget（归属 v1.5）。

### 2.5 Phase 1 结论

**完成。** 产品 MVP 已具备可灰度发布的完整闭环：移动端录入 → 后端 AI 解析/库存管理 → 定时任务 → 管理后台治理 → staging 部署。发布门禁无遗留项。

---

## 3. Phase 2（v1.5 · 物资模块深化）规划

### 3.1 目标

在 MVP 核心闭环基础上，提升**可定制性、协作深度、数据洞察与体验精致度**，为 Freemium 商业化（Pro 订阅）做准备。

### 3.2 功能范围（来自 PRD v1.1 路线图）

| 功能 | 价值 | 建议优先级 |
|------|------|-----------|
| **自定义品类** | 用户可新增/编辑/删除物资品类，突破 MVP 固定品类限制 | P0 |
| **家庭成员协作** | 多人共享家庭库存，支持权限区分（管理员/成员/只读） | P0 |
| **月度消费报告** | 自动生成消耗统计、采购成本、浪费预警，增强数据洞察 | P1 |
| **暗色模式** | 跟随系统主题，提升夜间使用体验 | P1 |
| **Widget 小组件** | iOS 主屏幕快速查看库存/待购清单，提高打开率 | P2 |

### 3.3 商业模式影响

依据 PRD 商业化路径：

| 版本 | 模式 | 免费版 | Pro 版（建议 ¥18/月） |
|------|------|--------|----------------------|
| v1.5 | Freemium | 单人物资管理、固定品类、基础报告 | 家庭共享 + 高级分析 + 无限自定义品类 + Widget |

Phase 2 需在数据模型与权限层预留 **订阅/权益** 扩展点，避免后续重构。

### 3.4 技术方案初案

#### 3.4.1 自定义品类

- 新增 `categories` 表：`id`, `household_id`, `name`, `icon`, `unit_type`, `decay_template`, `created_by`, `is_system`；
- 允许用户基于系统品类克隆或完全新建；
- AI 解析 prompt 增加 `category_id` 映射与未知品类 fallback。

#### 3.4.2 家庭成员协作

- 引入 `households` 与 `household_memberships` 表；
- 库存、采购建议、日志全部按 `household_id` 隔离；
- 邀请链路：手机号/链接邀请 → 被邀请人登录后自动加入；
- 角色：OWNER / ADMIN / MEMBER / VIEWER，与现有 `users.role`（USER/ADMIN/AUDITOR）正交；
- 离线重放队列需携带 `household_id` 并校验写入权限。

#### 3.4.3 月度消费报告

- 新增 `consumption_reports` 聚合表或按查询实时聚合；
- 数据源：`activity_logs`（入库/校准/消耗）+ `suggestions`（采购建议采纳）；
- 报告内容：月度消耗 Top N、品类周转天数、预估浪费金额、建议采购清单；
- 可选：生成 PDF/图片分享。

#### 3.4.4 暗色模式

- Flutter：`ThemeData` 扩展 `darkTheme` + `themeMode: ThemeMode.system`；
- Admin：Tailwind/CSS 增加 `dark:` 变体；
- 后端无需改动。

#### 3.4.5 Widget 小组件

- iOS Home Screen Widget（SwiftUI Widget Extension）；
- 数据接口：`GET /inventory/widgets/summary`（轻量、低频次、缓存）；
- 刷新策略：后台静默刷新 + 用户主动刷新。

### 3.5 建议里程碑

| 阶段 | 周期 | 交付物 |
|------|------|--------|
| Phase 2.1 | 2 周 | 自定义品类：后端模型/API/迁移 + 移动端品类管理页 + Admin 品类管理 |
| Phase 2.2 | 2 周 | 家庭协作：household 模型、邀请链路、权限中间件、库存隔离 |
| Phase 2.3 | 1.5 周 | 月度消费报告：聚合接口 + 移动端报告页 + PDF/图片导出 |
| Phase 2.4 | 1 周 | 暗色模式：Flutter + Admin 双端适配 |
| Phase 2.5 | 1 周 | iOS Widget：Extension、数据接口、后台刷新 |
| Phase 2.6 | 1 周 | 商业化埋点与权益门控：Pro 功能开关、订阅状态字段、灰度验收 |

**合计约 8–9 周**，与 MVP 10 周节奏相当。

### 3.6 新增数据表建议

```text
categories
households
household_memberships
household_invitations
consumption_reports
subscription_tiers          # 可选，为 Freemium 预留
user_subscriptions          # 可选，为 Freemium 预留
```

### 3.7 风险与依赖

| 风险 | 影响 | 应对 |
|------|------|------|
| household 权限模型与现有 admin RBAC 冲突 | 中 | 清晰划分：admin RBAC 管平台治理，household 角色管家庭内数据权限 |
| 多人同时编辑库存导致冲突 | 中 | 复用现有 `client_version` + `op_id` 离线重放机制 |
| 月度报告聚合查询慢 | 中 | 预生成聚合表 + 异步 Celery 任务，避免实时大表扫描 |
| Widget 后台刷新受限 | 低 | 设计为低实时性摘要，主入口仍是 App |
| Pro 权益门控设计不足导致后续重构 | 高 | Phase 2.6 预留 `subscription_tier` 字段与功能开关，即使暂不收费 |

---

## 4. 下一步行动

1. **评审本备忘录**：确认 Phase 2 范围、优先级与里程碑；
2. **输出 Phase 2 PRD/PCR**：将本规划拆分为正式 PRD 与架构变更评审（PCR）；
3. **设计数据模型**：重点评审 `households`、`household_memberships`、`categories` 与现有 `inventory_items` 的关系；
4. **创建 Phase 2 看板/任务**：按 2.1–2.6 拆分为可追踪的开发任务；
5. **更新 `docs/roadmap/MVP_10_WEEK_EXECUTION.md`**：将 Phase 2 周计划补充进路线图；
6. **保留发布能力**：Phase 2 开发期间保持 `main` 分支可随时灰度发布（MVP 已达成此能力）。

---

## 5. 附录：参考文档

- `SuperAssistant_PRD_v1.1.md` — 产品需求与路线图（v1.5 定义见 §16）。
- `docs/roadmap/IMPLEMENTATION_STATUS.md` — 已实现 part 1–45 的详细记录。
- `docs/roadmap/MVP_10_WEEK_EXECUTION.md` — MVP 10 周执行路线图。
- `docs/roadmap/status/PHASE_STATUS_REPORT_20260920_135033.md` — 最新自动生成的阶段状态报告。
- `docs/deployment/STAGING_DEPLOYMENT.md` — staging 部署与发布窗口操作手册。
- `docs/release/evidence/RELEASE_SIGNOFF_FINAL_20260914_075032.md` — Phase 6 最终签核文件。
- `docs/release/handoff/RELEASE_HANDOFF_20260914_075032.tar.gz` — Phase 6 交付交接包。

---

*备忘：本文件为规划性文档，后续 Phase 2 的每个完成增量应按项目规范以 `part N` 形式追加到 `docs/roadmap/IMPLEMENTATION_STATUS.md`。*
