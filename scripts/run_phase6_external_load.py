#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import os
import pathlib
import socket
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any, Callable

import httpx


ROOT = pathlib.Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
HOST = "127.0.0.1"
STARTUP_TIMEOUT_SEC = 25
REQUEST_TIMEOUT_SEC = 8.0

VOICE_P95_THRESHOLD_MS = 1200.0
OCR_P95_THRESHOLD_MS = 2800.0
HOME_LIST_P95_THRESHOLD_MS = 1500.0
OFFLINE_ENQUEUE_100_THRESHOLD_MS = 30000.0


@dataclass
class Scenario:
    name: str
    method: str
    path: str
    users: int
    requests_per_user: int
    p95_threshold_ms: float
    payload_factory: Callable[[int, int], dict[str, Any] | None]


@dataclass
class ScenarioResult:
    name: str
    total_requests: int
    errors: int
    p95_ms: float
    avg_ms: float
    max_ms: float
    throughput_rps: float


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((HOST, 0))
        return int(sock.getsockname()[1])


def _headers(token: str | None, request_id: str, *, idempotency_key: str | None = None) -> dict[str, str]:
    headers = {
        "X-Request-Id": request_id,
        "X-App-Version": "1.1.0",
        "X-Platform": "ios",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    return headers


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = int(0.95 * (len(ordered) - 1))
    return ordered[index]


def _server_env(db_path: pathlib.Path) -> dict[str, str]:
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path}"
    env["STT_PROVIDER"] = "local"
    env["LLM_PROVIDER"] = "deepseek"
    env["DEEPSEEK_API_KEY"] = ""
    env["OPENAI_API_KEY"] = ""
    env["ANTHROPIC_API_KEY"] = ""
    env["AI_PROVIDER_QPS_PER_MINUTE"] = "100000"
    env["AI_PROVIDER_TOKEN_PER_MINUTE"] = "100000000"
    env["AI_PROVIDER_TOKEN_PER_DAY"] = "1000000000"
    env["AI_QUOTA_REDIS_URL"] = ""
    env["OFFLINE_QUEUE_REDIS_URL"] = ""
    return env


