from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import os
import time
from typing import Any
from typing import Protocol
from uuid import uuid4

import httpx

from core.ai_quota import ProviderQuotaGuard, ai_quota_guard
from core.schemas import ItemKey, Operation, ParsedEntity

logger = logging.getLogger(__name__)


class STTProvider(Protocol):
    def transcribe(self, audio_url: str, locale: str) -> str: ...


class OCRTextProvider(Protocol):
    def extract_text(self, image_urls: list[str]) -> tuple[str, list[str]]: ...


class EntityParser(Protocol):
    def parse_entities(self, raw_text: str, parse_session_id: str) -> list[ParsedEntity]: ...


class LocalWhisperProvider:
    def transcribe(self, audio_url: str, locale: str) -> str:
        if not audio_url:
            return "补充鸡蛋 10 个"
        if "pork" in audio_url.lower():
            return "买猪肉一斤"
        return "补充鸡蛋 10 个"


class LocalOCRProvider:
    def extract_text(self, image_urls: list[str]) -> tuple[str, list[str]]:
        if not image_urls:
            return "猪肉 1 斤", ["酸奶"]
        has_yogurt = any("yogurt" in url.lower() for url in image_urls)
        if has_yogurt:
            return "酸奶 2 瓶", ["酸奶"]
        return "猪肉 1 斤", ["酸奶"]


class OpenAIWhisperProvider:
    def __init__(self, api_key: str, model: str = "whisper-1", timeout_seconds: float = 20.0, client: httpx.Client | None = None):
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._client = client

    def _infer_ext(self, content_type: str, audio_url: str) -> str:
        lowered = content_type.lower()
        if "wav" in lowered:
            return ".wav"
        if "ogg" in lowered:
            return ".ogg"
        if "mpeg" in lowered or "mp3" in lowered:
            return ".mp3"
        if "mp4" in lowered or audio_url.endswith(".m4a"):
            return ".m4a"
        return ".bin"

    def transcribe(self, audio_url: str, locale: str) -> str:
        if not audio_url:
            raise ValueError("audio_url is empty")

        close_client = self._client is None
        client = self._client or httpx.Client(timeout=self._timeout_seconds)
        try:
            audio_resp = client.get(audio_url)
            audio_resp.raise_for_status()
            content_type = audio_resp.headers.get("content-type", "application/octet-stream")
            filename = f"voice{self._infer_ext(content_type, audio_url)}"
            lang = (locale or "zh-CN").split("-")[0]
            response = client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                data={"model": self._model, "language": lang},
                files={"file": (filename, audio_resp.content, content_type)},
            )
            response.raise_for_status()
            payload = response.json()
            text = str(payload.get("text", "")).strip()
            if not text:
                raise ValueError("empty transcription result")
            return text
        finally:
            if close_client:
                client.close()


def _heuristic_entities(raw_text: str, parse_session_id: str) -> list[ParsedEntity]:
    text = raw_text.lower()
    if "\u86cb" in raw_text or "egg" in text:
        return [
            ParsedEntity(
                item_key=ItemKey.EGG,
                operation=Operation.ADD,
                value=10,
                unit="\u4e2a",
                normalized_value=10,
                normalized_unit="\u4e2a",
                confidence=0.95,
                parse_session_id=parse_session_id,
            )
        ]
    if "\u732a\u8089" in raw_text or "pork" in text:
        return [
            ParsedEntity(
                item_key=ItemKey.PORK,
                operation=Operation.ADD,
                value=1,
                unit="\u65a4",
                normalized_value=500,
                normalized_unit="g",
                confidence=0.88,
                parse_session_id=parse_session_id,
            )
        ]
    if "\u725b\u5976" in raw_text or "milk" in text:
        return [
            ParsedEntity(
                item_key=ItemKey.MILK,
                operation=Operation.ADD,
                value=1,
                unit="L",
                normalized_value=1,
                normalized_unit="L",
                confidence=0.85,
                parse_session_id=parse_session_id,
            )
        ]
    return [
        ParsedEntity(
            item_key=ItemKey.VEG,
            operation=Operation.ADD,
            value=1,
            unit="\u4efd",
            normalized_value=1,
            normalized_unit="\u4efd",
            confidence=0.7,
            parse_session_id=parse_session_id,
        )
    ]


def _build_category_hint() -> str:
    return (
        "Known system categories: EGG, MILK, MANTOU, RICE, PORK, VEG. "
        "If the item matches a user-defined category, use its uppercase item_key. "
        "If no known category matches, use a short uppercase identifier derived from the item name."
    )


