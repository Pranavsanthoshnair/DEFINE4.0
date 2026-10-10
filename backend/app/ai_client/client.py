"""
AI service client and FakeAIClient.

Real client: async httpx calls to ``settings.ai_base_url`` with
``X-Internal-Token`` header.  Retries once on 5xx or timeout.

FakeAIClient: returns realistic fake responses; used in tests and when
``AI_BASE_URL`` is empty.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import structlog

from app.ai_client.schemas import (
    IntentRequest,
    IntentResponse,
    SpeechIntentResponse,
    SttResponse,
    TranslateRequest,
    TranslateResponse,
)
from app.core.config import settings

log = structlog.get_logger()

# ---------------------------------------------------------------------------
# Real client
# ---------------------------------------------------------------------------


class AIClient:
    """Async typed client for the internal AI micro-service (port 8200)."""

    def __init__(self, base_url: str | None = None, token: str | None = None) -> None:
        self._base_url = (base_url or settings.ai_base_url).rstrip("/")
        self._token = token or settings.ai_internal_token
        self._headers = {"X-Internal-Token": self._token}

    # ------------------------------------------------------------------
    # translate
    # ------------------------------------------------------------------

    async def translate(
        self,
        segments: dict[str, str],
        source_lang: str,
        target_lang: str,
    ) -> TranslateResponse:
        """Translate template segments preserving ``{placeholder}`` tokens.

        Timeout: 60 s.  Retries once on 5xx or network timeout.
        """
        body = TranslateRequest(
            segments=segments,
            source_language=source_lang,
            target_language=target_lang,
        ).model_dump()
        return await self._post_json(
            "/v1/translate",
            body,
            timeout=60.0,
            response_cls=TranslateResponse,
        )

    # ------------------------------------------------------------------
    # tts
    # ------------------------------------------------------------------

    async def tts(
        self,
        text: str,
        language: str,
        voice: str | None = None,
    ) -> bytes:
        """Synthesise speech; returns raw WAV bytes.

        Timeout: 30 s.  Retries once on 5xx or network timeout.
        """
        body = {"text": text, "language": language, "voice": voice}
        return await self._post_bytes("/v1/tts", body, timeout=30.0)

    # ------------------------------------------------------------------
    # intent
    # ------------------------------------------------------------------

    async def intent(
        self,
        text: str,
        language: str,
        allowed_intents: list[str],
    ) -> IntentResponse:
        """Classify intent from text.

        Timeout: 10 s.
        """
        body = IntentRequest(
            text=text,
            language=language,
            allowed_intents=allowed_intents,
        ).model_dump()
        return await self._post_json(
            "/v1/intent",
            body,
            timeout=10.0,
            response_cls=IntentResponse,
        )

    # ------------------------------------------------------------------
    # stt
    # ------------------------------------------------------------------

    async def stt(
        self,
        audio_bytes: bytes,
        language: str | None = None,
    ) -> SttResponse:
        """Speech-to-text from WAV bytes.

        Timeout: 10 s.
        """
        files: dict[str, Any] = {
            "audio": ("audio.wav", audio_bytes, "audio/wav"),
        }
        if language:
            files["language"] = (None, language)
        return await self._post_multipart(
            "/v1/stt", files, timeout=10.0, response_cls=SttResponse
        )

    # ------------------------------------------------------------------
    # speech_intent
    # ------------------------------------------------------------------

    async def speech_intent(
        self,
        audio_bytes: bytes,
        language: str | None = None,
        allowed_intents: list[str] | None = None,
    ) -> SpeechIntentResponse:
        """Run VAD + STT + intent in one network call.

        Timeout: 10 s.
        """
        files: dict[str, Any] = {
            "audio": ("audio.wav", audio_bytes, "audio/wav"),
        }
        if language:
            files["language"] = (None, language)
        if allowed_intents:
            files["allowed_intents"] = (None, json.dumps(allowed_intents))
        return await self._post_multipart(
            "/v1/speech-intent",
            files,
            timeout=10.0,
            response_cls=SpeechIntentResponse,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _post_json(
        self,
        path: str,
        body: dict,
        timeout: float,
        response_cls: type,
    ):
        url = self._base_url + path
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(
                    headers=self._headers, timeout=timeout
                ) as client:
                    resp = await client.post(url, json=body)
                if resp.status_code < 500:
                    resp.raise_for_status()
                    return response_cls.model_validate(resp.json())
                if attempt == 0:
                    log.warning("ai_client_retry", path=path, status=resp.status_code)
                    continue
                resp.raise_for_status()
            except httpx.TimeoutException:
                if attempt == 0:
                    log.warning("ai_client_timeout_retry", path=path)
                    continue
                raise
        raise RuntimeError(f"AI service failed after retries: {path}")

    async def _post_bytes(
        self,
        path: str,
        body: dict,
        timeout: float,
    ) -> bytes:
        url = self._base_url + path
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(
                    headers=self._headers, timeout=timeout
                ) as client:
                    resp = await client.post(url, json=body)
                if resp.status_code < 500:
                    resp.raise_for_status()
                    return resp.content
                if attempt == 0:
                    log.warning("ai_client_retry", path=path, status=resp.status_code)
                    continue
                resp.raise_for_status()
            except httpx.TimeoutException:
                if attempt == 0:
                    log.warning("ai_client_timeout_retry", path=path)
                    continue
                raise
        raise RuntimeError(f"AI service failed after retries: {path}")

    async def _post_multipart(
        self,
        path: str,
        files: dict,
        timeout: float,
        response_cls: type,
    ):
        url = self._base_url + path
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(
                    headers=self._headers, timeout=timeout
                ) as client:
                    resp = await client.post(url, files=files)
                if resp.status_code < 500:
                    resp.raise_for_status()
                    return response_cls.model_validate(resp.json())
                if attempt == 0:
                    log.warning("ai_client_retry", path=path, status=resp.status_code)
                    continue
                resp.raise_for_status()
            except httpx.TimeoutException:
                if attempt == 0:
                    log.warning("ai_client_timeout_retry", path=path)
                    continue
                raise
        raise RuntimeError(f"AI service failed after retries: {path}")


# ---------------------------------------------------------------------------
# FakeAIClient — used in tests and when AI_BASE_URL is empty
# ---------------------------------------------------------------------------

class FakeAIClient:
    """Returns realistic fake responses without any network calls."""

    async def translate(
        self,
        segments: dict[str, str],
        source_lang: str,
        target_lang: str,
    ) -> TranslateResponse:
        """Return segments with a language tag prepended to each value."""
        translated = {
            k: f"[{target_lang}] {v}" for k, v in segments.items()
        }
        return TranslateResponse(segments=translated, model="fake-translate")

    async def tts(
        self,
        text: str,
        language: str,
        voice: str | None = None,
    ) -> bytes:
        """Return a minimal valid WAV file (44-byte header, silent)."""
        # 44-byte RIFF/WAV header, mono 8 kHz, 0 samples
        header = (
            b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00"
            b"\x01\x00\x01\x00@\x1f\x00\x00\x80>\x00\x00"
            b"\x02\x00\x10\x00data\x00\x00\x00\x00"
        )
        return header

    async def intent(
        self,
        text: str,
        language: str,
        allowed_intents: list[str],
    ) -> IntentResponse:
        """Always returns 'confirm' with confidence 0.99."""
        label = "confirm" if "confirm" in allowed_intents else allowed_intents[0]
        return IntentResponse(
            intent=label,
            confidence=0.99,
            source="rules",
            latency_ms=1,
        )

    async def stt(
        self,
        audio_bytes: bytes,
        language: str | None = None,
    ) -> SttResponse:
        # Do not fabricate words if audio is empty or silence
        return SttResponse(
            text="",
            language=language or "en",
            confidence=0.0,
            duration_ms=0,
            latency_ms=1,
            model="fake-stt",
        )

    async def speech_intent(
        self,
        audio_bytes: bytes,
        language: str | None = None,
        allowed_intents: list[str] | None = None,
    ) -> SpeechIntentResponse:
        return SpeechIntentResponse(
            text="",
            language=language or "en",
            intent="unclear",
            confidence=0.0,
            source="rules",
            stt_model="fake-stt",
            latency_ms=1,
            no_speech=True,
        )


# ---------------------------------------------------------------------------
# Module-level singleton — swapped in tests via monkeypatching
# ---------------------------------------------------------------------------

def get_ai_client() -> AIClient | FakeAIClient:
    """Return a real or fake AI client depending on configuration."""
    if not settings.ai_base_url or settings.ai_base_url in ("", "http://localhost:8200"):
        # Treat empty/default as fake for dev convenience
        # In prod, AI_BASE_URL must be explicitly set
        if settings.app_env == "dev":
            return FakeAIClient()  # type: ignore[return-value]
    return AIClient()