def _start_server(port: int, db_path: pathlib.Path) -> subprocess.Popen[str]:
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "main:app",
        "--host",
        HOST,
        "--port",
        str(port),
        "--log-level",
        "warning",
    ]
    return subprocess.Popen(
        cmd,
        cwd=str(API_ROOT),
        env=_server_env(db_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _wait_for_server(base_url: str, process: subprocess.Popen[str]) -> None:
    deadline = time.time() + STARTUP_TIMEOUT_SEC
    with httpx.Client(base_url=base_url, timeout=REQUEST_TIMEOUT_SEC, trust_env=False) as client:
        while time.time() < deadline:
            if process.poll() is not None:
                output = process.communicate(timeout=1)[0]
                raise RuntimeError(f"api server exited before ready:\n{output}")
            try:
                resp = client.get(
                    "/healthz",
                    headers=_headers(None, "load-health-check"),
                )
                if resp.status_code == 200:
                    return
            except Exception:
                pass
            time.sleep(0.3)
    process.terminate()
    raise TimeoutError(f"api server did not become ready in {STARTUP_TIMEOUT_SEC}s")


def _stop_server(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)


def _login(base_url: str, phone: str) -> str:
    with httpx.Client(base_url=base_url, timeout=REQUEST_TIMEOUT_SEC, trust_env=False) as client:
        resp = client.post(
            "/api/v1/auth/sms/login",
            json={"phone": phone, "code": "123456", "device_id": f"ios-load-{phone[-4:]}"},
            headers=_headers(None, f"load-login-{phone}", idempotency_key=f"load-login-{phone}"),
        )
        if resp.status_code != 200:
            raise RuntimeError(f"login failed: {resp.status_code} {resp.text}")
        data = resp.json()["data"]
        return str(data["access_token"])


async def _run_worker(
    client: httpx.AsyncClient,
    token: str,
    scenario: Scenario,
    worker_id: int,
    latencies: list[float],
    errors: list[str],
) -> None:
    method = scenario.method.upper()
    for idx in range(scenario.requests_per_user):
        request_id = f"load-{scenario.name}-{worker_id}-{idx}"
        payload = scenario.payload_factory(worker_id, idx)
        idempotency_key = request_id if method != "GET" else None
        start = time.perf_counter()
        try:
            if method == "GET":
                resp = await client.get(
                    scenario.path,
                    headers=_headers(token, request_id),
                )
            else:
                resp = await client.post(
                    scenario.path,
                    json=payload,
                    headers=_headers(token, request_id, idempotency_key=idempotency_key),
                )
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies.append(elapsed_ms)
            if resp.status_code != 200:
                errors.append(f"{scenario.name}:{resp.status_code}:{resp.text[:180]}")
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies.append(elapsed_ms)
            errors.append(f"{scenario.name}:exception:{exc}")


async def run_scenario(base_url: str, token: str, scenario: Scenario) -> ScenarioResult:
    latencies: list[float] = []
    errors: list[str] = []
    started = time.perf_counter()
    limits = httpx.Limits(max_connections=max(50, scenario.users * 3), max_keepalive_connections=20)
    timeout = httpx.Timeout(REQUEST_TIMEOUT_SEC)
    async with httpx.AsyncClient(base_url=base_url, limits=limits, timeout=timeout, trust_env=False) as client:
        workers = [
            _run_worker(client, token, scenario, worker_id, latencies, errors)
            for worker_id in range(scenario.users)
        ]
        await asyncio.gather(*workers)
    elapsed = max(0.001, time.perf_counter() - started)
    total = len(latencies)
    return ScenarioResult(
        name=scenario.name,
        total_requests=total,
        errors=len(errors),
        p95_ms=_p95(latencies),
        avg_ms=(statistics.fmean(latencies) if latencies else 0.0),
        max_ms=(max(latencies) if latencies else 0.0),
        throughput_rps=total / elapsed,
    )


def run_offline_enqueue_100(base_url: str, token: str) -> float:
    payload = {
        "offline_ops": [
            {
                "op_id": f"load-offline-{idx}",
                "payload": {
                    "operations": [
                        {
                            "item_key": "EGG",
                            "operation": "ADD",
                            "value": 1,
                            "unit": "个",
                            "source": "MANUAL",
                            "op_id": f"load-offline-{idx}",
                        }
                    ]
                },
            }
            for idx in range(100)
        ]
    }
    with httpx.Client(base_url=base_url, timeout=REQUEST_TIMEOUT_SEC, trust_env=False) as client:
        started = time.perf_counter()
        resp = client.post(
            "/api/v1/inventory/offline/replay",
            json=payload,
            headers=_headers(token, "load-offline-100", idempotency_key="load-offline-100"),
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
    if resp.status_code != 200:
        raise RuntimeError(f"offline enqueue failed: {resp.status_code} {resp.text}")
    return elapsed_ms


def _scenario_definitions() -> list[Scenario]:
    return [
        Scenario(
            name="home_inventory_list",
            method="GET",
            path="/api/v1/inventory/items",
            users=20,
            requests_per_user=20,
            p95_threshold_ms=HOME_LIST_P95_THRESHOLD_MS,
            payload_factory=lambda _w, _i: None,
        ),
        Scenario(
            name="voice_parse",
            method="POST",
            path="/api/v1/ai/voice/parse",
            users=10,
            requests_per_user=12,
            p95_threshold_ms=VOICE_P95_THRESHOLD_MS,
            payload_factory=lambda w, i: {
                "audio_url": f"https://example.com/load/{w}/{i}.m4a",
                "locale": "zh-CN",
            },
        ),
        Scenario(
            name="ocr_parse",
            method="POST",
            path="/api/v1/ai/ocr/parse",
            users=10,
            requests_per_user=12,
            p95_threshold_ms=OCR_P95_THRESHOLD_MS,
            payload_factory=lambda w, i: {"image_urls": [f"https://example.com/load/{w}/{i}.jpg"]},
        ),
    ]


def _print_result(result: ScenarioResult, threshold_ms: float) -> None:
    print(
        f"[phase6-load] {result.name}: total={result.total_requests}, errors={result.errors}, "
        f"p95={result.p95_ms:.2f}ms, avg={result.avg_ms:.2f}ms, max={result.max_ms:.2f}ms, "
        f"throughput={result.throughput_rps:.2f}rps, target_p95<={threshold_ms:.0f}ms"
    )


def main() -> int:
    port = _find_free_port()
    base_url = f"http://{HOST}:{port}"
    db_path = API_ROOT / f"phase6_external_load_{int(time.time())}.db"
    server = _start_server(port, db_path)
    try:
        _wait_for_server(base_url, server)
        token = _login(base_url, "13800138111")

        scenario_results: list[tuple[Scenario, ScenarioResult]] = []
        for scenario in _scenario_definitions():
            result = asyncio.run(run_scenario(base_url, token, scenario))
            scenario_results.append((scenario, result))
            _print_result(result, scenario.p95_threshold_ms)

        offline_enqueue_ms = run_offline_enqueue_100(base_url, token)
        print(
            f"[phase6-load] offline_enqueue_100: {offline_enqueue_ms:.2f}ms "
            f"(target <= {OFFLINE_ENQUEUE_100_THRESHOLD_MS:.0f}ms)"
        )

        failed = False
        for scenario, result in scenario_results:
            if result.errors > 0:
                print(f"[phase6-load] FAIL: {scenario.name} has {result.errors} request errors")
                failed = True
            if result.p95_ms > scenario.p95_threshold_ms:
                print(f"[phase6-load] FAIL: {scenario.name} p95 exceeded threshold")
                failed = True
        if offline_enqueue_ms > OFFLINE_ENQUEUE_100_THRESHOLD_MS:
            print("[phase6-load] FAIL: offline enqueue 100 exceeded threshold")
            failed = True

        if failed:
            return 1
        print("[phase6-load] PASS")
        return 0
    finally:
        _stop_server(server)
        if db_path.exists():
            db_path.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
