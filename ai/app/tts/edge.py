"""
Edge-TTS synthesis engine.
Uses Microsoft Edge's neural TTS via the edge-tts library (requires internet).
Post-processes output to 8 kHz mono PCM16 WAV via ffmpeg.
"""

from __future__ import annotations

import asyncio
import io
import subprocess
import time

import structlog

log = structlog.get_logger()

# Verified edge-tts voice names per language (run `edge-tts --list-voices` to confirm)
VOICES: dict[str, str] = {
    "en": "en-IN-NeerjaNeural",
    "hi": "hi-IN-SwaraNeural",
    "ml": "ml-IN-SobhanaNeural",
    "ta": "ta-IN-PallaviNeural",
    "te": "te-IN-ShrutiNeural",
    "kn": "kn-IN-SapnaNeural",
    "bn": "bn-IN-TanishaaNeural",
    "mr": "mr-IN-AarohiNeural",
}

MAX_RETRIES = 3


def _text_cleanup(text: str, language: str) -> str:
    """Pre-TTS text cleaning: collapse whitespace, expand abbreviations."""
    import re
    text = re.sub(r"\s+", " ", text).strip()

    # Currency / unit expansion (language-aware)
    if language in ("en", "hi"):
        text = re.sub(r"\bRs\.?\s*(\d)", r"rupees \1", text)
        text = re.sub(r"\bINR\b", "rupees", text)

    return text


def _to_phone_wav(mp3_bytes: bytes) -> bytes:
    """Convert MP3 bytes to 8 kHz mono PCM16 WAV with loudness normalisation."""
    cmd = [
        "ffmpeg", "-y",
        "-i", "pipe:0",
        "-af", "loudnorm=I=-16:LRA=7:TP=-1.5,silenceremove=start_periods=1:start_silence=0.1",
        "-acodec", "pcm_s16le",
        "-ac", "1",
        "-ar", "8000",
        "-f", "wav",
        "pipe:1",
    ]
    try:
        result = subprocess.run(
            cmd, input=mp3_bytes,
            capture_output=True, timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg error: {result.stderr.decode()[:200]}")
        return result.stdout
    except FileNotFoundError:
        raise RuntimeError("ffmpeg not found — install it with: apt install ffmpeg")


async def synthesize(
    text: str,
    language: str,
    voice: str | None = None,
) -> tuple[bytes, int, str]:
    """
    Synthesise text using edge-tts.

    Returns:
        (wav_bytes_8khz_pcm16, duration_ms, model_name)
    Raises:
        RuntimeError on all retries exhausted
    """
    try:
        import edge_tts  # type: ignore[import]
    except ImportError:
        raise RuntimeError("edge-tts not installed — pip install edge-tts")

    selected_voice = voice or VOICES.get(language, VOICES["en"])
    clean_text = _text_cleanup(text, language)

    last_err: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            communicate = edge_tts.Communicate(clean_text, selected_voice)
            mp3_chunks: list[bytes] = []
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    mp3_chunks.append(chunk["data"])

            if not mp3_chunks:
                raise RuntimeError("edge-tts returned empty audio")

            mp3_bytes = b"".join(mp3_chunks)
            wav_bytes = await asyncio.get_event_loop().run_in_executor(
                None, _to_phone_wav, mp3_bytes
            )

            # Compute duration from WAV header
            import struct
            data_size = struct.unpack_from("<I", wav_bytes, 40)[0]
            sample_rate = 8000
            bytes_per_sample = 2
            duration_ms = int(data_size / (sample_rate * bytes_per_sample) * 1000)

            return wav_bytes, duration_ms, f"edge-tts/{selected_voice}"

        except Exception as exc:
            last_err = exc
            log.warning("edge_tts_retry", attempt=attempt + 1, error=str(exc))
            await asyncio.sleep(2 ** attempt)  # exponential backoff

    raise RuntimeError(f"edge-tts failed after {MAX_RETRIES} attempts: {last_err}")
