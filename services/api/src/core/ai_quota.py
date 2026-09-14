from __future__ import annotations

import os
from threading import Lock
import time
from typing import Any

from redis import Redis


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name, "").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


class ProviderQuotaGuard:
    def __init__(
        self,
        qps_per_minute: int | None = None,
        token_per_minute: int | None = None,
        token_per_day: int | None = None,
        redis_url: str | None = None,
    ):
        self._qps_per_minute = qps_per_minute if qps_per_minute is not None else _int_env("AI_PROVIDER_QPS_PER_MINUTE", 120)
        self._token_per_minute = token_per_minute if token_per_minute is not None else _int_env("AI_PROVIDER_TOKEN_PER_MINUTE", 50000)
        self._token_per_day = token_per_day if token_per_day is not None else _int_env("AI_PROVIDER_TOKEN_PER_DAY", 1000000)
        self._redis_url = redis_url or os.getenv(
            "AI_QUOTA_REDIS_URL",
            os.getenv("OFFLINE_QUEUE_REDIS_URL", os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/3")),
        )

        self._client: Redis | None = None
        self._redis_disabled = False
        self._local_lock = Lock()
        self._local_reqs: dict[str, int] = {}
        self._local_tokens_minute: dict[str, int] = {}
        self._local_tokens_day: dict[str, int] = {}

    def _redis(self) -> Redis | None:
        if self._redis_disabled:
            return None
        if self._client is not None:
            return self._client
        try:
            client = Redis.from_url(self._redis_url, decode_responses=True)
            client.ping()
            self._client = client
            return self._client
        except Exception:
            self._redis_disabled = True
            return None

    def _minute_bucket(self) -> int:
        return int(time.time() // 60)

    def _day_bucket(self) -> int:
        return int(time.time() // (60 * 60 * 24))

    def _cleanup_local(self, minute_bucket: int, day_bucket: int) -> None:
        req_prefix = ":req:"
        token_min_prefix = ":tokenm:"
        token_day_prefix = ":tokend:"
        self._local_reqs = {k: v for k, v in self._local_reqs.items() if k.endswith(f":{minute_bucket}") or req_prefix not in k}
        self._local_tokens_minute = {
            k: v for k, v in self._local_tokens_minute.items() if k.endswith(f":{minute_bucket}") or token_min_prefix not in k
        }
        self._local_tokens_day = {k: v for k, v in self._local_tokens_day.items() if k.endswith(f":{day_bucket}") or token_day_prefix not in k}

    def _redis_incr(self, client: Redis, key: str, expire_seconds: int, delta: int) -> int:
        value = int(client.incrby(key, delta))
        if value == delta:
            client.expire(key, expire_seconds)
        return value

    def allow(self, provider: str, estimated_tokens: int) -> tuple[bool, str]:
        minute_bucket = self._minute_bucket()
        day_bucket = self._day_bucket()
        estimated = max(1, int(estimated_tokens))

        client = self._redis()
        if client is not None:
            req_key = f"aiq:{provider}:req:{minute_bucket}"
            req_value = self._redis_incr(client, req_key, 120, 1)
            if self._qps_per_minute > 0 and req_value > self._qps_per_minute:
                return False, "QPS_LIMIT_EXCEEDED"

            min_token_key = f"aiq:{provider}:tokenm:{minute_bucket}"
            min_token_value = self._redis_incr(client, min_token_key, 120, estimated)
            if self._token_per_minute > 0 and min_token_value > self._token_per_minute:
                return False, "TOKEN_MINUTE_LIMIT_EXCEEDED"

            day_token_key = f"aiq:{provider}:tokend:{day_bucket}"
            day_token_value = self._redis_incr(client, day_token_key, 60 * 60 * 24 * 2, estimated)
            if self._token_per_day > 0 and day_token_value > self._token_per_day:
                return False, "TOKEN_DAILY_LIMIT_EXCEEDED"
            return True, "OK"

        with self._local_lock:
            self._cleanup_local(minute_bucket, day_bucket)
            req_key = f"{provider}:req:{minute_bucket}"
            req_value = self._local_reqs.get(req_key, 0) + 1
            self._local_reqs[req_key] = req_value
            if self._qps_per_minute > 0 and req_value > self._qps_per_minute:
                return False, "QPS_LIMIT_EXCEEDED"

            min_token_key = f"{provider}:tokenm:{minute_bucket}"
            min_token_value = self._local_tokens_minute.get(min_token_key, 0) + estimated
            self._local_tokens_minute[min_token_key] = min_token_value
            if self._token_per_minute > 0 and min_token_value > self._token_per_minute:
                return False, "TOKEN_MINUTE_LIMIT_EXCEEDED"

            day_token_key = f"{provider}:tokend:{day_bucket}"
            day_token_value = self._local_tokens_day.get(day_token_key, 0) + estimated
            self._local_tokens_day[day_token_key] = day_token_value
            if self._token_per_day > 0 and day_token_value > self._token_per_day:
                return False, "TOKEN_DAILY_LIMIT_EXCEEDED"

        return True, "OK"

    def snapshot(self) -> dict[str, Any]:
        minute_bucket = self._minute_bucket()
        day_bucket = self._day_bucket()
        providers = ("stt", "parser")
        usage: dict[str, dict[str, int]] = {}

        client = self._redis()
        if client is not None:
            for provider in providers:
                req = int(client.get(f"aiq:{provider}:req:{minute_bucket}") or 0)
                token_m = int(client.get(f"aiq:{provider}:tokenm:{minute_bucket}") or 0)
                token_d = int(client.get(f"aiq:{provider}:tokend:{day_bucket}") or 0)
                usage[provider] = {"requests_minute": req, "tokens_minute": token_m, "tokens_day": token_d}
            backend = "redis"
        else:
            with self._local_lock:
                self._cleanup_local(minute_bucket, day_bucket)
                for provider in providers:
                    usage[provider] = {
                        "requests_minute": int(self._local_reqs.get(f"{provider}:req:{minute_bucket}", 0)),
                        "tokens_minute": int(self._local_tokens_minute.get(f"{provider}:tokenm:{minute_bucket}", 0)),
                        "tokens_day": int(self._local_tokens_day.get(f"{provider}:tokend:{day_bucket}", 0)),
                    }
            backend = "local"

        return {
            "backend": backend,
            "limits": {
                "qps_per_minute": self._qps_per_minute,
                "token_per_minute": self._token_per_minute,
                "token_per_day": self._token_per_day,
            },
            "usage": usage,
        }


ai_quota_guard = ProviderQuotaGuard()
