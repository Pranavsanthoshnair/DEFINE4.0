"""
LLM fallback for intent classification.
Only called when rules gave nothing AND model confidence < threshold.
Sends ONLY the transcript text — never audio, phone numbers, or personal data.

Enabled by env LLM_FALLBACK=gemini|groq (default: none).
"""

from __future__ import annotations

import hashlib
import json
import time
from functools import lru_cache

import httpx
import structlog

from app.schemas import IntentLabel

log = structlog.get_logger()

ALLOWED_LABELS = {
    "confirm", "decline", "reschedule",
    "call_later", "stop_calling", "unclear",
}

# Simple in-memory cache keyed by transcript hash (holds template text only)
_cache: dict[str, tuple[IntentLabel, float]] = {}


def _failure_fields(exc: Exception) -> dict[str, int | str]:
    """Return safe diagnostics without serialising request URLs or credentials."""
    fields: dict[str, int | str] = {"error_type": type(exc).__name__}
    if isinstance(exc, httpx.HTTPStatusError) and exc.response is not None:
        fields["status_code"] = exc.response.status_code
    return fields


def _cache_key(text: str) -> str:
    return hashlib.sha256(text.lower().strip().encode()).hexdigest()


def _build_prompt(text: str, allowed: list[IntentLabel]) -> str:
    return (
        "Classify the following short phone call utterance into exactly one intent.\n"
        f"Allowed intents: {', '.join(allowed)}.\n"
        "Respond with only valid JSON: {\"intent\": \"<one of allowed>\", \"confidence\": <0..1>}\n"
        f"Utterance: {text}"
    )


async def _call_gemini(
    text: str, allowed: list[IntentLabel], api_key: str
) -> tuple[IntentLabel, float] | None:
    prompt = _build_prompt(text, allowed)
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"gemini-1.5-flash:generateContent?key={api_key}",
                json={"contents": [{"parts": [{"text": prompt}]}]},
            )
            resp.raise_for_status()
            raw = resp.json()
            content = (
                raw["candidates"][0]["content"]["parts"][0]["text"]
                .strip()
                .strip("```json").strip("```").strip()
            )
            parsed = json.loads(content)
            intent = parsed.get("intent", "unclear")
            conf = float(parsed.get("confidence", 0.5))
            if intent not in ALLOWED_LABELS:
                intent = "unclear"
            return intent, min(max(conf, 0.0), 1.0)  # type: ignore[return-value]
    except Exception as exc:
        log.warning("gemini_fallback_failed", **_failure_fields(exc))
        return None


async def _call_groq(
    text: str, allowed: list[IntentLabel], api_key: str
) -> tuple[IntentLabel, float] | None:
    prompt = _build_prompt(text, allowed)
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "llama3-8b-8192",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0,
                    "max_tokens": 80,
                },
            )
            resp.raise_for_status()
            content = (
                resp.json()["choices"][0]["message"]["content"]
                .strip()
                .strip("```json").strip("```").strip()
            )
            parsed = json.loads(content)
            intent = parsed.get("intent", "unclear")
            conf = float(parsed.get("confidence", 0.5))
            if intent not in ALLOWED_LABELS:
                intent = "unclear"
            return intent, min(max(conf, 0.0), 1.0)  # type: ignore[return-value]
    except Exception as exc:
        log.warning("groq_fallback_failed", **_failure_fields(exc))
        return None


async def classify_with_llm(
    text: str,
    allowed_intents: list[IntentLabel],
) -> tuple[IntentLabel, float]:
    """
    Try LLM fallback. Returns (intent, confidence) or ("unclear", 0.0) on failure.
    Never logs the transcript text — only length and language metadata.
    """
    from app.config import settings

    if settings.llm_fallback == "none":
        return "unclear", 0.0

    # Check cache first
    key = _cache_key(text)
    if key in _cache:
        log.debug("llm_cache_hit", text_len=len(text))
        return _cache[key]

    log.info("llm_fallback_invoked", provider=settings.llm_fallback, text_len=len(text))

    result: tuple[IntentLabel, float] | None = None

    if settings.llm_fallback == "gemini" and settings.gemini_api_key:
        result = await _call_gemini(text, allowed_intents, settings.gemini_api_key)

    if result is None and settings.llm_fallback == "groq" and settings.groq_api_key:
        result = await _call_groq(text, allowed_intents, settings.groq_api_key)

    if result is None:
        return "unclear", 0.0

    _cache[key] = result
    return result
