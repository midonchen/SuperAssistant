# v3.0 社交与关系模块 · 规划备忘录（草案）

> 用途：v1.5（物资深化）与 v2.0（工作日程）闭环后，规划下一大版本 v3.0。
> 依据：PRD v1.1 §16 路线图（v3.0 = 社交与关系模块）；产品方向调整为「生活场景优先、工作场景后置、暂不做原生 iOS（先用 HTML）」。

## 1. 目标与范围（依据 PRD §16）

v3.0 把产品从「物资 + 工作」扩展到「人与关系」，继续主打生活场景：

| 功能 | 说明 | 建议优先级 |
|------|------|-----------|
| 重要人物管理 | 联系人档案：姓名、关系、生日/纪念日、喜好备注 | P0 |
| 纪念日/生日提醒 | 提前 N 天提醒（Push/日历），重复周期（每年/农历可选） | P0 |
| 联系频率管理 | 记录互动（电话/见面/微信），久未联系自动提醒「该问候了」 | P1 |
| 礼物建议 | 结合联系人喜好 + 场合 + 预算，AI 生成礼物建议 | P1 |
| 家庭事务协同 | 复用 households，多人可见的家庭待办（换水、缴费、维修） | P1 |

## 2. 与现有基建的复用

- **订阅门控**：沿用 subscription_tiers / can_use_feature（联系人上限、礼物建议次数）。
- **AI 管线**：礼物建议复用 ai_pipeline（DeepSeek），启发式兜底。
- **日历**：纪念日/生日接入 /calendar/events（source=occasion），自动进 iCal 订阅。
- **提醒**：复用 Celery beat 每日扫描 + Push 记录（真实推送仍待接 APNs）。
- **家庭事务**：优先复用 tasks 但加 household 维度，或独立 family_affairs 表。

## 3. 数据模型（新增草案）

```text
contacts            -> 联系人：id, user_id, name, relationship, birthday, preferences(JSON), notes
occasions           -> 纪念日：id, contact_id, user_id, name, date, is_lunar, remind_days_before
contact_interactions-> 互动记录：id, contact_id, user_id, channel, interacted_at, note
gift_suggestions    -> 礼物建议：id, contact_id, occasion_id, user_id, content, budget, generated_at
family_affairs      -> 家庭事务：id, household_id, user_id, title, due_at, assignee, status, created_at
```

## 4. 建议里程碑（后端 + HTML 移动端 + Admin，暂不做原生 iOS）

| 阶段 | 交付物 |
|------|--------|
| 3.1 | contacts + occasions：CRUD、生日/纪念日计算、日历接入 + 提醒任务 |
| 3.2 | contact_interactions：记录互动、久未联系提醒（beat 每日扫描） |
| 3.3 | gift_suggestions：AI 礼物建议（DeepSeek + 启发式） |
| 3.4 | family_affairs：家庭事务 CRUD + 权限（复用 household 角色） |
| 3.5 | HTML 移动端「人脉」tab + Admin 数据页 + demo 脚本覆盖 |

## 5. 风险

- 农历/生日历法：先做公历，农历后置（依赖库可选）。
- 真实 Push 提醒：沿用现有「记录 delivery 模拟触发」，真实 APNs 后续接。
- 隐私：联系人/互动属敏感数据，需比库存更严格的访问隔离（user_id 隔离已有基础）。

## 6. 待评审 → 已确认

> 2026-09-21 用户确认：**先做关系（v3.0）**。开工顺序 3.1 → 3.5。

- ✅ 3.1 联系人 + 纪念日：先做（P0，接入日历/提醒）。
- ✅ 联系频率（3.2）与礼物建议（3.3）：本版本包含。
- ✅ 家庭事务（3.4）：并入 v3.0（复用 household 角色）。
- 会议语音转写：已确认暂缓，不阻塞。
