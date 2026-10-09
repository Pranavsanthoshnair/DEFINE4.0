"""
STT Benchmark — compare Sarvam Saaras v4 vs Groq Whisper Large v3 Turbo.

Usage:
    python stt_benchmark.py                   # uses built-in test tone
    python stt_benchmark.py path/to/call.wav  # use a real audio file
    python stt_benchmark.py path/to/call.wav --language hi

Reads SARVAM_API_KEY and GROQ_API_KEY from .env.
Never prints API keys.
"""

import asyncio
import io
import math
import os
import struct
import sys
import time
import wave

from dotenv import load_dotenv

load_dotenv()

# ── Validate keys ──────────────────────────────────────────────────────────────
sarvam_key = os.getenv("SARVAM_API_KEY", "")
groq_key   = os.getenv("GROQ_API_KEY", "")

if not sarvam_key:
    print("[WARN] SARVAM_API_KEY not set — Sarvam test will be skipped")
if not groq_key:
    print("[WARN] GROQ_API_KEY not set — Groq test will be skipped")
if not sarvam_key and not groq_key:
    raise SystemExit("No API keys found in .env — nothing to benchmark.")


# ── Audio loading ──────────────────────────────────────────────────────────────

def _make_test_wav(duration_sec: float = 2.0, sample_rate: int = 16000) -> bytes:
    """Generate a silent 16kHz WAV for testing connectivity (empty transcript expected)."""
    n = int(sample_rate * duration_sec)
    samples = [0] * n  # silence — Sarvam/Groq will return empty transcript
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{n}h", *samples))
    return buf.getvalue()


def _load_audio(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


# ── Provider calls ─────────────────────────────────────────────────────────────

async def _sarvam(audio: bytes, filename: str, language: str | None) -> dict:
    if not sarvam_key:
        return {"provider": "sarvam", "skipped": True}

    import httpx
    t0 = time.monotonic()
    try:
        r = httpx.post(
            "https://api.sarvam.ai/speech-to-text",
            headers={"api-subscription-key": sarvam_key},
            files={"file": (filename, audio, "audio/wav")},
            data={"model": "saaras:v4", "language_code": f"{language or 'en'}-IN"},
            timeout=30,
        )
        latency_ms = int((time.monotonic() - t0) * 1000)
        r.raise_for_status()
        data = r.json()
        return {
            "provider": "sarvam/saaras:v4",
            "transcript": data.get("transcript", ""),
            "language": data.get("language_code", ""),
            "latency_ms": latency_ms,
            "status": r.status_code,
            "error": None,
        }
    except Exception as exc:
        latency_ms = int((time.monotonic() - t0) * 1000)
        return {"provider": "sarvam/saaras:v4", "error": str(exc)[:80], "latency_ms": latency_ms}


async def _groq(audio: bytes, filename: str, language: str | None) -> dict:
    if not groq_key:
        return {"provider": "groq/whisper-large-v3-turbo", "skipped": True}

    from groq import Groq
    client = Groq(api_key=groq_key)
    buf = io.BytesIO(audio)
    buf.name = filename

    kwargs = {
        "file": (filename, buf, "audio/wav"),
        "model": "whisper-large-v3-turbo",
        "response_format": "verbose_json",
    }
    if language:
        kwargs["language"] = language

    t0 = time.monotonic()
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(
            None,
            lambda: client.audio.transcriptions.create(**kwargs)
        )
        latency_ms = int((time.monotonic() - t0) * 1000)
        lang = getattr(resp, "language", language or "")
        return {
            "provider": "groq/whisper-large-v3-turbo",
            "transcript": resp.text or "",
            "language": lang,
            "latency_ms": latency_ms,
            "status": 200,
            "error": None,
        }
    except Exception as exc:
        latency_ms = int((time.monotonic() - t0) * 1000)
        return {"provider": "groq/whisper-large-v3-turbo", "error": str(exc)[:80], "latency_ms": latency_ms}


# ── Main ───────────────────────────────────────────────────────────────────────

async def main():
    # Parse args
    audio_path = None
    language   = None
    args = sys.argv[1:]
    for arg in args:
        if arg.startswith("--language="):
            language = arg.split("=", 1)[1]
        elif arg.startswith("--language"):
            idx = args.index(arg)
            if idx + 1 < len(args):
                language = args[idx + 1]
        elif not arg.startswith("--"):
            audio_path = arg

    if audio_path:
        print(f"Loading audio: {audio_path}")
        audio = _load_audio(audio_path)
        filename = os.path.basename(audio_path)
    else:
        print("No audio file given — using 2-second silence test tone")
        audio = _make_test_wav()
        filename = "test_silence.wav"

    size_kb = len(audio) / 1024
    print(f"Audio: {filename} | {size_kb:.1f} KB | language hint: {language or 'auto-detect'}")
    print(f"\nRacing Sarvam and Groq concurrently...\n")

    # Race both providers
    sarvam_result, groq_result = await asyncio.gather(
        _sarvam(audio, filename, language),
        _groq(audio, filename, language),
    )

    results = [sarvam_result, groq_result]
    results.sort(key=lambda r: r.get("latency_ms", 99999))

    # ── Print results ──────────────────────────────────────────────────────────
    separator = "-" * 60
    print(separator)
    for r in results:
        if r.get("skipped"):
            print(f"  {r['provider']:<35} SKIPPED (no key)")
            continue
        if r.get("error"):
            print(f"  {r['provider']:<35} ERROR: {r['error']}")
            continue
        print(f"  {r['provider']:<35} {r['latency_ms']:>5} ms")
        print(f"    transcript : \"{r['transcript']}\"")
        print(f"    language   : {r['language']}")
    print(separator)

    # ── Winner ─────────────────────────────────────────────────────────────────
    ok = [r for r in results if not r.get("error") and not r.get("skipped")]
    if ok:
        winner = ok[0]  # already sorted by latency
        print(f"\nFASTER: {winner['provider']} ({winner['latency_ms']} ms)")
        print(f"\nTo lock in this provider, set in ai/.env:")
        if "sarvam" in winner["provider"]:
            print("  STT_PROVIDER=sarvam")
        else:
            print("  STT_PROVIDER=groq")
        print("\nOr keep STT_PROVIDER=auto to always race and return the fastest.")


if __name__ == "__main__":
    asyncio.run(main())
