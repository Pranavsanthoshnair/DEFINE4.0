"""
Placeholder protection for translation.

Replaces {key} variables with safe tokens ⟦0⟧, ⟦1⟧... before MT,
restores them after. Validates the full set is preserved.
"""

from __future__ import annotations

import re


_PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")
# Token format: ⟦N⟧ — unlikely to appear in natural text or be split by MT
_TOKEN_FMT = "⟦{idx}⟧"
_TOKEN_RE = re.compile(r"⟦(\d+)⟧")


def protect(text: str) -> tuple[str, dict[str, str]]:
    """
    Replace {key} placeholders with ⟦N⟧ tokens.

    Returns:
        (protected_text, mapping of token -> original_placeholder)
    """
    keys = _PLACEHOLDER_RE.findall(text)
    mapping: dict[str, str] = {}

    for idx, key in enumerate(keys):
        token = _TOKEN_FMT.format(idx=idx)
        original = f"{{{key}}}"
        # Only first occurrence; preserve order
        if original not in [v for v in mapping.values()]:
            mapping[token] = original

    protected = text
    for token, original in mapping.items():
        protected = protected.replace(original, token, 1)

    return protected, mapping


def restore(text: str, mapping: dict[str, str]) -> str:
    """
    Restore ⟦N⟧ tokens back to {key} placeholders.
    """
    for token, original in mapping.items():
        text = text.replace(token, original)
    return text


def validate_placeholders(
    original: str, translated: str, mapping: dict[str, str]
) -> list[str]:
    """
    Return a list of placeholder keys that are missing from translated text.
    Empty list means all placeholders were preserved.
    """
    missing = []
    for token in mapping:
        if token not in translated:
            missing.append(mapping[token])
    return missing


def protect_segments(segments: dict[str, str]) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    """
    Protect all segments. Returns (protected_segments, per_segment_mapping).
    """
    protected: dict[str, str] = {}
    mappings: dict[str, dict[str, str]] = {}
    for key, text in segments.items():
        p, m = protect(text)
        protected[key] = p
        mappings[key] = m
    return protected, mappings


def restore_segments(
    segments: dict[str, str],
    mappings: dict[str, dict[str, str]],
) -> dict[str, str]:
    return {key: restore(text, mappings.get(key, {})) for key, text in segments.items()}


def validate_segments(
    original_segments: dict[str, str],
    translated_segments: dict[str, str],
    mappings: dict[str, dict[str, str]],
) -> dict[str, list[str]]:
    """
    Returns a dict of {segment_key: [missing_placeholder, ...]} for any issues.
    """
    errors: dict[str, list[str]] = {}
    for key, protected_orig in original_segments.items():
        translated = translated_segments.get(key, "")
        missing = validate_placeholders(protected_orig, translated, mappings.get(key, {}))
        if missing:
            errors[key] = missing
    return errors
