from __future__ import annotations

from uuid import uuid4

from core.ai_pipeline import AIPipeline
from core.ai_quota import ProviderQuotaGuard


def test_provider_quota_guard_local_limit():
    guard = ProviderQuotaGuard(qps_per_minute=1, token_per_minute=10, token_per_day=100, redis_url="redis://localhost:0/0")
    provider = f"parser-test-{uuid4().hex}"
    ok1, reason1 = guard.allow(provider, estimated_tokens=5)
    ok2, reason2 = guard.allow(provider, estimated_tokens=5)
    assert ok1 is True
    assert reason1 == "OK"
    assert ok2 is False
    assert reason2 in {"QPS_LIMIT_EXCEEDED", "TOKEN_MINUTE_LIMIT_EXCEEDED"}


def test_ai_pipeline_quota_rejection_fallback():
    guard = ProviderQuotaGuard(qps_per_minute=1, token_per_minute=1, token_per_day=2, redis_url="redis://localhost:0/0")
    pipeline = AIPipeline(quota_guard=guard)

    # first call may pass quota partially, second call should be quota-rejected and fallback-safe
    first = pipeline.parse_voice("https://example.com/voice-any.m4a", "zh-CN")
    second = pipeline.parse_voice("https://example.com/voice-any.m4a", "zh-CN")

    assert first.session_id.startswith("parse-v-")
    assert second.session_id.startswith("parse-v-")
    metrics = pipeline.metrics_snapshot()
    assert metrics["stt_quota_rejections"] >= 1 or metrics["parser_quota_rejections"] >= 1
    assert metrics["quota"]["backend"] in {"local", "redis"}
