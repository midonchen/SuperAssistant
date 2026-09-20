# v1.5 Phase 2 执行路线图

> 文档用途：将 `docs/roadmap/PROJECT_PHASE_MEMO.md` 中的 Phase 2 规划拆分为可执行的周计划与任务清单。
> 生效状态：已确认，进入开发排期。
> 生成时间：2026-09-20。

---

## 1. 阶段总览

| 属性 | 值 |
|---|---|
| 阶段名 | v1.5 Phase 2 · 物资模块深化 |
| 目标 | 在 MVP 闭环基础上提升可定制性、协作深度、数据洞察与体验精致度，为 Freemium 商业化做准备 |
| 周期 | 8–9 周 |
| 前置条件 | Phase 6 完成，`main` 分支处于可随时灰度发布状态 |
| 商业模式 | Freemium：免费版单人物资管理；Pro 版 ¥18/月开放家庭共享 + 高级分析 + 无限自定义品类 |

---

## 2. 周计划

### Week 1–2 · Phase 2.1 · 自定义品类

**目标**：让用户可以新增、编辑、删除物资品类，突破 MVP 固定品类限制。

**后端任务**

- [ ] 设计 `categories` 表：`id`, `household_id`, `name`, `icon`, `unit_type`, `decay_template`, `created_by`, `is_system`, `created_at`, `updated_at`。
- [ ] 创建 Alembic 迁移脚本。
- [ ] 实现 CRUD API：`GET /categories`, `POST /categories`, `PATCH /categories/{id}`, `DELETE /categories/{id}`。
- [ ] 更新 AI 解析 prompt：支持 `category_id` 映射与未知品类 fallback。
- [ ] 更新 `inventory_items` 外键关联与数据完整性约束。
- [ ] 补充 API 回归测试。

**移动端任务**

- [ ] 新增品类管理页面（列表 / 创建 / 编辑 / 删除）。
- [ ] 在手动录入、AI 确认流程中支持品类选择。
- [ ] 更新 `AppStore` 中的品类状态管理。
- [ ] 更新移动端契约模型。

**Admin 任务**

- [ ] Admin 品类管理页面（系统默认品类 + 用户自定义品类查看/禁用）。

**验收标准**

- 用户可以创建自定义品类并在录入时使用。
- 系统品类不可删除，`is_system=true` 受保护。
- AI 解析返回的品类可以绑定到自定义品类。
- 所有新 API 通过测试与治理门禁。

---

### Week 3–4 · Phase 2.2 · 家庭成员协作

**目标**：实现多人共享家庭库存，支持权限区分。

**后端任务**

- [ ] 设计 `households` 与 `household_memberships` 表。
- [ ] 创建 Alembic 迁移脚本。
- [ ] 实现邀请链路：`POST /households/invitations` 生成邀请码/链接，`POST /households/invitations/accept` 接受邀请。
- [ ]  household 角色模型：OWNER / ADMIN / MEMBER / VIEWER（与平台 admin RBAC 正交）。
- [ ]  inventory / suggestions / activity_logs / offline replay 全部按 `household_id` 隔离。
- [ ] 新增 household 权限中间件，校验写入权限。
- [ ] 离线重放队列携带 `household_id` 并校验权限。
- [ ] 补充 API 回归测试（跨 household 越权、角色边界）。

**移动端任务**

- [ ] 新增家庭管理页面（创建家庭、邀请成员、成员列表、角色显示）。
- [ ] 更新 App Store：所有库存/建议/日志操作默认使用当前 household。
- [ ] 邀请处理页面（深链接打开 App 后接受邀请）。

**Admin 任务**

- [ ] Admin Households 页面（查看家庭、成员、冻结异常家庭）。

**验收标准**

- 用户可以创建家庭并邀请其他用户。
- 被邀请人接受后可以看到共享库存。
- VIEWER 只能读，MEMBER 可以写，OWNER/ADMIN 可以管理成员。
- 用户不能访问或修改其他家庭的库存。

---

### Week 5 · Phase 2.3 · 月度消费报告

**目标**：自动生成消耗统计、采购成本、浪费预警，增强数据洞察。

**后端任务**

- [ ] 设计 `consumption_reports` 聚合表或决策是否实时聚合。
- [ ] 创建 Alembic 迁移脚本。
- [ ] 实现报告生成 Celery 任务（每月 1 日凌晨执行）。
- [ ] 实现 API：`GET /reports/consumption/monthly`（支持月份参数）。
- [ ] 报告内容：月度消耗 Top N、品类周转天数、预估浪费金额、建议采购清单。
- [ ] 补充 API 回归测试。

**移动端任务**

- [ ] 新增报告页面（月度选择、图表、Top 列表、导出按钮）。
- [ ] 支持 PDF/图片分享（Flutter `share_plus` + 截图/生成图片）。

**Admin 任务**

- [ ] Admin 报告概览页面（按 household 聚合的活跃/消费指标）。

**验收标准**

- 用户可以查看上月的消耗报告。
- 报告数据与 `activity_logs` 和 `suggestions` 一致。
- 可以导出/分享报告图片。

---

### Week 6 · Phase 2.4 · 暗色模式

**目标**：跟随系统主题，提升夜间使用体验。

**移动端任务**

