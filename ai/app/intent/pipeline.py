"""
Intent pipeline: rules → ONNX model → LLM fallback → unclear.
Contract section 3.5 order strictly followed.
"""

from __future__ import annotations

import time

import structlog

from app.config import settings
from app.intent.rules import classify as rules_classify
from app.schemas import IntentLabel, IntentSource

log = structlog.get_logger()

# Module-level singleton for the ONNX model (loaded in lifespan)
_onnx_model = None


def set_onnx_model(model) -> None:  # type: ignore[type-arg]
    global _onnx_model
    _onnx_model = model


async def run_pipeline(
    text: str,
    language: str,
    allowed_intents: list[IntentLabel] | None = None,
) -> tuple[IntentLabel, float, IntentSource, int]:
    """
    Full intent pipeline.

    Returns:
        (intent, confidence, source, latency_ms)
    """
    t0 = time.monotonic()

    if allowed_intents is None:
        allowed_intents = [
            "confirm", "decline", "reschedule",
            "call_later", "stop_calling", "unclear",
        ]

    # ── Step 1: Rules ──────────────────────────────────────────────────────────
    intent, conf = rules_classify(text, language, allowed_intents)

    if conf >= 0.9:
        latency_ms = int((time.monotonic() - t0) * 1000)
        log.info("intent_rules", intent=intent, conf=conf, latency_ms=latency_ms)
        return intent, conf, "rules", latency_ms

    # ── Step 2: ONNX model ────────────────────────────────────────────────────
    if _onnx_model is not None and _onnx_model.available:
        try:
            model_intent, model_conf = _onnx_model.predict(text, allowed_intents)
            if model_conf >= settings.intent_confidence_threshold:
                latency_ms = int((time.monotonic() - t0) * 1000)
                log.info(
                    "intent_model",
                    intent=model_intent, conf=model_conf,
                    latency_ms=latency_ms,
                )
                return model_intent, model_conf, "model", latency_ms
        except Exception as exc:
            log.error("intent_model_error", error=str(exc))

    # ── Step 3: LLM fallback ──────────────────────────────────────────────────
    if settings.llm_fallback != "none":
        from app.intent.llm_fallback import classify_with_llm
        llm_intent, llm_conf = await classify_with_llm(text, allowed_intents)
        if llm_intent != "unclear" or llm_conf > 0.0:
            latency_ms = int((time.monotonic() - t0) * 1000)
            log.info(
                "intent_llm",
                intent=llm_intent, conf=llm_conf,
                latency_ms=latency_ms,
            )
            return llm_intent, llm_conf, "llm", latency_ms

    # ── Step 4: unclear ───────────────────────────────────────────────────────
    latency_ms = int((time.monotonic() - t0) * 1000)
    log.info("intent_unclear", latency_ms=latency_ms, text_len=len(text))
    return "unclear", 0.0, "rules", latency_ms
