from __future__ import annotations

import json
import logging
import os

import httpx

logger = logging.getLogger(__name__)


class GenerativeAIMixin:
    def rank_tasks(self, tasks: list[dict]) -> tuple[str, list[dict]]:
        """AI re-rank of tasks. Returns (method, tasks) where method is "ai"|"heuristic". Falls back to input order."""
        if not tasks:
            return "heuristic", tasks
        try:
            ranked = self._ai_rank(tasks)
            if not ranked:
                return "heuristic", tasks
            by_id = {t["task_id"]: t for t in tasks}
            reordered: list[dict] = []
            for index, (task_id, reason) in enumerate(ranked):
                source = by_id.get(task_id)
                if source is None:
                    continue
                entry = dict(source)
                entry["reason"] = reason
                entry["score"] = round(100.0 - index * 5.0, 1)
                reordered.append(entry)
            seen = {t["task_id"] for t in reordered}
            for task in tasks:
                if task["task_id"] not in seen:
                    reordered.append(task)
            if len(reordered) == len(tasks):
                return "ai", reordered
        except Exception as exc:
            logger.warning("task AI ranking failed, fallback to heuristic: %s", exc)
        return "heuristic", tasks

    def _ai_rank(self, tasks: list[dict]) -> list[tuple[str, str]]:
        api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        if not api_key:
            return []
        model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip() or "deepseek-chat"
        endpoint = os.getenv("DEEPSEEK_CHAT_ENDPOINT", "https://api.deepseek.com/v1/chat/completions").strip()
        lines = "\n".join(
            f"- id:{t['task_id']} 标题:{t['title']} 截止:{t.get('due_at') or '无'} 优先级:{t.get('priority', 3)}（1最高4最低）"
            for t in tasks
        )
        prompt = (
            "你是任务优先级助手。请按截止时间和重要性将以下任务从高到低排序，"
            '只返回 JSON：{"ranking":[{"task_id":"...","reason":"一句话理由"}]}。\n'
            + lines
        )
        with httpx.Client(timeout=20.0) as client:
            response = client.post(
                endpoint,
                headers={"Authorization": f"Bearer {api_key}", "content-type": "application/json"},
                json={"model": model, "temperature": 0, "messages": [{"role": "user", "content": prompt}]},
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            data = json.loads(content)
            ranking = data.get("ranking", [])
            result: list[tuple[str, str]] = []
            for row in ranking:
                if isinstance(row, dict) and row.get("task_id"):
                    result.append((str(row["task_id"]), str(row.get("reason", "AI 排序"))))
            return result

    def summarize_meeting(self, title: str, transcript: str) -> tuple[str, list[dict]]:
        """Generate a meeting summary + action items. Returns (summary, [{text, assignee}]). Falls back to heuristic."""
        try:
            result = self._ai_meeting_summary(title, transcript)
            if result:
                return result
        except Exception as exc:
            logger.warning("meeting summarization failed, fallback to heuristic: %s", exc)
        return self._heuristic_meeting_summary(transcript)

    def _ai_meeting_summary(self, title: str, transcript: str) -> tuple[str, list[dict]] | None:
        api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        if not api_key:
            return None
        model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip() or "deepseek-chat"
        endpoint = os.getenv("DEEPSEEK_CHAT_ENDPOINT", "https://api.deepseek.com/v1/chat/completions").strip()
        prompt = (
            "你是会议纪要助手。请根据以下会议标题和转写内容，生成一份简洁中文摘要，并提取待办事项。"
            '只返回 JSON：{"summary":"...","action_items":[{"text":"...","assignee":"..."}]}（assignee 未知则省略）。\n'
            f"会议标题：{title}\n转写内容：\n{transcript[:6000]}"
        )
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                endpoint,
                headers={"Authorization": f"Bearer {api_key}", "content-type": "application/json"},
                json={"model": model, "temperature": 0, "messages": [{"role": "user", "content": prompt}]},
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            data = json.loads(content)
            summary = str(data.get("summary", "")).strip()
            items: list[dict] = []
            for row in data.get("action_items", []) or []:
                if isinstance(row, dict) and row.get("text"):
                    items.append({"text": str(row["text"]).strip(), "assignee": row.get("assignee") or None})
            if not summary:
                return None
            return summary, items

    def _heuristic_meeting_summary(self, transcript: str) -> tuple[str, list[dict]]:
        summary = transcript[:200].strip() + ("…" if len(transcript) > 200 else "")
        items: list[dict] = []
        for line in transcript.splitlines():
            stripped = line.strip()
            for prefix in ("TODO", "待办", "行动项", "Action", "- [ ]"):
                if stripped.startswith(prefix):
                    text = stripped[len(prefix):].strip(" :-[]：，,")
                    if text:
                        items.append({"text": text, "assignee": None})
                    break
        return summary, items

    def generate_weekly_report(self, week_start: str, tasks: list[dict], meetings: list[dict]) -> str:
        """Aggregate weekly tasks + meetings into a report. Falls back to heuristic."""
        try:
            content = self._ai_weekly_report(week_start, tasks, meetings)
            if content:
                return content
        except Exception as exc:
            logger.warning("weekly report generation failed, fallback to heuristic: %s", exc)
        return self._heuristic_weekly_report(week_start, tasks, meetings)

    def _ai_weekly_report(self, week_start: str, tasks: list[dict], meetings: list[dict]) -> str | None:
        api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        if not api_key:
            return None
        model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip() or "deepseek-chat"
        endpoint = os.getenv("DEEPSEEK_CHAT_ENDPOINT", "https://api.deepseek.com/v1/chat/completions").strip()
        task_lines = "\n".join(f"- {t['title']}（{t['status']}，截止 {t.get('due_at') or '无'}）" for t in tasks) or "- 无"
        meeting_lines = "\n".join(f"- {m['title']}：{m.get('summary') or '无摘要'}" for m in meetings) or "- 无"
        prompt = (
            "你是周报助手。根据以下本周任务和会议，生成一份简洁中文周报（markdown，含：本周完成、逾期未完成、进行中、会议纪要、下周计划）。\n"
            f"本周：{week_start}\n任务：\n{task_lines}\n会议：\n{meeting_lines}"
        )
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                endpoint,
                headers={"Authorization": f"Bearer {api_key}", "content-type": "application/json"},
                json={"model": model, "temperature": 0, "messages": [{"role": "user", "content": prompt}]},
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"].strip()
            return content or None

    def _heuristic_weekly_report(self, week_start: str, tasks: list[dict], meetings: list[dict]) -> str:
        done = [t for t in tasks if t["status"] == "已完成"]
        overdue = [t for t in tasks if t["status"] == "已逾期"]
        pending = [t for t in tasks if t["status"] == "进行中"]
        lines = [f"# 周报 {week_start}", "", "## 本周完成"]
        lines += [f"- {t['title']}" for t in done] or ["- 无"]
        lines += ["", "## 逾期未完成"]
        lines += [f"- {t['title']}" for t in overdue] or ["- 无"]
        lines += ["", "## 进行中"]
        lines += [f"- {t['title']}" for t in pending] or ["- 无"]
        lines += ["", "## 会议纪要"]
        lines += [f"- {m['title']}：{m.get('summary') or '无摘要'}" for m in meetings] or ["- 无"]
        return "\n".join(lines)

    def suggest_gift(self, contact_name: str, relationship: str | None, preferences: dict | None, occasion_name: str, budget: float | None) -> str:
        """Generate a gift suggestion. Falls back to heuristic."""
        try:
            content = self._ai_gift_suggestion(contact_name, relationship, preferences, occasion_name, budget)
            if content:
                return content
        except Exception as exc:
            logger.warning("gift suggestion failed, fallback to heuristic: %s", exc)
        return self._heuristic_gift_suggestion(contact_name, relationship, occasion_name)

    def _ai_gift_suggestion(self, contact_name: str, relationship: str | None, preferences: dict | None, occasion_name: str, budget: float | None) -> str | None:
        api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        if not api_key:
            return None
        model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip() or "deepseek-chat"
        endpoint = os.getenv("DEEPSEEK_CHAT_ENDPOINT", "https://api.deepseek.com/v1/chat/completions").strip()
        prefs = json.dumps(preferences, ensure_ascii=False) if preferences else "未知"
        budget_str = f"{budget} 元" if budget else "不限"
        prompt = (
            "你是礼物建议助手。根据收礼人信息和场合，给出一个具体、贴心的礼物建议（含简短理由），50字以内。\n"
            f"收礼人：{contact_name}（关系：{relationship or '未知'}）\n"
            f"喜好：{prefs}\n场合：{occasion_name or '日常'}\n预算：{budget_str}\n"
            "只返回礼物建议文本。"
        )
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                endpoint,
                headers={"Authorization": f"Bearer {api_key}", "content-type": "application/json"},
                json={"model": model, "temperature": 0.6, "messages": [{"role": "user", "content": prompt}]},
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"].strip()
            return content or None

    def _heuristic_gift_suggestion(self, contact_name: str, relationship: str | None, occasion_name: str) -> str:
        if occasion_name and "生日" in occasion_name:
            return f"为{contact_name}准备一份生日礼物：结合ta的喜好挑选（书籍、手作或一顿用心的大餐）。"
        if occasion_name and ("纪念" in occasion_name or "周年" in occasion_name):
            return f"为{contact_name}准备一份纪念礼物：一件有纪念意义的定制小物，如照片相册或刻字饰品。"
        return f"为{contact_name}挑选一份心意礼物：结合ta的喜好，选一份实用或精致的礼物。"

    def career_advice(
        self, goals: list[dict], skills: list[dict], applications: list[dict], learning_items: list[dict]
    ) -> str:
        """Generate career growth advice. Falls back to heuristic."""
        try:
            content = self._ai_career_advice(goals, skills, applications, learning_items)
            if content:
                return content
        except Exception as exc:
            logger.warning("career advice failed, fallback to heuristic: %s", exc)
        return self._heuristic_career_advice(goals, skills, applications, learning_items)

    def _ai_career_advice(
        self, goals: list[dict], skills: list[dict], applications: list[dict], learning_items: list[dict]
    ) -> str | None:
        api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        if not api_key:
            return None
        model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip() or "deepseek-chat"
        endpoint = os.getenv("DEEPSEEK_CHAT_ENDPOINT", "https://api.deepseek.com/v1/chat/completions").strip()
        g = "; ".join([f"{x['title']}(进度{x['progress']}%, {x['status']})" for x in goals]) or "无"
        s = "; ".join([f"{x['name']}(L{x['level']}→L{x['target_level']})" for x in skills]) or "无"
        a = "; ".join([f"{x['company']}·{x['position']}({x['status']})" for x in applications]) or "无"
        l = "; ".join([f"{x['title']}({x['item_type']}, {x['status']})" for x in learning_items]) or "无"
        prompt = (
            "你是职业规划顾问。根据用户的职业目标、技能、求职进展和学习计划，给出三条具体可执行的成长建议，每条一句话，语气务实。\n"
            f"职业目标：{g}\n技能：{s}\n求职进展：{a}\n学习计划：{l}\n"
            "用 markdown 列表返回，每条以 '- ' 开头，200字以内。"
        )
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                endpoint,
                headers={"Authorization": f"Bearer {api_key}", "content-type": "application/json"},
                json={"model": model, "temperature": 0.6, "messages": [{"role": "user", "content": prompt}]},
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"].strip()
            return content or None

    def _heuristic_career_advice(
        self, goals: list[dict], skills: list[dict], applications: list[dict], learning_items: list[dict]
    ) -> str:
        lines = ["## 职业成长建议"]
        if goals:
            active = [x for x in goals if x.get("status") == "ACTIVE"]
            lines.append(f"- 聚焦当前 {len(active)} 个进行中的目标，把进度推进到 100%。")
        else:
            lines.append("- 先设定一个明确的职业目标（如晋升/转岗/技能深耕），再拆解季度里程碑。")
        gaps = [x for x in skills if x.get("target_level", 0) > x.get("level", 0)]
        if gaps:
            names = "、".join(x["name"] for x in gaps[:3])
            lines.append(f"- 优先补齐技能缺口：{names}，制定学习计划提升等级。")
        interviewing = [x for x in applications if x.get("status") == "INTERVIEW"]
        if interviewing:
            lines.append(f"- 你有 {len(interviewing)} 个面试进行中，及时复盘每次面试并补充针对性准备。")
        pending = [x for x in learning_items if x.get("status") != "DONE"]
        if pending:
            lines.append(f"- 推进 {len(pending)} 个未完成的学习项，保持输入节奏。")
        if not (goals or skills or applications or learning_items):
            lines.append("- 先完善职业档案：设定目标、盘点技能、记录投递、规划学习。")
        return "\n".join(lines)

    def suggest_meal(self, items: list[dict]) -> str:
        """Suggest a meal from household inventory. Falls back to heuristic."""
        try:
            content = self._ai_meal_suggestion(items)
            if content:
                return content
        except Exception as exc:
            logger.warning("meal suggestion failed, fallback to heuristic: %s", exc)
        return self._heuristic_meal_suggestion(items)

    def _ai_meal_suggestion(self, items: list[dict]) -> str | None:
        api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        if not api_key:
            return None
        model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip() or "deepseek-chat"
        endpoint = os.getenv("DEEPSEEK_CHAT_ENDPOINT", "https://api.deepseek.com/v1/chat/completions").strip()
        inventory = "; ".join([f"{x['item_name']}×{x['current_stock']}{x.get('unit', '')}" for x in items]) or "空"
        prompt = (
            "你是家常菜厨师。根据家里现有食材，推荐一道今晚能做的菜，并列出用到的食材和缺少的配料。\n"
            f"现有食材：{inventory}\n"
            "返回格式（markdown）：\n## 今晚推荐\n- 菜名：...\n- 用到：...\n- 缺料：...\n100字以内，只返回这段。"
        )
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                endpoint,
                headers={"Authorization": f"Bearer {api_key}", "content-type": "application/json"},
                json={"model": model, "temperature": 0.6, "messages": [{"role": "user", "content": prompt}]},
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"].strip()
            return content or None

    def _heuristic_meal_suggestion(self, items: list[dict]) -> str:
        names = [x.get("item_name", "") for x in items]
        has = set(names)
        dish = "一锅乱炖（用现有食材）"
        if "鸡蛋" in has:
            dish = "西红柿炒鸡蛋" if "西红柿" in has else "鸡蛋炒饭"
        elif "土豆" in has:
            dish = "酸辣土豆丝"
        elif any(k in has for k in ("猪肉", "牛肉", "鸡肉")):
            dish = "家常小炒"
        used = "、".join(names[:4]) or "现有食材"
        return f"## 今晚推荐\n- 菜名：{dish}\n- 用到：{used}\n- 缺料：按口味补充调味料"
