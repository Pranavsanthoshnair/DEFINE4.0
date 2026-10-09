"""Tests for the local, credential-free e2e smoke helpers."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "e2e_smoke.py"
spec = importlib.util.spec_from_file_location("e2e_smoke", SCRIPT)
e2e_smoke = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = e2e_smoke
spec.loader.exec_module(e2e_smoke)


@pytest.mark.parametrize(
    ("suffix", "content_type"),
    [
        (".wav", "audio/wav"),
        (".m4a", "audio/mp4"),
        (".mp3", "audio/mpeg"),
        (".ogg", "audio/ogg"),
        (".opus", "audio/ogg"),
        (".webm", "audio/webm"),
    ],
)
def test_audio_formats_are_supported(suffix: str, content_type: str) -> None:
    assert e2e_smoke.audio_mime_type(Path("reply" + suffix)) == content_type


def test_acknowledgement_choice_covers_the_fixed_intent_label_order() -> None:
    assert tuple(e2e_smoke.ACK_BY_INTENT) == e2e_smoke.ALLOWED_INTENTS