def _extract_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return json.loads(stripped)
    left = stripped.find("{")
    right = stripped.rfind("}")
    if left == -1 or right == -1 or right <= left:
        raise ValueError("json object not found in model output")
    return json.loads(stripped[left : right + 1])


def _to_entities(payload: dict[str, Any], parse_session_id: str) -> list[ParsedEntity]:
    items = payload.get("entities")
    if not isinstance(items, list):
        raise ValueError("entities array missing")
    parsed: list[ParsedEntity] = []
    for row in items:
        if not isinstance(row, dict):
            continue
        item_key = str(row.get("item_key", "")).upper().strip()
        operation = str(row.get("operation", "")).upper()
        if not item_key:
            continue
        if operation not in Operation._value2member_map_:
            continue
        value = float(row.get("value", 0))
        normalized_value = float(row.get("normalized_value", value))
        unit = str(row.get("unit", "")).strip() or "\u4e2a"
        normalized_unit = str(row.get("normalized_unit", "")).strip() or unit
        confidence = max(0.0, min(1.0, float(row.get("confidence", 0.7))))
        parsed.append(
            ParsedEntity(
                item_key=item_key,
                operation=Operation(operation),
                value=value,
                unit=unit,
                normalized_value=normalized_value,
                normalized_unit=normalized_unit,
                confidence=confidence,
                parse_session_id=parse_session_id,
            )
        )
    if not parsed:
        raise ValueError("no valid entities in model response")
    return parsed


class HeuristicEntityParser:
    def parse_entities(self, raw_text: str, parse_session_id: str) -> list[ParsedEntity]:
        return _heuristic_entities(raw_text, parse_session_id)


class AnthropicClaudeParser:
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-latest", timeout_seconds: float = 20.0, client: httpx.Client | None = None):
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._client = client

    def parse_entities(self, raw_text: str, parse_session_id: str) -> list[ParsedEntity]:
        prompt = (
            "你是库存解析器。请从文本提取实体，返回 JSON: "
            '{"entities":[{"item_key":"uppercase identifier","operation":"ADD|SET|SUBTRACT|CLEAR","value":number,'
            '"unit":"string","normalized_value":number,"normalized_unit":"string","confidence":0-1}]}\n'
            f"{_build_category_hint()}\n"
            f"文本: {raw_text}"
        )
        close_client = self._client is None
        client = self._client or httpx.Client(timeout=self._timeout_seconds)
        try:
            response = client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self._model,
                    "max_tokens": 512,
                    "temperature": 0,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            payload = response.json()
            text_chunks = []
            for block in payload.get("content", []):
                if isinstance(block, dict) and block.get("type") == "text":
                    text_chunks.append(str(block.get("text", "")))
            text = "\n".join(text_chunks).strip()
            if not text:
                raise ValueError("empty anthropic output")
            return _to_entities(_extract_json(text), parse_session_id)
        finally:
            if close_client:
                client.close()


class OpenAIGPTParser:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", timeout_seconds: float = 20.0, client: httpx.Client | None = None):
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._client = client

    def parse_entities(self, raw_text: str, parse_session_id: str) -> list[ParsedEntity]:
        system_prompt = (
            "Extract inventory entities from user text. Return strict JSON object: "
            '{"entities":[{"item_key":"uppercase identifier","operation":"ADD|SET|SUBTRACT|CLEAR","value":number,'
            '"unit":"string","normalized_value":number,"normalized_unit":"string","confidence":0-1}]}\n'
            f"{_build_category_hint()}"
        )
        close_client = self._client is None
        client = self._client or httpx.Client(timeout=self._timeout_seconds)
        try:
            response = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}", "content-type": "application/json"},
                json={
                    "model": self._model,
                    "temperature": 0,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": raw_text},
                    ],
                },
            )
            response.raise_for_status()
            payload = response.json()
            choices = payload.get("choices", [])
            if not choices:
                raise ValueError("empty openai choices")
            content = choices[0].get("message", {}).get("content", "")
            if not content:
                raise ValueError("empty openai content")
            return _to_entities(_extract_json(str(content)), parse_session_id)
        finally:
            if close_client:
                client.close()


