from __future__ import annotations

from uuid import UUID, uuid4

from core.errors import ApiException
from core.offline_queue import offline_replay_queue
from core.store.base import StoreBase


class OfflineStoreMixin(StoreBase):
    def enqueue_offline_replay_ops(self, household_id: str, user_id: UUID, offline_ops: list[dict]) -> dict:
        queued = 0
        for row in offline_ops:
            payload = {
                "job_id": row.get("op_id", str(uuid4())),
                "household_id": household_id,
                "user_id": str(user_id),
                "created_at": row.get("created_at"),
                "retry_count": int(row.get("retry_count", 0)),
                "payload": row.get("payload", {}),
            }
            offline_replay_queue.enqueue(payload)
            queued += 1
        return {"queued_count": queued, "queue_depth": offline_replay_queue.size()}

    def process_offline_replay_queue(self, max_jobs: int = 100) -> dict:
        jobs = offline_replay_queue.pop_many(max_jobs=max_jobs)
        processed = 0
        applied_ops = 0
        conflicts = 0
        failed = 0
        retried = 0

        for job in jobs:
            try:
                household_id = job["household_id"]
                user_id = UUID(job["user_id"])
                payload = job.get("payload", {})
                operations = payload.get("operations", [])
                result = self.apply_batch_operations(household_id, user_id, operations, from_replay=True)
                processed += 1
                applied_ops += len(result["activity_ids"])
            except ApiException as exc:
                if exc.detail.get("code") == "BIZ_409_CONFLICT":
                    conflicts += 1
                    processed += 1
                    continue
                failed += 1
            except Exception:
                retry_count = int(job.get("retry_count", 0))
                if retry_count < 5:
                    job["retry_count"] = retry_count + 1
                    offline_replay_queue.enqueue(job)
                    retried += 1
                else:
                    failed += 1

        return {
            "processed_jobs": processed,
            "applied_ops": applied_ops,
            "conflicts": conflicts,
            "failed": failed,
            "retried": retried,
            "queue_depth": offline_replay_queue.size(),
        }
