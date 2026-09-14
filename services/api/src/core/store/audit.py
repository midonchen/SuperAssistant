from __future__ import annotations

from sqlalchemy import func, select

from core.db import SessionLocal
from core.models import AuditTaskModel
from core.schemas import ParsedEntity, utc_now
from core.store.base import StoreBase


class AuditStoreMixin(StoreBase):
    def count_audit_tasks(self) -> tuple[int, int]:
        with SessionLocal() as db:
            total = int(db.scalar(select(func.count()).select_from(AuditTaskModel)) or 0)
            pending = int(
                db.scalar(select(func.count()).select_from(AuditTaskModel).where(AuditTaskModel.status == "PENDING")) or 0
            )
            return total, pending

    def add_audit_task(self, parse_session_id: str, entities: list[ParsedEntity]) -> None:
        with SessionLocal() as db:
            db.add(
                AuditTaskModel(
                    parse_session_id=parse_session_id,
                    status="PENDING",
                    entities=[entity.model_dump(mode="json") for entity in entities],
                    created_at=utc_now(),
                )
            )
            db.commit()

    def list_audit_tasks(self) -> list[dict]:
        with SessionLocal() as db:
            rows = db.scalars(select(AuditTaskModel).order_by(AuditTaskModel.created_at.desc())).all()
            return [
                {
                    "task_id": row.id,
                    "parse_session_id": row.parse_session_id,
                    "status": row.status,
                    "entities": row.entities,
                    "review_action": row.review_action,
                    "corrected_entities": row.corrected_entities,
                    "created_at": row.created_at.isoformat(),
                    "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
                }
                for row in rows
            ]

    def review_audit_task(self, task_id: str, action: str, corrected_entities: list[dict] | None = None) -> bool:
        with SessionLocal() as db:
            row = db.scalar(select(AuditTaskModel).where(AuditTaskModel.id == task_id))
            if row is None:
                return False
            row.status = "DONE"
            row.review_action = action
            row.corrected_entities = corrected_entities or []
            row.reviewed_at = utc_now()
            db.commit()
            return True