class DeepSeekParser:
    def __init__(
        self,
        api_key: str,
        model: str = "deepseek-chat",
        endpoint: str = "https://api.deepseek.com/v1/chat/completions",
        timeout_seconds: float = 20.0,
        client: httpx.Client | None = None,
    ):
        self._api_key = api_key
        self._model = model
        self._endpoint = endpoint
        self._timeout_seconds = timeout_seconds
        self._client = client

    def parse_entities(self, raw_text: str, parse_session_id: str) -> list[ParsedEntity]:
        system_prompt = (
            "Extract inventory entities from user text. Return strict JSON object: "
            '{"entities":[{"item_key":"uppercase identifier","operation":"ADD|SET|SUBTRACT|CLEAR","value":number,'
            '"unit":"string","normalized_value":number,"normalized_unit":"string","confidence":0-1}]}\n'
            f"{_build_category_hint()}"
        )
        close_client = self._client is None
        client = self._client or httpx.Client(timeout=self._timeout_seconds)
        try:
            response = client.post(
                self._endpoint,
                headers={"Authorization": f"Bearer {self._api_key}", "content-type": "application/json"},
                json={
                    "model": self._model,
                    "temperature": 0,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": raw_text},
                    ],
                },
            )
            response.raise_for_status()
            payload = response.json()
            choices = payload.get("choices", [])
            if not choices:
                raise ValueError("empty deepseek choices")
            content = choices[0].get("message", {}).get("content", "")
            if not content:
                raise ValueError("empty deepseek content")
            return _to_entities(_extract_json(str(content)), parse_session_id)
        finally:
            if close_client:
                client.close()


class ClaudeCompatibleParser:
    def __init__(self):
        self._fallback = HeuristicEntityParser()
        api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        self._external = AnthropicClaudeParser(api_key=api_key) if api_key else None

    def parse_entities(self, raw_text: str, parse_session_id: str) -> list[ParsedEntity]:
        if self._external is None:
            return self._fallback.parse_entities(raw_text, parse_session_id)
        try:
            return self._external.parse_entities(raw_text, parse_session_id)
        except Exception as exc:
            logger.warning("claude parser failed, fallback to heuristic parser: %s", exc)
            return self._fallback.parse_entities(raw_text, parse_session_id)


class GPTCompatibleParser:
    def __init__(self):
        self._fallback = HeuristicEntityParser()
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self._external = OpenAIGPTParser(api_key=api_key) if api_key else None

    def parse_entities(self, raw_text: str, parse_session_id: str) -> list[ParsedEntity]:
        if self._external is None:
            return self._fallback.parse_entities(raw_text, parse_session_id)
        try:
            return self._external.parse_entities(raw_text, parse_session_id)
        except Exception as exc:
            logger.warning("gpt parser failed, fallback to heuristic parser: %s", exc)
            return self._fallback.parse_entities(raw_text, parse_session_id)


class DeepSeekCompatibleParser:
    def __init__(self):
        self._fallback = HeuristicEntityParser()
        api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip() or "deepseek-chat"
        endpoint = os.getenv("DEEPSEEK_CHAT_ENDPOINT", "https://api.deepseek.com/v1/chat/completions").strip()
        self._external = DeepSeekParser(api_key=api_key, model=model, endpoint=endpoint) if api_key else None

    def parse_entities(self, raw_text: str, parse_session_id: str) -> list[ParsedEntity]:
        if self._external is None:
            return self._fallback.parse_entities(raw_text, parse_session_id)
        try:
            return self._external.parse_entities(raw_text, parse_session_id)
        except Exception as exc:
            logger.warning("deepseek parser failed, fallback to heuristic parser: %s", exc)
            return self._fallback.parse_entities(raw_text, parse_session_id)


@dataclass
class VoiceParseResult:
    session_id: str
    entities: list[ParsedEntity]
    confidence: float


@dataclass
class OcrParseResult:
    session_id: str
    entities: list[ParsedEntity]
    unknown_items: list[str]


@dataclass
class _CircuitBreaker:
    max_failures: int
    cooldown_seconds: int
    failures: int = 0
    opened_until_epoch: float = 0.0

    def is_open(self) -> bool:
        return self.opened_until_epoch > time.time()

    def mark_success(self) -> None:
        self.failures = 0
        self.opened_until_epoch = 0.0

    def mark_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.max_failures:
            self.opened_until_epoch = time.time() + self.cooldown_seconds


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name, "").strip()
    if not value:
        return default
    try:
        return max(1, int(value))
    except ValueError:
        return default


def _build_stt_provider() -> STTProvider:
    provider = os.getenv("STT_PROVIDER", "local").strip().lower()
    if provider in {"openai", "openai_whisper", "whisper"}:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if api_key:
            return OpenAIWhisperProvider(api_key=api_key)
    return LocalWhisperProvider()


def _build_parser() -> EntityParser:
    provider = os.getenv("LLM_PROVIDER", "deepseek").strip().lower()
    if provider in {"deepseek", "deepseek-chat"}:
        return DeepSeekCompatibleParser()
    if provider == "gpt":
        return GPTCompatibleParser()
    if provider == "claude":
        return ClaudeCompatibleParser()
    return DeepSeekCompatibleParser()


