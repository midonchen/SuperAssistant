# v2.0 工作与日程模块 · 规划备忘录

> 用途：在 v1.5（Phase 2 物资模块深化）闭环演示落地后，规划下一大版本 v2.0。
> 生成时间：2026-09-21。

## 1. 目标与范围（依据 PRD v1.1 §16）

v2.0 工作与日程模块，把产品从「家庭物资管理」扩展到「个人工作生产力」：

| 功能 | 说明 | 建议优先级 |
|------|------|-----------|
| 任务优先级 AI 排序 | 录入任务 → AI 按截止时间/重要性自动排序 | P0（本轮起步） |
| 日历整合 | 与日历互通，按天/周视图查看任务与会议 | P1 |
| 会议智能摘要 | 会议录音 → AI 生成摘要与待办 | P1 |
| 工作周报生成 | 聚合本周任务/会议 → 自动生成周报 | P1 |

商业化：v2.0 起进入「订阅制」（全模块 ¥38/月 或 ¥298/年），沿用 v1.5 的 subscription_tiers / can_use_feature 权益门控基建。

## 2. 本轮已起步（part 55）

- 任务域：`tasks` 表 + 迁移 `20260331_0012`（user_id/title/description/due_at/priority/status）
- `TaskStoreMixin`：list/create/update/delete + `prioritize_tasks`
- `/tasks` 路由：`GET /tasks`、`POST /tasks`、`PATCH /tasks/{id}`、`DELETE /tasks/{id}`、`POST /tasks/prioritize`
- 优先级排序：启发式打分（截止日期紧迫度 + 手动优先级），返回有序列表 + 排序理由
- 任务按 `user_id` 隔离（个人工作，不按家庭共享）

## 3. 下一步（后端）

- AI 排序：接入 `core.ai_pipeline`（DeepSeek），用 LLM 对任务重新排序并给理由，启发式为降级兜底（与 voice/OCR 解析同一套 provider/熔断/配额护栏）。
- 日历整合：`GET /calendar/events` 聚合任务 deadline + 会议；可选接入外部日历（iCal/CalDAV）—— 外部日历为后续 P1。
- 会议摘要：复用 STT（语音转写）+ 摘要 prompt，产出 `meetings` + `meeting_action_items`。
- 周报生成：聚合本周 `tasks`（已完成/逾期）+ `meetings`，产出 `weekly_reports`。
- 门控：将「任务/会议/周报」纳入 v1.5 的 subscription 权益（免费版任务数上限等）。
- 移动端：Flutter 任务列表/详情/排序页（iOS，需 Xcode，另排）。

## 4. 数据模型（新增）

```text
tasks              -> 已建（part 55）
meetings           -> 会议：id, user_id, title, transcript, summary, started_at, ended_at
meeting_action_items -> 会议待办：id, meeting_id, user_id, text, assignee, done
weekly_reports     -> 周报：id, user_id, week_start, content, generated_at
```

## 5. 风险

- AI 排序/摘要依赖 LLM（DeepSeek）可用性与配额 —— 沿用现有 circuit breaker + 配额护栏 + 启发式兜底。
- 任务/会议量增长后的查询性能 —— 按 user_id 建索引，后续再考虑分页/缓存。
- 日历整合的外部依赖（CalDAV/iCal）—— 先做内部聚合视图，外部日历后置。
