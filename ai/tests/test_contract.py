"""
Contract compliance tests for the AI service.
Tests run with AI_STUB=true — no models required, no network calls.
All response shapes must match CONTRACTS.md section 7 exactly.
"""

from __future__ import annotations

import io
import json
import math
import struct
import wave

import pytest
from fastapi.testclient import TestClient

# Force stub mode for tests
import os
os.environ["AI_STUB"] = "true"
os.environ["AI_INTERNAL_TOKEN"] = "test-token-12345"

from app.main import app  # noqa: E402
from app.config import settings as _settings

TOKEN = "test-token-12345"
HEADERS = {"X-Internal-Token": TOKEN}


@pytest.fixture(scope="module")
def client():
    # Patch settings directly (env var mutation alone doesn't reload pydantic-settings)
    _settings.ai_stub = True           # type: ignore[assignment]
    _settings.ai_internal_token = TOKEN  # type: ignore[assignment]
    with TestClient(app) as c:
        yield c


def _make_wav_bytes(duration_sec: float = 0.5) -> bytes:
    """Generate a minimal valid 8 kHz mono PCM16 WAV."""
    sample_rate = 8000
    n = int(sample_rate * duration_sec)
    samples = [int(32767 * math.sin(2 * math.pi * 440 * i / sample_rate)) for i in range(n)]
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{n}h", *samples))
    return buf.getvalue()


# ── /healthz ──────────────────────────────────────────────────────────────────

def test_healthz_public_no_auth(client):
    """Health endpoint must be public (no token needed)."""
    r = client.get("/healthz")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] in ("ok", "degraded")
    assert "models" in data
    for key in ("stt", "intent", "translate", "tts"):
        assert key in data["models"]
        assert data["models"][key] in ("loaded", "stub", "unavailable")


# ── Auth ──────────────────────────────────────────────────────────────────────

def test_missing_token_returns_401(client):
    r = client.post("/v1/intent", json={"text": "yes", "language": "en"})
    assert r.status_code == 401
    data = r.json()
    # FastAPI wraps HTTPException.detail under "detail" key
    detail = data.get("detail") or data
    if isinstance(detail, dict):
        assert detail.get("error", {}).get("code") == "unauthorized"


def test_wrong_token_returns_401(client):
    r = client.post(
        "/v1/intent",
        json={"text": "yes", "language": "en"},
        headers={"X-Internal-Token": "wrong"},
    )
    assert r.status_code == 401


# ── /v1/intent ────────────────────────────────────────────────────────────────

def test_intent_confirm(client):
    r = client.post(
        "/v1/intent",
        json={"text": "yes I will come", "language": "en"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["intent"] == "confirm"
    assert 0.0 <= data["confidence"] <= 1.0
    assert data["source"] in ("rules", "model", "llm")
    assert isinstance(data["latency_ms"], int)


def test_intent_decline_hindi(client):
    r = client.post(
        "/v1/intent",
        json={"text": "nahi", "language": "hi"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["intent"] == "decline"


def test_intent_unsupported_language(client):
    r = client.post(
        "/v1/intent",
        json={"text": "hello", "language": "zz"},
        headers=HEADERS,
    )
    assert r.status_code == 400
    data = r.json()
    detail = data.get("detail") or data
    if isinstance(detail, dict):
        assert detail.get("error", {}).get("code") == "unsupported_language"


def test_intent_allowed_intents_filtering(client):
    r = client.post(
        "/v1/intent",
        json={
            "text": "yes",
            "language": "en",
            "allowed_intents": ["confirm", "decline"],
        },
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["intent"] in ("confirm", "decline", "unclear")


# ── /v1/stt ───────────────────────────────────────────────────────────────────

def test_stt_stub_confirm(client):
    wav = _make_wav_bytes()
    r = client.post(
        "/v1/stt",
        files={"audio": ("yes.wav", wav, "audio/wav")},
        headers=HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert "text" in data
    assert "language" in data
    assert "confidence" in data
    assert "duration_ms" in data
    assert "latency_ms" in data
    assert "model" in data


def test_stt_stub_no_filename(client):
    wav = _make_wav_bytes()
    r = client.post(
        "/v1/stt",
        files={"audio": ("audio.wav", wav, "audio/wav")},
        headers=HEADERS,
    )
    assert r.status_code == 200


def test_stt_unsupported_language(client):
    wav = _make_wav_bytes()
    r = client.post(
        "/v1/stt",
        files={"audio": ("audio.wav", wav, "audio/wav")},
        data={"language": "zz"},
        headers=HEADERS,
    )
    assert r.status_code == 400


# ── /v1/speech-intent ─────────────────────────────────────────────────────────

def test_speech_intent_stub(client):
    wav = _make_wav_bytes()
    r = client.post(
        "/v1/speech-intent",
        files={"audio": ("yes.wav", wav, "audio/wav")},
        headers=HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert "text" in data
    assert "intent" in data
    assert "stt_model" in data
    assert "latency_ms" in data
    assert "no_speech" in data


def test_speech_intent_no_speech_stub(client):
    """Filename containing 'noise' → stub returns no_speech=True."""
    wav = _make_wav_bytes()
    r = client.post(
        "/v1/speech-intent",
        files={"audio": ("noise_background.wav", wav, "audio/wav")},
        headers=HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["no_speech"] is True
    assert data["intent"] == "unclear"
    assert data["confidence"] == 0.0


# ── /v1/translate ─────────────────────────────────────────────────────────────

def test_translate_stub_preserves_placeholders(client):
    r = client.post(
        "/v1/translate",
        json={
            "segments": {
                "greeting": "Hello from {org_name}.",
                "prompt": "Join {event_name} on {date}.",
            },
            "source_language": "en",
            "target_language": "hi",
        },
        headers=HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert "segments" in data
    assert "model" in data
    for key, text in data["segments"].items():
        # Stub prefixes with [hi] but placeholders must still be present
        assert "{org_name}" in text or "{event_name}" in text or "{date}" in text or "[hi]" in text


def test_translate_too_many_segments(client):
    segments = {f"seg_{i}": "Hello" for i in range(21)}
    r = client.post(
        "/v1/translate",
        json={"segments": segments, "source_language": "en", "target_language": "hi"},
        headers=HEADERS,
    )
    assert r.status_code == 400


# ── /v1/tts ───────────────────────────────────────────────────────────────────

def test_tts_stub_returns_wav(client):
    r = client.post(
        "/v1/tts",
        json={"text": "Hello, this is a test.", "language": "en"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/wav"
    assert "X-Duration-Ms" in r.headers
    assert "X-Tts-Model" in r.headers
    assert r.content[:4] == b"RIFF"  # WAV magic bytes


def test_tts_unsupported_language(client):
    r = client.post(
        "/v1/tts",
        json={"text": "hello", "language": "zz"},
        headers=HEADERS,
    )
    assert r.status_code == 400
