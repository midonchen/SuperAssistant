from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import select

from core.db import SessionLocal
from core.errors import ApiException
from core.models import ApprovalRequestModel, SecurityEventModel, SessionModel
from core.schemas import utc_now


ACTION_REVOKE_USER_SESSIONS = "REVOKE_USER_SESSIONS"
STATUS_PENDING = "PENDING"
STATUS_APPROVED = "APPROVED"
STATUS_REJECTED = "REJECTED"


@dataclass
class ApprovalStore:
    def _row_to_dict(self, row: ApprovalRequestModel) -> dict:
        return {
            "approval_id": row.id,
            "action_type": row.action_type,
            "status": row.status,
            "target_user_id": row.target_user_id,
            "requested_by": row.requested_by,
            "reviewed_by": row.reviewed_by,
            "request_payload": row.request_payload,
            "review_comment": row.review_comment,
            "execution_result": row.execution_result,
            "created_at": row.created_at.isoformat(),
            "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
        }

    def _add_security_event(self, user_id: str, event_type: str, details: dict) -> None:
        with SessionLocal() as db:
            db.add(
                SecurityEventModel(
                    user_id=user_id,
                    event_type=event_type,
                    details=details,
                    created_at=utc_now(),
                )
            )
            db.commit()

    def create_revoke_user_sessions_request(self, requested_by: str, target_user_id: str, reason: str | None = None) -> dict:
        approval_id = str(uuid4())
        payload = {"target_user_id": target_user_id, "reason": reason or ""}
        with SessionLocal() as db:
            row = ApprovalRequestModel(
                id=approval_id,
                action_type=ACTION_REVOKE_USER_SESSIONS,
                status=STATUS_PENDING,
                target_user_id=target_user_id,
                requested_by=requested_by,
                request_payload=payload,
                created_at=utc_now(),
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            result = self._row_to_dict(row)

        self._add_security_event(
            requested_by,
            "ADMIN_APPROVAL_REQUEST_CREATED",
            {"approval_id": approval_id, "action_type": ACTION_REVOKE_USER_SESSIONS, "target_user_id": target_user_id},
        )
        return result

    def list_requests(self, status: str | None = None, action_type: str | None = None) -> list[dict]:
        with SessionLocal() as db:
            stmt = select(ApprovalRequestModel).order_by(ApprovalRequestModel.created_at.desc())
            if status:
                stmt = stmt.where(ApprovalRequestModel.status == status)
            if action_type:
                stmt = stmt.where(ApprovalRequestModel.action_type == action_type)
            rows = db.scalars(stmt).all()
            return [self._row_to_dict(row) for row in rows]

    def review_request(self, approval_id: str, reviewer_id: str, decision: str, comment: str | None = None) -> dict | None:
        action = decision.upper()
        if action not in {"APPROVE", "REJECT"}:
            raise ApiException(400, "VAL_400_INVALID_PARAM", "invalid approval decision")

        with SessionLocal() as db:
            row = db.scalar(select(ApprovalRequestModel).where(ApprovalRequestModel.id == approval_id))
            if row is None:
                return None
            if row.status != STATUS_PENDING:
                return self._row_to_dict(row)
            if action == "APPROVE" and row.requested_by == reviewer_id:
                raise ApiException(403, "AUTH_403_FORBIDDEN", "self-approval is not allowed")

            row.reviewed_by = reviewer_id
            row.reviewed_at = utc_now()
            row.review_comment = comment

            execution_result: dict | None = None
            if action == "APPROVE":
                if row.action_type == ACTION_REVOKE_USER_SESSIONS:
                    sessions = db.scalars(
                        select(SessionModel).where(
                            SessionModel.user_id == row.target_user_id,
                            SessionModel.revoked.is_(False),
                        )
                    ).all()
                    for session in sessions:
                        session.revoked = True
                    execution_result = {
                        "target_user_id": row.target_user_id,
                        "revoked_sessions": len(sessions),
                    }
                row.status = STATUS_APPROVED
                row.execution_result = execution_result or {}
            else:
                row.status = STATUS_REJECTED
                row.execution_result = {"rejected": True}

            db.commit()
            db.refresh(row)
            result = self._row_to_dict(row)

        self._add_security_event(
            reviewer_id,
            "ADMIN_APPROVAL_REVIEWED",
            {
                "approval_id": approval_id,
                "decision": action,
                "action_type": result["action_type"],
                "target_user_id": result["target_user_id"],
                "status": result["status"],
            },
        )
        return result


approval_store = ApprovalStore()
