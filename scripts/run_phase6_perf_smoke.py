#!/usr/bin/env python3
from __future__ import annotations

import os
import pathlib
import sys
import time

from fastapi.testclient import TestClient

ROOT = pathlib.Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
API_SRC = API_ROOT / "src"
if str(API_SRC) not in sys.path:
    sys.path.insert(0, str(API_SRC))
PERF_DB = API_ROOT / "phase6_perf.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{PERF_DB}")

from core.db import engine
from core.models import Base
from core.offline_queue import offline_replay_queue
from core.store import store
from main import app


VOICE_P95_THRESHOLD_MS = 1200.0
OCR_P95_THRESHOLD_MS = 2800.0
REPLAY_100_THRESHOLD_MS = 30000.0
ITERATIONS = 30


def request_headers(token: str | None = None, *, idempotent: bool = False) -> dict[str, str]:
    headers = {
        "X-Request-Id": f"perf-{int(time.time() * 1000)}",
        "X-App-Version": "1.1.0",
        "X-Platform": "ios",
    }
    if idempotent:
        headers["Idempotency-Key"] = f"perf-op-{int(time.time() * 1000)}"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def p95_ms(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, int(round(0.95 * (len(ordered) - 1))))
    return ordered[index]


def benchmark_parse(client: TestClient, token: str, path: str, payload: dict, iterations: int) -> float:
    durations: list[float] = []
    for i in range(iterations):
        start = time.perf_counter()
        resp = client.post(
            path,
            json=payload,
            headers={
                **request_headers(token, idempotent=True),
                "X-Request-Id": f"perf-{path}-{i}",
                "Idempotency-Key": f"perf-op-{path}-{i}",
            },
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        if resp.status_code != 200:
            raise RuntimeError(f"{path} failed: {resp.status_code} {resp.text}")
        durations.append(elapsed_ms)
    return p95_ms(durations)


def benchmark_replay(client: TestClient, token: str, jobs: int) -> float:
    offline_replay_queue.clear()
    payload = {
        "offline_ops": [
            {
                "op_id": f"perf-offline-{i}",
                "payload": {
                    "operations": [
                        {
                            "item_key": "EGG",
                            "operation": "ADD",
                            "value": 1,
                            "unit": "个",
                            "source": "MANUAL",
                            "op_id": f"perf-offline-{i}",
                        }
                    ]
                },
            }
            for i in range(jobs)
        ]
    }
    enqueue = client.post(
        "/api/v1/inventory/offline/replay",
        json=payload,
        headers=request_headers(token, idempotent=True),
    )
    if enqueue.status_code != 200:
        raise RuntimeError(f"offline replay enqueue failed: {enqueue.status_code} {enqueue.text}")
    start = time.perf_counter()
    result = store.process_offline_replay_queue(max_jobs=jobs)
    elapsed_ms = (time.perf_counter() - start) * 1000
    if result["processed_jobs"] < jobs:
        raise RuntimeError(f"offline replay processed {result['processed_jobs']} < {jobs}")
    return elapsed_ms


def main() -> int:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    offline_replay_queue.clear()

    with TestClient(app) as client:
        login_resp = client.post(
            "/api/v1/auth/sms/login",
            json={"phone": "13800138111", "code": "123456", "device_id": "ios-perf-001"},
            headers=request_headers(idempotent=True),
        )
        if login_resp.status_code != 200:
            raise RuntimeError(f"login failed: {login_resp.status_code} {login_resp.text}")
        token = login_resp.json()["data"]["access_token"]

        voice_p95 = benchmark_parse(
            client,
            token,
            "/api/v1/ai/voice/parse",
            {"audio_url": "https://example.com/perf.m4a", "locale": "zh-CN"},
            ITERATIONS,
        )
        ocr_p95 = benchmark_parse(
            client,
            token,
            "/api/v1/ai/ocr/parse",
            {"image_urls": ["https://example.com/perf.jpg"]},
            ITERATIONS,
        )
        replay_100_ms = benchmark_replay(client, token, jobs=100)

    print(f"[phase6-perf] voice parse p95: {voice_p95:.2f} ms (target <= {VOICE_P95_THRESHOLD_MS:.0f} ms)")
    print(f"[phase6-perf] ocr parse p95: {ocr_p95:.2f} ms (target <= {OCR_P95_THRESHOLD_MS:.0f} ms)")
    print(f"[phase6-perf] offline replay 100 jobs: {replay_100_ms:.2f} ms (target <= {REPLAY_100_THRESHOLD_MS:.0f} ms)")

    failed = False
    if voice_p95 > VOICE_P95_THRESHOLD_MS:
        print("[phase6-perf] FAIL: voice parse p95 exceeded threshold")
        failed = True
    if ocr_p95 > OCR_P95_THRESHOLD_MS:
        print("[phase6-perf] FAIL: ocr parse p95 exceeded threshold")
        failed = True
    if replay_100_ms > REPLAY_100_THRESHOLD_MS:
        print("[phase6-perf] FAIL: offline replay throughput exceeded threshold")
        failed = True

    if failed:
        return 1
    print("[phase6-perf] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
