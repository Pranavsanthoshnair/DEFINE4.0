"""Unit checks for the credential-free portions of scripts/tts_check.py."""

from __future__ import annotations

import importlib.util
import io
import struct
import sys
import wave
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "tts_check.py"
spec = importlib.util.spec_from_file_location("tts_check", SCRIPT)
tts_check = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = tts_check
spec.loader.exec_module(tts_check)


def _wav(*, sample_rate: int = 8000, channels: int = 1) -> bytes:
    frames = struct.pack("<" + "h" * (sample_rate * channels), *([4000] * sample_rate * channels))
    output = io.BytesIO()
    with wave.open(output, "wb") as stream:
        stream.setnchannels(channels)
        stream.setsampwidth(2)
        stream.setframerate(sample_rate)
        stream.writeframes(frames)
    return output.getvalue()


def test_check_wav_accepts_contract_format() -> None:
    result = tts_check.check_wav(_wav())
    assert result.ok
    assert result.duration_ms == 1000


def test_check_wav_rejects_non_contract_sample_rate() -> None:
    result = tts_check.check_wav(_wav(sample_rate=16_000))
    assert not result.ok
    assert "8000 Hz" in " ".join(result.errors)


def test_seminar_segments_are_limited_to_requested_voice_check_steps() -> None:
    assert tuple(tts_check.seminar_segments()) == tts_check.SEGMENT_KEYS
