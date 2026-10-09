"""
Sarvam provider integration tests — all Sarvam HTTP calls are mocked.
No live credentials required for these tests.

Run with:
    pytest tests/test_sarvam.py -v

For a real end-to-end test with live credentials:
    pytest tests/test_sarvam.py::test_live_sarvam_stt -v -m integration --sarvam-key=<YOUR_KEY>
"""

from __future__ import annotations

import base64
import io
import json
import math
import struct
import wave
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Both test files import from app.main. The app singleton is already created
# with AI_STUB=true by test_contract.py. We patch settings per-test instead
# of flipping env vars at module level.
import os
os.environ.setdefault("AI_INTERNAL_TOKEN", "test-token-sarvam")
os.environ.setdefault("SARVAM_API_KEY", "test-sarvam-key-12345")

from app.main import app, create_app  # noqa: E402
from app.config import settings as _settings

TOKEN = "test-token-sarvam"
HEADERS = {"X-Internal-Token": TOKEN}

# Force the token to match (settings may already be loaded)
_settings.ai_internal_token = TOKEN  # type: ignore[assignment]


@pytest.fixture(scope="module")
def client():
    """TestClient with stub=False and Sarvam-mode settings patched in."""
    original_token = _settings.ai_internal_token
    original_stub = _settings.ai_stub
    original_key = _settings.sarvam_api_key
    original_stt_provider = _settings.stt_provider

    _settings.ai_stub = False  # type: ignore[assignment]
    _settings.sarvam_api_key = "test-sarvam-key-12345"  # type: ignore[assignment]
    _settings.stt_provider = "sarvam"  # type: ignore[assignment]
    _settings.ai_internal_token = TOKEN  # type: ignore[assignment]

    with TestClient(app) as c:
        yield c

    # Restore original values so test_contract.py still works
    _settings.ai_stub = original_stub  # type: ignore[assignment]
    _settings.sarvam_api_key = original_key  # type: ignore[assignment]
    _settings.stt_provider = original_stt_provider  # type: ignore[assignment]
    _settings.ai_internal_token = original_token  # type: ignore[assignment]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_wav_bytes(duration_sec: float = 0.5, sample_rate: int = 8000) -> bytes:
    n = int(sample_rate * duration_sec)
    samples = [int(32767 * math.sin(2 * math.pi * 440 * i / sample_rate)) for i in range(n)]
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{n}h", *samples))
    return buf.getvalue()


def _make_stub_sarvam_client(
    transcript: str = "yes I will come",
    language_code: str = "en-IN",
    language_prob: float = 0.98,
    translated_text: str = "[translated]",
    tts_audio_b64: str | None = None,
) -> MagicMock:
    """Build a mock SarvamAI client with all methods patched."""
    if tts_audio_b64 is None:
        # Minimal valid WAV bytes, base64 encoded
        wav = _make_wav_bytes(0.1)
        tts_audio_b64 = base64.b64encode(wav).decode()

    mock_client = MagicMock()

    # STT
    stt_response = MagicMock()
    stt_response.transcript = transcript
    stt_response.language_code = language_code
    stt_response.language_probability = language_prob
    mock_client.speech_to_text.transcribe.return_value = stt_response

    # Translate
    trans_response = MagicMock()
    trans_response.translated_text = translated_text
    mock_client.text.translate.return_value = trans_response

    # TTS
    tts_response = MagicMock()
    tts_response.audios = [tts_audio_b64]
    mock_client.text_to_speech.convert.return_value = tts_response

    return mock_client


# ── /v1/stt mocked tests ──────────────────────────────────────────────────────

