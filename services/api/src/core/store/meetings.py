from __future__ import annotations

import uuid

from sqlalchemy import func, select

from core.ai_pipeline import ai_pipeline
from core.db import SessionLocal
from core.errors import ApiException
from core.models import MeetingActionItemModel, MeetingModel
from core.schemas import Meeting, MeetingActionItem, MeetingCreateRequest, utc_now
from core.store.base import StoreBase


class MeetingStoreMixin(StoreBase):
    def _meeting_action_item(self, row: MeetingActionItemModel) -> MeetingActionItem:
        return MeetingActionItem(
            action_item_id=row.id,
            meeting_id=row.meeting_id,
            text=row.text,
            assignee=row.assignee,
            done=row.done,
        )

    def _meeting(self, row: MeetingModel, items: list[MeetingActionItemModel]) -> Meeting:
        return Meeting(
            meeting_id=row.id,
            title=row.title,
            transcript=row.transcript,
            summary=row.summary,
            started_at=row.started_at,
            ended_at=row.ended_at,
            action_items=[self._meeting_action_item(i) for i in items],
            created_at=row.created_at,
        )

    def _count_meetings(self, user_id: str) -> int:
        with SessionLocal() as db:
            return db.scalar(select(func.count()).select_from(MeetingModel).where(MeetingModel.user_id == user_id)) or 0

    def create_meeting(self, user_id: str, request: MeetingCreateRequest) -> Meeting:
        if not self.can_use_feature(user_id, "meetings", self._count_meetings(user_id)):
            self.record_event(user_id, "subscription_gate_hit", {"feature": "meetings"})
            raise ApiException(402, "BIZ_402_UPGRADE_REQUIRED", "free tier meeting limit reached")
        summary, items = ai_pipeline.summarize_meeting(request.title, request.transcript)
        with SessionLocal() as db:
            meeting = MeetingModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                title=request.title,
                transcript=request.transcript,
                summary=summary,
                started_at=request.started_at or utc_now(),
                ended_at=request.ended_at,
            )
            db.add(meeting)
            db.flush()
            item_rows: list[MeetingActionItemModel] = []
            for item in items:
                row = MeetingActionItemModel(
                    id=str(uuid.uuid4()),
                    meeting_id=meeting.id,
                    user_id=user_id,
                    text=item["text"],
                    assignee=item.get("assignee"),
                )
                db.add(row)
                item_rows.append(row)
            db.commit()
            db.refresh(meeting)
            return self._meeting(meeting, item_rows)

    def list_meetings(self, user_id: str) -> list[Meeting]:
        with SessionLocal() as db:
            rows = db.scalars(
                select(MeetingModel)
                .where(MeetingModel.user_id == user_id)
                .order_by(MeetingModel.started_at.desc())
            ).all()
            result: list[Meeting] = []
            for meeting in rows:
                items = db.scalars(
                    select(MeetingActionItemModel)
                    .where(MeetingActionItemModel.meeting_id == meeting.id)
                    .order_by(MeetingActionItemModel.created_at.asc())
                ).all()
                result.append(self._meeting(meeting, list(items)))
            return result

    def get_meeting(self, user_id: str, meeting_id: str) -> Meeting:
        with SessionLocal() as db:
            meeting = db.scalar(
                select(MeetingModel).where(MeetingModel.id == meeting_id, MeetingModel.user_id == user_id)
            )
            if meeting is None:
                raise KeyError("meeting not found")
            items = db.scalars(
                select(MeetingActionItemModel)
                .where(MeetingActionItemModel.meeting_id == meeting.id)
                .order_by(MeetingActionItemModel.created_at.asc())
            ).all()
            return self._meeting(meeting, list(items))

    def update_action_item(self, user_id: str, action_item_id: str, done: bool) -> MeetingActionItem:
        with SessionLocal() as db:
            row = db.scalar(
                select(MeetingActionItemModel).where(
                    MeetingActionItemModel.id == action_item_id,
                    MeetingActionItemModel.user_id == user_id,
                )
            )
            if row is None:
                raise KeyError("action item not found")
            row.done = done
            db.commit()
            db.refresh(row)
            return self._meeting_action_item(row)
