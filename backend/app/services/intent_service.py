"""
Unified Intent Classification Service
======================================
Cascade:
  1. Own AI service  (Sarvam STT + MuRIL intent — runs locally/on Render)
  2. Gemini 1.5 Flash (if GEMINI_API_KEY set)
  3. Groq LLaMA-3    (if GROQ_API_KEY set)
  4. Keyword rules   (always available — zero deps)

Never logs transcript text, names, or phone numbers.
Used by ALL channels: telephony webhooks, browser sessions, Telegram bot.
"""
from __future__ import annotations

import hashlib
import json
from typing import Optional

import httpx
import structlog

from app.core.config import settings

log = structlog.get_logger()

ALLOWED_INTENTS = ["confirm", "decline", "reschedule", "call_later", "stop_calling", "unclear"]

# Keyword patterns (language-agnostic basics)
_CONFIRM_WORDS = {"yes", "ok", "okay", "sure", "attend", "confirm", "coming", "will",
                  "ആണ്", "हाँ", "हां", "ஆம்", "ہاں", "ঠিক", "हो", "ji", "haan"}
_DECLINE_WORDS = {"no", "nope", "not", "can't", "cannot", "won't", "decline", "absent",
                  "ഇല്ല", "नहीं", "இல்லை", "نہیں", "না", "nahi", "nhi"}
_CALLBACK_WORDS = {"callback", "call back", "later", "busy", "now", "baad", "बाद"}
_STOP_WORDS = {"stop", "remove", "opt out", "unsubscribe", "don't call", "band karo"}


# ── Keyword fallback (zero deps, always runs last) ─────────────────────────────

def _keyword_classify(text: str) -> tuple[str, str]:
    """Returns (intent, method)."""
    t = text.lower().strip()
    words = set(t.split())
    if words & _CONFIRM_WORDS:
        return "confirm", "keyword"
    if words & _STOP_WORDS:
        return "stop_calling", "keyword"
    if words & _DECLINE_WORDS:
        return "decline", "keyword"
    if words & _CALLBACK_WORDS:
        return "call_later", "keyword"
    return "unclear", "keyword"


# ── Own AI service (Sarvam + MuRIL) ──────────────────────────────────────────

async def _try_own_ai(text: str, audio: Optional[bytes], language: str) -> tuple[str, float, str] | None:
    """Try the internal AI service. Returns (intent, confidence, method) or None."""
    try:
        from app.ai_client.client import get_ai_client, FakeAIClient
        ai = get_ai_client()
        if isinstance(ai, FakeAIClient):
            return None  # Not a real AI service

        if audio:
            result = await ai.speech_intent(
                audio_bytes=audio,
                language=language,
                allowed_intents=ALLOWED_INTENTS,
            )
            return result.intent, result.confidence, f"sarvam_stt+{result.source or 'muril'}"
        else:
            result = await ai.intent(
                text=text,
                language=language,
                allowed_intents=ALLOWED_INTENTS,
            )
            return result.intent, result.confidence, result.source or "muril"
    except Exception as exc:
        log.warning("intent_own_ai_failed", error=str(exc))
        return None


# ── Gemini fallback ────────────────────────────────────────────────────────────

def _build_prompt(text: str) -> str:
    return (
        "Classify this short phone call utterance into exactly one intent.\n"
        f"Allowed: confirm, decline, reschedule, call_later, stop_calling, unclear\n"
        "Reply ONLY with valid JSON: {\"intent\": \"<one>\", \"confidence\": <0..1>}\n"
        f"Utterance: {text}"
    )


async def _try_gemini(text: str) -> tuple[str, float, str] | None:
    if not settings.gemini_api_key:
        return None
    try:
        prompt = _build_prompt(text)
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"gemini-1.5-flash:generateContent?key={settings.gemini_api_key}",
                json={"contents": [{"parts": [{"text": prompt}]}]},
            )
            resp.raise_for_status()
            content = (
                resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                .strip().strip("```json").strip("```").strip()
            )
            parsed = json.loads(content)
            intent = parsed.get("intent", "unclear")
            conf = float(parsed.get("confidence", 0.5))
            if intent not in ALLOWED_INTENTS:
                intent = "unclear"
            return intent, min(max(conf, 0.0), 1.0), "gemini"
    except Exception as exc:
        log.warning("intent_gemini_failed", error=str(exc))
        return None


# ── Groq fallback ──────────────────────────────────────────────────────────────

async def _try_groq(text: str) -> tuple[str, float, str] | None:
    if not settings.groq_api_key:
        return None
    try:
        prompt = _build_prompt(text)
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
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
                .strip().strip("```json").strip("```").strip()
            )
            parsed = json.loads(content)
            intent = parsed.get("intent", "unclear")
            conf = float(parsed.get("confidence", 0.5))
            if intent not in ALLOWED_INTENTS:
                intent = "unclear"
            return intent, min(max(conf, 0.0), 1.0), "groq"
    except Exception as exc:
        log.warning("intent_groq_failed", error=str(exc))
        return None


# ── Public interface ───────────────────────────────────────────────────────────

async def classify_intent(
    text: str = "",
    audio: Optional[bytes] = None,
    language: str = "en",
) -> tuple[str, float, str]:
    """
    Classify intent from text and/or audio using cascading providers.

    Returns:
        (intent, confidence, method)
        method describes which provider produced the result.

    Cascade:
        1. Own AI service (Sarvam STT + MuRIL intent)
        2. Gemini 1.5 Flash
        3. Groq LLaMA-3
        4. Keyword rules (always succeeds)
    """
    # 1. Own AI
    if text or audio:
        result = await _try_own_ai(text, audio, language)
        if result and result[0] != "unclear":
            log.info("intent_classified", method=result[2], intent=result[0])
            return result

    # 2. Gemini
    if text:
        result = await _try_gemini(text)
        if result and result[0] != "unclear":
            log.info("intent_classified", method=result[2], intent=result[0])
            return result

    # 3. Groq
    if text:
        result = await _try_groq(text)
        if result and result[0] != "unclear":
            log.info("intent_classified", method=result[2], intent=result[0])
            return result

    # 4. Keyword fallback (always runs)
    intent, method = _keyword_classify(text)
    confidence = 0.7 if intent != "unclear" else 0.0
    log.info("intent_classified", method=method, intent=intent)
    return intent, confidence, method