class TestSarvamSTT:
    def test_configured_output_mode_is_passed_to_sarvam(self, client):
        mock = _make_stub_sarvam_client(transcript="नमस्ते", language_code="hi-IN")
        with patch("app.providers.sarvam._client", mock), patch(
            "app.providers.sarvam._stt_mode_for", return_value="codemix"
        ):
            r = client.post(
                "/v1/stt",
                files={"audio": ("hi.wav", _make_wav_bytes(), "audio/wav")},
                data={"language": "hi"},
                headers=HEADERS,
            )
        assert r.status_code == 200
        assert mock.speech_to_text.transcribe.call_args.kwargs["mode"] == "codemix"

    def test_successful_transcription_english(self, client):
        mock = _make_stub_sarvam_client(transcript="yes I will come", language_code="en-IN")
        with patch("app.providers.sarvam._client", mock):
            wav = _make_wav_bytes()
            r = client.post(
                "/v1/stt",
                files={"audio": ("yes_en.wav", wav, "audio/wav")},
                headers=HEADERS,
            )
        assert r.status_code == 200
        data = r.json()
        assert data["text"] == "yes I will come"
        assert data["language"] == "en"
        assert data["no_speech"] is False
        assert data["model"] == "saaras:v4"
        assert isinstance(data["confidence"], float)
        assert isinstance(data["latency_ms"], int)

    def test_successful_transcription_malayalam(self, client):
        mock = _make_stub_sarvam_client(
            transcript="അതെ ഞാൻ വരാം",
            language_code="ml-IN",
            language_prob=0.95,
        )
        with patch("app.providers.sarvam._client", mock):
            wav = _make_wav_bytes()
            r = client.post(
                "/v1/stt",
                files={"audio": ("ml_yes.wav", wav, "audio/wav")},
                data={"language": "ml"},
                headers=HEADERS,
            )
        assert r.status_code == 200
        data = r.json()
        assert data["language"] == "ml"
        assert data["no_speech"] is False
        assert "അതെ" in data["text"]

    def test_empty_transcript_returns_no_speech(self, client):
        """Empty transcript from Sarvam → no_speech=True."""
        mock = _make_stub_sarvam_client(transcript="", language_code="hi-IN")
        with patch("app.providers.sarvam._client", mock):
            wav = _make_wav_bytes()
            r = client.post(
                "/v1/stt",
                files={"audio": ("silence.wav", wav, "audio/wav")},
                data={"language": "hi"},
                headers=HEADERS,
            )
        assert r.status_code == 200
        data = r.json()
        assert data["no_speech"] is True
        assert data["text"] == ""
        # confidence must be 0.0 when there is no speech
        assert data["confidence"] == 0.0

    def test_unsupported_language_returns_400(self, client):
        wav = _make_wav_bytes()
        r = client.post(
            "/v1/stt",
            files={"audio": ("audio.wav", wav, "audio/wav")},
            data={"language": "zz"},
            headers=HEADERS,
        )
        assert r.status_code == 400

    def test_audio_too_large_returns_413(self, client):
        large_data = b"0" * (6 * 1024 * 1024)
        r = client.post(
            "/v1/stt",
            files={"audio": ("big.wav", large_data, "audio/wav")},
            headers=HEADERS,
        )
        assert r.status_code == 413

    def test_provider_rate_limit_returns_429(self, client):
        mock = MagicMock()
        mock.speech_to_text.transcribe.side_effect = Exception("429 rate_limit_exceeded")
        with patch("app.providers.sarvam._client", mock):
            wav = _make_wav_bytes()
            r = client.post(
                "/v1/stt",
                files={"audio": ("audio.wav", wav, "audio/wav")},
                headers=HEADERS,
            )
        assert r.status_code == 429
        data = r.json()
        detail = data.get("detail") or data
        assert isinstance(detail, dict)

    def test_provider_timeout_returns_504(self, client):
        mock = MagicMock()
        mock.speech_to_text.transcribe.side_effect = Exception("timed out")
        with patch("app.providers.sarvam._client", mock):
            wav = _make_wav_bytes()
            r = client.post(
                "/v1/stt",
                files={"audio": ("audio.wav", wav, "audio/wav")},
                headers=HEADERS,
            )
        assert r.status_code == 504

    def test_invalid_audio_returns_422(self, client):
        mock = MagicMock()
        mock.speech_to_text.transcribe.side_effect = Exception("422 invalid input")
        with patch("app.providers.sarvam._client", mock):
            r = client.post(
                "/v1/stt",
                files={"audio": ("bad.wav", b"notaudio", "audio/wav")},
                headers=HEADERS,
            )
        assert r.status_code == 422

    def test_missing_api_key_returns_503(self, client):
        """Missing key → is_configured() false → 503 during lifespan;
        or SarvamError(missing_credentials) → mapped to 503."""
        import app.providers.sarvam as sarvam_mod
        original = sarvam_mod._client
        sarvam_mod._client = None

        from app.config import settings as cfg
        original_key = cfg.sarvam_api_key
        cfg.sarvam_api_key = ""  # type: ignore[assignment]

        try:
            wav = _make_wav_bytes()
            r = client.post(
                "/v1/stt",
                files={"audio": ("audio.wav", wav, "audio/wav")},
                headers=HEADERS,
            )
            assert r.status_code == 503
        finally:
            sarvam_mod._client = original
            cfg.sarvam_api_key = original_key  # type: ignore[assignment]

    def test_response_schema_fields_present(self, client):
        """Verify all contract-required fields are present."""
        mock = _make_stub_sarvam_client()
        with patch("app.providers.sarvam._client", mock):
            wav = _make_wav_bytes()
            r = client.post(
                "/v1/stt",
                files={"audio": ("audio.wav", wav, "audio/wav")},
                headers=HEADERS,
            )
        assert r.status_code == 200
        data = r.json()
        for field in ("text", "language", "confidence", "duration_ms",
                      "latency_ms", "model", "truncated", "no_speech"):
            assert field in data, f"Missing field: {field}"


