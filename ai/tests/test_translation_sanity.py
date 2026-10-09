"""Tests for deterministic translation-sanity checks."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "translation_sanity.py"
spec = importlib.util.spec_from_file_location("translation_sanity", SCRIPT)
translation_sanity = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = translation_sanity
spec.loader.exec_module(translation_sanity)


def test_translation_sanity_accepts_hindi_script_and_preserved_token() -> None:
    failures = translation_sanity.check_segment(
        "Hello {event_name}", "नमस्ते {event_name}", "hi"
    )
    assert not failures


def test_translation_sanity_reports_missing_placeholder_and_target_script() -> None:
    failures = translation_sanity.check_segment(
        "Hello {event_name}", "Hello there", "ta"
    )
    assert any("protected tokens" in failure for failure in failures)
    assert any("target ta script" in failure for failure in failures)


def test_all_backend_presets_are_discovered() -> None:
    assert {"seminar", "clinic", "school", "payment"}.issubset(
        translation_sanity.load_presets()
    )
