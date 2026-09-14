from __future__ import annotations

import httpx

from core.ai_pipeline import (
    AIPipeline,
    AnthropicClaudeParser,
    DeepSeekParser,
    HeuristicEntityParser,
    OpenAIGPTParser,
    OpenAIWhisperProvider,
)
from core.schemas import ItemKey


def test_openai_whisper_provider_with_mock_transport():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and str(request.url) == "https://example.com/voice.m4a":
            return httpx.Response(200, content=b"audio-bytes", headers={"content-type": "audio/mp4"})
        if request.method == "POST" and str(request.url) == "https://api.openai.com/v1/audio/transcriptions":
            return httpx.Response(200, json={"text": "补充鸡蛋 8 个"})
        return httpx.Response(404, json={"error": "unexpected"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = OpenAIWhisperProvider(api_key="test-key", client=client)
    text = provider.transcribe("https://example.com/voice.m4a", "zh-CN")
    assert "鸡蛋" in text


def test_anthropic_parser_with_mock_transport():
    output = {
        "content": [
            {
                "type": "text",
                "text": '{"entities":[{"item_key":"PORK","operation":"ADD","value":1,"unit":"斤","normalized_value":500,"normalized_unit":"g","confidence":0.88}]}',
            }
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://api.anthropic.com/v1/messages"
        return httpx.Response(200, json=output)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    parser = AnthropicClaudeParser(api_key="anthropic-key", client=client)
    entities = parser.parse_entities("买猪肉一斤", "parse-v-unit")
    assert entities[0].item_key == ItemKey.PORK
    assert entities[0].parse_session_id == "parse-v-unit"


def test_openai_gpt_parser_with_mock_transport():
    output = {
        "choices": [
            {
                "message": {
                    "content": '{"entities":[{"item_key":"MILK","operation":"ADD","value":1,"unit":"L","normalized_value":1,"normalized_unit":"L","confidence":0.9}]}'
                }
            }
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://api.openai.com/v1/chat/completions"
        return httpx.Response(200, json=output)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    parser = OpenAIGPTParser(api_key="openai-key", client=client)
    entities = parser.parse_entities("牛奶一升", "parse-o-unit")
    assert entities[0].item_key == ItemKey.MILK
    assert entities[0].parse_session_id == "parse-o-unit"


def test_deepseek_parser_with_mock_transport():
    output = {
        "choices": [
            {
                "message": {
                    "content": '{"entities":[{"item_key":"EGG","operation":"ADD","value":6,"unit":"个","normalized_value":6,"normalized_unit":"个","confidence":0.92}]}'
                }
            }
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://api.deepseek.com/v1/chat/completions"
        return httpx.Response(200, json=output)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    parser = DeepSeekParser(api_key="deepseek-key", client=client)
    entities = parser.parse_entities("补鸡蛋 6 个", "parse-deepseek-unit")
    assert entities[0].item_key == ItemKey.EGG
    assert entities[0].parse_session_id == "parse-deepseek-unit"


def test_ai_pipeline_fallback_when_stt_or_parser_fails():
    class BrokenSTT:
        def transcribe(self, audio_url: str, locale: str) -> str:
            raise RuntimeError("stt down")

    class BrokenParser:
        def parse_entities(self, raw_text: str, parse_session_id: str):
            raise RuntimeError("llm down")

    pipeline = AIPipeline(stt_provider=BrokenSTT(), parser=BrokenParser())
    result = pipeline.parse_voice("https://example.com/voice-any.m4a", "zh-CN")
    assert result.session_id.startswith("parse-v-")
    assert result.confidence > 0
    assert len(result.entities) >= 1

    fallback_pipeline = AIPipeline(parser=HeuristicEntityParser())
    ocr_result = fallback_pipeline.parse_ocr(["https://example.com/yogurt-receipt.jpg"])
    assert ocr_result.session_id.startswith("parse-o-")
    assert len(ocr_result.unknown_items) >= 1


def test_ai_pipeline_parser_circuit_breaker_skips_after_threshold():
    class BrokenParser:
        def __init__(self):
            self.calls = 0

        def parse_entities(self, raw_text: str, parse_session_id: str):
            self.calls += 1
            raise RuntimeError("deepseek unavailable")

    parser = BrokenParser()
    pipeline = AIPipeline(
        parser=parser,
        parser_breaker_max_failures=1,
        parser_breaker_cooldown_seconds=60,
    )

    first = pipeline.parse_voice("https://example.com/voice-any.m4a", "zh-CN")
    second = pipeline.parse_voice("https://example.com/voice-any.m4a", "zh-CN")

    assert first.session_id.startswith("parse-v-")
    assert second.session_id.startswith("parse-v-")
    assert parser.calls == 1

    metrics = pipeline.metrics_snapshot()
    assert metrics["parser_external_calls"] == 1
    assert metrics["parser_external_failures"] == 1
    assert metrics["parser_breaker_skips"] >= 1
    assert metrics["parser_fallbacks"] >= 2
    assert metrics["parser_breaker_open"] is True
