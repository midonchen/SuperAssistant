from __future__ import annotations

import uuid

from sqlalchemy import func, select

from core.db import SessionLocal
from core.errors import ApiException
from core.models import JobApplicationModel
from core.schemas import JobApplication, JobApplicationCreateRequest, JobApplicationUpdateRequest, utc_now
from core.store.base import StoreBase


class JobApplicationStoreMixin(StoreBase):
    def _application(self, row: JobApplicationModel) -> JobApplication:
        return JobApplication(
            application_id=row.id,
            company=row.company,
            position=row.position,
            status=row.status,
            applied_at=row.applied_at,
            notes=row.notes,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _count_applications(self, user_id: str) -> int:
        with SessionLocal() as db:
            return (
                db.scalar(
                    select(func.count())
                    .select_from(JobApplicationModel)
                    .where(JobApplicationModel.user_id == user_id)
                )
                or 0
            )

    def create_application(self, user_id: str, request: JobApplicationCreateRequest) -> JobApplication:
        if not self.can_use_feature(user_id, "job_applications", self._count_applications(user_id)):
            self.record_event(user_id, "subscription_gate_hit", {"feature": "job_applications"})
            raise ApiException(402, "BIZ_402_UPGRADE_REQUIRED", "free tier job application limit reached")
        with SessionLocal() as db:
            row = JobApplicationModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                company=request.company,
                position=request.position,
                applied_at=request.applied_at,
                notes=request.notes,
                status="APPLIED",
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._application(row)

    def list_applications(self, user_id: str) -> list[JobApplication]:
        with SessionLocal() as db:
            rows = db.scalars(
                select(JobApplicationModel)
                .where(JobApplicationModel.user_id == user_id)
                .order_by(JobApplicationModel.created_at.desc())
            ).all()
            return [self._application(r) for r in rows]

    def update_application(
        self, user_id: str, application_id: str, request: JobApplicationUpdateRequest
    ) -> JobApplication:
        with SessionLocal() as db:
            row = db.scalar(
                select(JobApplicationModel).where(
                    JobApplicationModel.id == application_id,
                    JobApplicationModel.user_id == user_id,
                )
            )
            if row is None:
                raise KeyError("job application not found")
            if request.company is not None:
                row.company = request.company
            if request.position is not None:
                row.position = request.position
            if request.status is not None:
                if request.status not in {"APPLIED", "INTERVIEW", "OFFER", "REJECTED"}:
                    raise ApiException(400, "VAL_400_INVALID_PARAM", "invalid application status")
                row.status = request.status
            if request.applied_at is not None:
                row.applied_at = request.applied_at
            if request.notes is not None:
                row.notes = request.notes
            row.updated_at = utc_now()
            db.commit()
            db.refresh(row)
            return self._application(row)

    def delete_application(self, user_id: str, application_id: str) -> None:
        with SessionLocal() as db:
            row = db.scalar(
                select(JobApplicationModel).where(
                    JobApplicationModel.id == application_id,
                    JobApplicationModel.user_id == user_id,
                )
            )
            if row is None:
                raise KeyError("job application not found")
            db.delete(row)
            db.commit()