# ── /v1/intent mocked tests ───────────────────────────────────────────────────

class TestIntentClassification:
    """Intent runs on rules engine (no Sarvam call needed)."""

    def test_confirm_intent_english(self, client):
        r = client.post(
            "/v1/intent",
            json={"text": "yes I will come", "language": "en"},
            headers=HEADERS,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["intent"] == "confirm"
        assert data["confidence"] >= 0.8
        assert data["source"] == "rules"

    def test_decline_intent_hindi(self, client):
        # "nahi" is a decline keyword in the lexicon; "aaunga" is a filler
        r = client.post(
            "/v1/intent",
            json={"text": "nahi", "language": "hi"},
            headers=HEADERS,
        )
        assert r.status_code == 200
        assert r.json()["intent"] == "decline"

    def test_stop_calling_intent(self, client):
        r = client.post(
            "/v1/intent",
            json={"text": "stop calling me please", "language": "en"},
            headers=HEADERS,
        )
        assert r.status_code == 200
        assert r.json()["intent"] == "stop_calling"

    def test_call_later_intent_malayalam(self, client):
        r = client.post(
            "/v1/intent",
            json={"text": "pinne call cheyyu", "language": "ml"},
            headers=HEADERS,
        )
        assert r.status_code == 200
        assert r.json()["intent"] == "call_later"

    def test_unclear_for_empty_text(self, client):
        r = client.post(
            "/v1/intent",
            json={"text": "", "language": "en"},
            headers=HEADERS,
        )
        assert r.status_code == 200
        assert r.json()["intent"] == "unclear"

    def test_allowed_intents_filter(self, client):
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


# ── /v1/speech-intent mocked tests ───────────────────────────────────────────

class TestSpeechIntent:
    def test_combined_stt_and_intent(self, client):
        mock = _make_stub_sarvam_client(transcript="yes I will come", language_code="en-IN")
        with patch("app.providers.sarvam._client", mock):
            wav = _make_wav_bytes()
            r = client.post(
                "/v1/speech-intent",
                files={"audio": ("yes.wav", wav, "audio/wav")},
                headers=HEADERS,
            )
        assert r.status_code == 200
        data = r.json()
        assert data["text"] == "yes I will come"
        assert data["intent"] == "confirm"
        assert data["no_speech"] is False
        for f in ("text", "language", "intent", "confidence", "source",
                  "stt_model", "latency_ms", "no_speech"):
            assert f in data

    def test_no_speech_returns_unclear(self, client):
        """Empty Sarvam transcript → no_speech=True → intent=unclear, conf=0."""
        mock = _make_stub_sarvam_client(transcript="", language_code="hi-IN")
        with patch("app.providers.sarvam._client", mock):
            wav = _make_wav_bytes()
            r = client.post(
                "/v1/speech-intent",
                files={"audio": ("silence.wav", wav, "audio/wav")},
                headers=HEADERS,
            )
        assert r.status_code == 200
        data = r.json()
        assert data["no_speech"] is True
        assert data["intent"] == "unclear"
        assert data["confidence"] == 0.0

    def test_decline_malayalam(self, client):
        # "illa" is a known decline keyword in the intent rules
        mock = _make_stub_sarvam_client(transcript="illa", language_code="ml-IN")
        with patch("app.providers.sarvam._client", mock):
            wav = _make_wav_bytes()
            r = client.post(
                "/v1/speech-intent",
                files={"audio": ("no_ml.wav", wav, "audio/wav")},
                data={"language": "ml"},
                headers=HEADERS,
            )
        assert r.status_code == 200
        assert r.json()["intent"] == "decline"


# ── /v1/translate mocked tests ────────────────────────────────────────────────

class TestTranslate:
    def test_basic_translation(self, client):
        mock = _make_stub_sarvam_client(translated_text="हाँ, हम कल मिलेंगे ⟦0⟧ पर")
        with patch("app.providers.sarvam._client", mock):
            r = client.post(
                "/v1/translate",
                json={
                    "segments": {"greeting": "Yes, we will meet at {event_name}"},
                    "source_language": "en",
                    "target_language": "hi",
                },
                headers=HEADERS,
            )
        assert r.status_code == 200
        data = r.json()
        assert "segments" in data
        assert "model" in data
        assert "greeting" in data["segments"]

    def test_too_many_segments_returns_400(self, client):
        r = client.post(
            "/v1/translate",
            json={
                "segments": {f"seg_{i}": "hello" for i in range(21)},
                "source_language": "en",
                "target_language": "hi",
            },
            headers=HEADERS,
        )
        assert r.status_code == 400

    def test_provider_error_during_translate(self, client):
        mock = MagicMock()
        mock.text.translate.side_effect = Exception("502 provider failure")
        with patch("app.providers.sarvam._client", mock):
            r = client.post(
                "/v1/translate",
                json={
                    "segments": {"g": "Hello"},
                    "source_language": "en",
                    "target_language": "hi",
                },
                headers=HEADERS,
            )
        assert r.status_code in (502, 422)


# ── /v1/tts mocked tests ──────────────────────────────────────────────────────

class TestTTS:
    def test_tts_returns_wav(self, client):
        wav = _make_wav_bytes(0.1, 8000)
        mock = _make_stub_sarvam_client(tts_audio_b64=base64.b64encode(wav).decode())
        with patch("app.providers.sarvam._client", mock):
            r = client.post(
                "/v1/tts",
                json={"text": "Hello, please attend the event.", "language": "en"},
                headers=HEADERS,
            )
        assert r.status_code == 200
        assert r.headers["content-type"] == "audio/wav"
        assert "X-Duration-Ms" in r.headers
        assert "X-Tts-Model" in r.headers

    def test_tts_unsupported_language_returns_400(self, client):
        r = client.post(
            "/v1/tts",
            json={"text": "hello", "language": "zz"},
            headers=HEADERS,
        )
        assert r.status_code == 400

    def test_tts_text_too_long(self, client):
        # Pydantic validates max_length=2000 at schema level → 422
        r = client.post(
            "/v1/tts",
            json={"text": "x" * 2001, "language": "en"},
            headers=HEADERS,
        )
        assert r.status_code == 422


# ── /healthz tests ────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_public_no_auth(self, client):
        r = client.get("/healthz")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] in ("ok", "degraded")
        for key in ("stt", "intent", "translate", "tts"):
            assert key in data["models"]
            assert data["models"][key] in ("loaded", "stub", "unavailable")

    def test_health_does_not_expose_api_key(self, client):
        r = client.get("/healthz")
        body = r.text
        assert "sarvam" not in body.lower() or "api_key" not in body.lower()
        assert "test-sarvam-key" not in body


# ── Optional live integration test ────────────────────────────────────────────


@pytest.mark.integration
def test_live_sarvam_stt(request, tmp_path):
    """
    REAL Sarvam API call — only runs with -m integration --sarvam-key=<key>.
    Requires a valid API key and internet access.
    """
    key = request.config.getoption("--sarvam-key", default=None)
    if not key:
        pytest.skip("Pass --sarvam-key=<KEY> to run this test")

    import asyncio
    import app.providers.sarvam as sarvam_mod
    from app.config import settings as cfg
    cfg.sarvam_api_key = key  # type: ignore[assignment]
    sarvam_mod._client = None   # force re-init with real key

    wav = _make_wav_bytes(1.0, 16000)  # 1s 16kHz WAV
    result = asyncio.run(sarvam_mod.transcribe(wav, "test.wav", language="en"))

    assert isinstance(result.transcript, str)
    assert result.language in ("en", "hi", "ml", "ta", "te", "kn", "bn", "mr", "gu")
    print(f"\n[LIVE] transcript='{result.transcript}' language={result.language}")

    sarvam_mod._client = None   # reset
    cfg.sarvam_api_key = ""     # type: ignore[assignment]
