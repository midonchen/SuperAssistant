from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from core.db import SessionLocal
from core.errors import ApiException
from core.models import TaskModel
from core.schemas import PrioritizedTask, Task, TaskCreateRequest, TaskUpdateRequest, utc_now
from core.store.base import StoreBase


def _naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class TaskStoreMixin(StoreBase):
    def list_tasks(self, user_id: str, status: str | None = None) -> list[Task]:
        with SessionLocal() as db:
            stmt = select(TaskModel).where(TaskModel.user_id == user_id)
            if status:
                stmt = stmt.where(TaskModel.status == status)
            stmt = stmt.order_by(TaskModel.created_at.desc())
            rows = db.scalars(stmt).all()
            return [self._task(row) for row in rows]

    def get_task(self, user_id: str, task_id: str) -> Task:
        with SessionLocal() as db:
            row = db.scalar(select(TaskModel).where(TaskModel.id == task_id, TaskModel.user_id == user_id))
            if row is None:
                raise KeyError("task not found")
            return self._task(row)

    def create_task(self, user_id: str, request: TaskCreateRequest) -> Task:
        with SessionLocal() as db:
            row = TaskModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                title=request.title,
                description=request.description,
                due_at=request.due_at,
                priority=request.priority,
                status="TODO",
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._task(row)

    def update_task(self, user_id: str, task_id: str, request: TaskUpdateRequest) -> Task:
        with SessionLocal() as db:
            row = db.scalar(select(TaskModel).where(TaskModel.id == task_id, TaskModel.user_id == user_id))
            if row is None:
                raise KeyError("task not found")
            if request.title is not None:
                row.title = request.title
            if request.description is not None:
                row.description = request.description
            if request.due_at is not None:
                row.due_at = request.due_at
            if request.priority is not None:
                row.priority = request.priority
            if request.status is not None:
                if request.status not in {"TODO", "IN_PROGRESS", "DONE"}:
                    raise ApiException(400, "VAL_400_INVALID_PARAM", "invalid task status")
                row.status = request.status
            row.updated_at = utc_now()
            db.commit()
            db.refresh(row)
            return self._task(row)

    def delete_task(self, user_id: str, task_id: str) -> None:
        with SessionLocal() as db:
            row = db.scalar(select(TaskModel).where(TaskModel.id == task_id, TaskModel.user_id == user_id))
            if row is None:
                raise KeyError("task not found")
            db.delete(row)
            db.commit()

    def prioritize_tasks(self, user_id: str) -> list[PrioritizedTask]:
        """Rank TODO tasks by urgency: deadline proximity + manual priority. Heuristic baseline for AI ranking."""
        tasks = self.list_tasks(user_id, status="TODO")
        now = utc_now()
        scored: list[PrioritizedTask] = []
        for task in tasks:
            score = (5 - task.priority) * 10.0
            reason = "无截止日期，按手动优先级"
            if task.due_at is not None:
                due = _naive_utc(task.due_at)
                days = (due - now).total_seconds() / 86400.0
                if days < 0:
                    score += 50.0
                    reason = "已逾期"
                elif days < 1:
                    score += 30.0
                    reason = "今天到期"
                elif days < 3:
                    score += 20.0
                    reason = "3 天内到期"
                elif days < 7:
                    score += 10.0
                    reason = "7 天内到期"
                else:
                    reason = f"距截止 {int(days)} 天"
            scored.append(
                PrioritizedTask(
                    task_id=task.task_id,
                    title=task.title,
                    priority=task.priority,
                    due_at=task.due_at,
                    status=task.status,
                    score=round(score, 1),
                    reason=reason,
                )
            )
        scored.sort(key=lambda t: t.score, reverse=True)
        return scored