- [ ] Flutter `ThemeData` 扩展 `darkTheme`。
- [ ] 设置 `themeMode: ThemeMode.system`。
- [ ] 全页面检查颜色/图标在暗色模式下的可读性。

**Admin 任务**

- [ ] Tailwind CSS 增加 `dark:` 变体。
- [ ] 检测系统主题或提供手动切换。

**验收标准**

- 系统切换暗色模式后，移动端和 Admin 自动跟随。
- 无明显可读性问题。

---

### Week 7 · Phase 2.5 · iOS Widget

**目标**：iOS 主屏幕快速查看库存/待购清单，提高打开率。

**后端任务**

- [ ] 实现轻量接口 `GET /inventory/widgets/summary`（返回低频次缓存的摘要数据）。
- [ ] 添加 API 测试。

**移动端任务**

- [ ] 创建 iOS Widget Extension（SwiftUI）。
- [ ] 设计小、中、大三种尺寸 UI。
- [ ] 实现后台刷新策略与主动刷新按钮。
- [ ] 配置 App Groups 与密钥链共享。

**验收标准**

- 用户可以在主屏幕添加 Widget。
- Widget 展示当前库存摘要或待购清单。
- 数据刷新在合理延迟内完成。

---

### Week 8 · Phase 2.6 · 商业化埋点与权益门控

**目标**：预留 Freemium 扩展点，确保后续付费功能不重构。

**后端任务**

- [ ] 设计 `subscription_tiers` 与 `user_subscriptions` 表（即使暂不收费也预留）。
- [ ] 创建 Alembic 迁移脚本。
- [ ] 实现权益检查工具函数：`can_use_feature(user, feature)`。
- [ ] 为自定义品类数量、家庭成员数量、高级报告添加门控。
- [ ] 添加订阅状态字段到用户模型与 API 响应。

**移动端任务**

- [ ] 在 Pro 功能入口展示升级提示（UI 占位，支付接入后续再做）。
- [ ] 埋点：记录自定义品类创建、家庭成员邀请、报告导出等关键行为。

**Admin 任务**

- [ ] Admin 用户列表显示订阅等级。

**验收标准**

- 免费用户达到权益上限时收到清晰的升级提示。
- 所有 Pro 功能都有门控检查。
- 埋点数据可被后续分析使用。

---

### Week 9 · 缓冲 / 灰度验收

- [ ] 全量回归测试。
- [ ] 性能与压测。
- [ ] 更新发布文档与签核。
- [ ] Staging 灰度验证。

---

## 3. 数据模型清单

新增表：

```text
categories
households
household_memberships
household_invitations
consumption_reports
subscription_tiers
user_subscriptions
```

需改动的现有表：

```text
users          -> 添加 household_id, subscription_tier_id
inventory_items -> 添加 household_id, category_id
suggestions     -> 添加 household_id
activity_logs   -> 添加 household_id
```

---

## 4. 关键设计决策

| 决策 | 选择 | 原因 |
|---|---|---|
| household 角色与平台 admin RBAC 关系 | 正交 | 避免权限模型冲突；admin RBAC 管平台治理，household 角色管家庭内数据权限 |
| 多人编辑冲突 | 复用 `client_version` + `op_id` | 已有离线重放机制，降低重复开发 |
| 报告聚合 | 预生成聚合表 + Celery | 避免实时大表扫描，提升查询性能 |
| 订阅模型 | 提前预留表和字段 | 即使 v1.5 暂不收费，也避免后续重构 |

---

## 5. 风险与应对

| 风险 | 影响 | 应对 |
|---|---|---|
| household 权限模型与现有 admin RBAC 冲突 | 中 | 清晰划分两套权限体系，写边界测试 |
| 多人同时编辑库存导致冲突 | 中 | 复用现有 `client_version` + `op_id` 机制 |
| 月度报告聚合查询慢 | 中 | 预生成聚合表 + 异步 Celery 任务 |
| Widget 后台刷新受限 | 低 | 设计为低实时性摘要，主入口仍是 App |
| Pro 权益门控设计不足导致后续重构 | 高 | Phase 2.6 预留表、字段、工具函数 |

---

## 6. 依赖与前置

- [ ] Phase 2 PRD / PCR 评审通过（本路线图为执行层拆分）。
- [ ] 设计师确认暗色模式色板与 Widget 设计稿。
- [ ] 确定 Freemium 权益数值（免费品类上限、家庭成员上限等）。

---

## 7. 成功指标

| 指标 | 目标 |
|---|---|
| Phase 2 功能全部通过 API 回归测试 | 新增测试覆盖率 ≥80% |
| 治理门禁 | `npm run check:all` PASS |
| Staging 灰度 | WAVE 10/50/100 `decision=CONTINUE` |
| 用户可用性 | 自定义品类、家庭共享、报告可在移动端完整闭环使用 |

---

## 8. 附录：参考文档

- `SuperAssistant_PRD_v1.1.md` — 产品需求与路线图。
- `docs/roadmap/PROJECT_PHASE_MEMO.md` — Phase 2 规划备忘录。
- `docs/roadmap/IMPLEMENTATION_STATUS.md` — 已实现 part 1–45 的详细记录。
- `docs/roadmap/MVP_10_WEEK_EXECUTION.md` — MVP 10 周执行路线图。