class AIPipeline:
    def __init__(
        self,
        stt_provider: STTProvider | None = None,
        ocr_provider: OCRTextProvider | None = None,
        parser: EntityParser | None = None,
        quota_guard: ProviderQuotaGuard | None = None,
        stt_breaker_max_failures: int | None = None,
        stt_breaker_cooldown_seconds: int | None = None,
        parser_breaker_max_failures: int | None = None,
        parser_breaker_cooldown_seconds: int | None = None,
    ):
        self._stt_provider = stt_provider or _build_stt_provider()
        self._stt_fallback = LocalWhisperProvider()
        self._ocr_provider = ocr_provider or LocalOCRProvider()
        self._parser = parser or _build_parser()
        self._parser_fallback = HeuristicEntityParser()
        self._quota_guard = quota_guard or ai_quota_guard
        self._stt_breaker = _CircuitBreaker(
            max_failures=stt_breaker_max_failures or _int_env("AI_STT_BREAKER_MAX_FAILURES", 3),
            cooldown_seconds=stt_breaker_cooldown_seconds or _int_env("AI_STT_BREAKER_COOLDOWN_SECONDS", 30),
        )
        self._parser_breaker = _CircuitBreaker(
            max_failures=parser_breaker_max_failures or _int_env("AI_PARSER_BREAKER_MAX_FAILURES", 3),
            cooldown_seconds=parser_breaker_cooldown_seconds or _int_env("AI_PARSER_BREAKER_COOLDOWN_SECONDS", 30),
        )
        self._metrics: dict[str, Any] = {
            "voice_requests": 0,
            "ocr_requests": 0,
            "stt_external_calls": 0,
            "stt_external_failures": 0,
            "stt_fallbacks": 0,
            "stt_breaker_skips": 0,
            "parser_external_calls": 0,
            "parser_external_failures": 0,
            "parser_fallbacks": 0,
            "parser_breaker_skips": 0,
            "stt_quota_rejections": 0,
            "parser_quota_rejections": 0,
            "last_quota_reason": "",
            "last_stt_error": "",
            "last_parser_error": "",
        }

    def metrics_snapshot(self) -> dict[str, Any]:
        return {
            **self._metrics,
            "stt_provider": type(self._stt_provider).__name__,
            "parser_provider": type(self._parser).__name__,
            "stt_breaker_open": self._stt_breaker.is_open(),
            "parser_breaker_open": self._parser_breaker.is_open(),
            "stt_breaker_open_until_epoch": self._stt_breaker.opened_until_epoch,
            "parser_breaker_open_until_epoch": self._parser_breaker.opened_until_epoch,
            "quota": self._quota_guard.snapshot(),
        }

    def parse_voice(self, audio_url: str, locale: str) -> VoiceParseResult:
        self._metrics["voice_requests"] += 1
        parse_session_id = f"parse-v-{uuid4().hex[:12]}"
        use_stt_fallback = False
        if self._stt_breaker.is_open():
            self._metrics["stt_breaker_skips"] += 1
            use_stt_fallback = True
        else:
            allowed, reason = self._quota_guard.allow("stt", estimated_tokens=max(1, len(audio_url) // 8 + 20))
            if not allowed:
                self._metrics["stt_quota_rejections"] += 1
                self._metrics["last_quota_reason"] = reason
                use_stt_fallback = True
            else:
                self._metrics["stt_external_calls"] += 1
                try:
                    raw_text = self._stt_provider.transcribe(audio_url, locale)
                    self._stt_breaker.mark_success()
                except Exception as exc:
                    logger.warning("stt provider failed, fallback to local whisper: %s", exc)
                    self._metrics["stt_external_failures"] += 1
                    self._metrics["last_stt_error"] = str(exc)
                    self._stt_breaker.mark_failure()
                    use_stt_fallback = True
        if use_stt_fallback:
            self._metrics["stt_fallbacks"] += 1
            raw_text = self._stt_fallback.transcribe(audio_url, locale)

        use_parser_fallback = False
        if self._parser_breaker.is_open():
            self._metrics["parser_breaker_skips"] += 1
            use_parser_fallback = True
        else:
            allowed, reason = self._quota_guard.allow("parser", estimated_tokens=max(1, len(raw_text) // 4 + 50))
            if not allowed:
                self._metrics["parser_quota_rejections"] += 1
                self._metrics["last_quota_reason"] = reason
                use_parser_fallback = True
            else:
                self._metrics["parser_external_calls"] += 1
                try:
                    entities = self._parser.parse_entities(raw_text, parse_session_id)
                    self._parser_breaker.mark_success()
                except Exception as exc:
                    logger.warning("entity parser failed, fallback to heuristic parser: %s", exc)
                    self._metrics["parser_external_failures"] += 1
                    self._metrics["last_parser_error"] = str(exc)
                    self._parser_breaker.mark_failure()
                    use_parser_fallback = True
        if use_parser_fallback:
            self._metrics["parser_fallbacks"] += 1
            entities = self._parser_fallback.parse_entities(raw_text, parse_session_id)

        confidence = max((entity.confidence for entity in entities), default=0.0)
        return VoiceParseResult(session_id=parse_session_id, entities=entities, confidence=confidence)

    def parse_ocr(self, image_urls: list[str]) -> OcrParseResult:
        self._metrics["ocr_requests"] += 1
        parse_session_id = f"parse-o-{uuid4().hex[:12]}"
        raw_text, unknown_items = self._ocr_provider.extract_text(image_urls)
        use_parser_fallback = False
        if self._parser_breaker.is_open():
            self._metrics["parser_breaker_skips"] += 1
            use_parser_fallback = True
        else:
            allowed, reason = self._quota_guard.allow("parser", estimated_tokens=max(1, len(raw_text) // 4 + 50))
            if not allowed:
                self._metrics["parser_quota_rejections"] += 1
                self._metrics["last_quota_reason"] = reason
                use_parser_fallback = True
            else:
                self._metrics["parser_external_calls"] += 1
                try:
                    entities = self._parser.parse_entities(raw_text, parse_session_id)
                    self._parser_breaker.mark_success()
                except Exception as exc:
                    logger.warning("ocr entity parser failed, fallback to heuristic parser: %s", exc)
                    self._metrics["parser_external_failures"] += 1
                    self._metrics["last_parser_error"] = str(exc)
                    self._parser_breaker.mark_failure()
                    use_parser_fallback = True
        if use_parser_fallback:
            self._metrics["parser_fallbacks"] += 1
            entities = self._parser_fallback.parse_entities(raw_text, parse_session_id)
        return OcrParseResult(session_id=parse_session_id, entities=entities, unknown_items=unknown_items)

    def rank_tasks(self, tasks: list[dict]) -> tuple[str, list[dict]]:
        """AI re-rank of tasks. Returns (method, tasks) where method is "ai"|"heuristic". Falls back to input order."""
        if not tasks:
            return "heuristic", tasks
        try:
            ranked = self._ai_rank(tasks)
            if not ranked:
                return "heuristic", tasks
            by_id = {t["task_id"]: t for t in tasks}
            reordered: list[dict] = []
            for index, (task_id, reason) in enumerate(ranked):
                source = by_id.get(task_id)
                if source is None:
                    continue
                entry = dict(source)
                entry["reason"] = reason
                entry["score"] = round(100.0 - index * 5.0, 1)
                reordered.append(entry)
            seen = {t["task_id"] for t in reordered}
            for task in tasks:
                if task["task_id"] not in seen:
                    reordered.append(task)
            if len(reordered) == len(tasks):
                return "ai", reordered
        except Exception as exc:
            logger.warning("task AI ranking failed, fallback to heuristic: %s", exc)
        return "heuristic", tasks

    def _ai_rank(self, tasks: list[dict]) -> list[tuple[str, str]]:
        api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        if not api_key:
            return []
        model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip() or "deepseek-chat"
        endpoint = os.getenv("DEEPSEEK_CHAT_ENDPOINT", "https://api.deepseek.com/v1/chat/completions").strip()
        lines = "\n".join(
            f"- id:{t['task_id']} 标题:{t['title']} 截止:{t.get('due_at') or '无'} 优先级:{t.get('priority', 3)}（1最高4最低）"
            for t in tasks
        )
        prompt = (
            "你是任务优先级助手。请按截止时间和重要性将以下任务从高到低排序，"
            '只返回 JSON：{"ranking":[{"task_id":"...","reason":"一句话理由"}]}。\n'
            + lines
        )
        with httpx.Client(timeout=20.0) as client:
            response = client.post(
                endpoint,
                headers={"Authorization": f"Bearer {api_key}", "content-type": "application/json"},
                json={"model": model, "temperature": 0, "messages": [{"role": "user", "content": prompt}]},
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            data = json.loads(content)
            ranking = data.get("ranking", [])
            result: list[tuple[str, str]] = []
            for row in ranking:
                if isinstance(row, dict) and row.get("task_id"):
                    result.append((str(row["task_id"]), str(row.get("reason", "AI 排序"))))
            return result


ai_pipeline = AIPipeline()
