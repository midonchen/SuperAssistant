from __future__ import annotations

import json
import os
from collections import deque
from dataclasses import dataclass, field
from threading import Lock
from typing import Any
from uuid import uuid4

from redis import Redis


@dataclass
class OfflineReplayQueue:
    redis_url: str = field(default_factory=lambda: os.getenv("OFFLINE_QUEUE_REDIS_URL", os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/2")))
    queue_key: str = "offline_ops_queue"
    processed_prefix: str = "offline_processed"
    processed_ttl_sec: int = 7 * 24 * 3600

    _client: Redis | None = None
    _redis_disabled: bool = False
    _fallback_queue: deque[dict[str, Any]] = field(default_factory=deque)
    _fallback_processed: set[str] = field(default_factory=set)
    _lock: Lock = field(default_factory=Lock)

    def _redis(self) -> Redis | None:
        if self._redis_disabled:
            return None
        if self._client is not None:
            return self._client
        try:
            client = Redis.from_url(self.redis_url, decode_responses=True)
            client.ping()
            self._client = client
            return self._client
        except Exception:
            self._redis_disabled = True
            return None

    def enqueue(self, payload: dict[str, Any]) -> str:
        payload = dict(payload)
        job_id = payload.get("job_id", str(uuid4()))
        payload["job_id"] = job_id

        client = self._redis()
        if client is not None:
            client.rpush(self.queue_key, json.dumps(payload, ensure_ascii=False))
            return job_id

        with self._lock:
            self._fallback_queue.append(payload)
        return job_id

    def pop_many(self, max_jobs: int = 100) -> list[dict[str, Any]]:
        jobs: list[dict[str, Any]] = []
        client = self._redis()
        if client is not None:
            for _ in range(max_jobs):
                row = client.lpop(self.queue_key)
                if row is None:
                    break
                jobs.append(json.loads(row))
            return jobs

        with self._lock:
            while self._fallback_queue and len(jobs) < max_jobs:
                jobs.append(self._fallback_queue.popleft())
        return jobs

    def mark_processed(self, op_id: str) -> None:
        client = self._redis()
        key = f"{self.processed_prefix}:{op_id}"
        if client is not None:
            client.setex(key, self.processed_ttl_sec, "1")
            return

        with self._lock:
            self._fallback_processed.add(op_id)

    def is_processed(self, op_id: str) -> bool:
        client = self._redis()
        key = f"{self.processed_prefix}:{op_id}"
        if client is not None:
            return bool(client.exists(key))

        with self._lock:
            return op_id in self._fallback_processed

    def size(self) -> int:
        client = self._redis()
        if client is not None:
            return int(client.llen(self.queue_key))

        with self._lock:
            return len(self._fallback_queue)

    def clear(self) -> None:
        client = self._redis()
        if client is not None:
            client.delete(self.queue_key)
            keys = list(client.scan_iter(match=f"{self.processed_prefix}:*"))
            if keys:
                client.delete(*keys)
            return

        with self._lock:
            self._fallback_queue.clear()
            self._fallback_processed.clear()


offline_replay_queue = OfflineReplayQueue()
