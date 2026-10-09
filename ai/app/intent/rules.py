"""
Intent rules engine — Phase 1 first-pass classification.

Rules run before the ML model. They use phrase-matching with word boundaries
on normalised text. Confidence 0.95 on a clear single match, 0.0 on ambiguity.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from functools import lru_cache
from typing import Optional

import yaml
import structlog

from app.schemas import IntentLabel

log = structlog.get_logger()

NEGATION_TOKENS = {
    "not", "no", "never", "nahi", "nahin", "nahi", "mat", "illa",
    "illai", "varilla", "pattilla",
}
ALL_LABELS: list[IntentLabel] = [
    "confirm", "decline", "reschedule", "call_later", "stop_calling",
]


def _normalise(text: str) -> str:
    """Lowercase, NFC, strip punctuation, collapse whitespace, map digits."""
    text = unicodedata.normalize("NFC", text.lower())
    text = re.sub(r"[^\w\s]", " ", text)        # remove punctuation
    text = re.sub(r"\s+", " ", text).strip()
    return text


@lru_cache(maxsize=None)
def _load_lexicon(language: str) -> dict[str, list[str]]:
    """Load and cache lexicon YAML for a language. Falls back to English."""
    from app.config import settings
    lex_dir = Path(settings.lexicon_dir)
    path = lex_dir / f"{language}.yaml"
    if not path.exists():
        log.warning("lexicon_not_found", language=language, fallback="en")
        path = lex_dir / "en.yaml"
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _phrase_match(text: str, phrases: list[str]) -> bool:
    """Return True if any phrase appears as a whole-word match in text."""
    for phrase in phrases:
        phrase_norm = _normalise(phrase)
        # Word-boundary match: pad text so partial words don't match
        pattern = r"(?<!\w)" + re.escape(phrase_norm) + r"(?!\w)"
        if re.search(pattern, text):
            return True
    return False


def _strong_stop_calling_match(text: str, phrases: list[str]) -> bool:
    """Match multi-word opt-out phrases, excluding the weak bare ``stop`` cue."""
    strong_phrases = [
        phrase for phrase in phrases
        if len(_normalise(phrase).split()) >= 2
    ]
    return _phrase_match(text, strong_phrases)


def classify(
    text: str,
    language: str,
    allowed_intents: list[IntentLabel] | None = None,
) -> tuple[IntentLabel, float]:
    """
    Apply lexicon rules.

    Returns:
        (intent, confidence)
        confidence == 0.95  → clear single match, caller may return immediately
        confidence == 0.0   → ambiguous or no match, hand off to model
        confidence == 0.3   → empty / very short text → unclear
    """
    if not text or len(text.strip()) < 2:
        return "unclear", 0.3

    allowed = set(allowed_intents) if allowed_intents else set(ALL_LABELS)
    normalised = _normalise(text)

    try:
        lexicon = _load_lexicon(language)
    except Exception as exc:
        log.error("lexicon_load_error", language=language, error=str(exc))
        return "unclear", 0.0

    matched: list[IntentLabel] = []

    for label in ALL_LABELS:
        if label not in allowed:
            continue
        phrases = lexicon.get(label, [])
        if _phrase_match(normalised, [_normalise(p) for p in phrases]):
            matched.append(label)

    # Explicit multi-word opt-out language wins over weak cues such as
    # "busy", "no", "later", or a bare "stop". A bare "stop" remains
    # ambiguous when another label also matches.
    if "stop_calling" in allowed and _strong_stop_calling_match(
        normalised, lexicon.get("stop_calling", [])
    ):
        return "stop_calling", 0.95

    if len(matched) == 1:
        # Negation check: if the text contains a strong negation word and the
        # matched intent is confirm, re-evaluate
        if matched[0] == "confirm" and any(
            n in normalised.split() for n in NEGATION_TOKENS
        ):
            if "decline" in allowed:
                return "decline", 0.95
        return matched[0], 0.95

    if len(matched) == 0:
        # No match — hand off to model
        return "unclear", 0.0

    # Multiple conflicting intents — ambiguous, let model decide
    return "unclear", 0.0
