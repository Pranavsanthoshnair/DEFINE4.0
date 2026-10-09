#!/usr/bin/env python3
"""Exercise the seminar translation and TTS APIs without exposing credentials.

The AI service owns SARVAM_API_KEY.  This client only reads AI_BASE_URL and
AI_INTERNAL_TOKEN from its environment, and never prints either value.

Usage:
    python scripts/tts_check.py --dry-run
    python scripts/tts_check.py --base-url http://localhost:8200
"""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import math
import os
import sys
import wave
from dataclasses import dataclass
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[1]
PRESET_PATH = ROOT / "fixtures" / "template_seminar.json"
OUTPUT_DIR = ROOT / "ai" / "tests" / "tts_out"
LANGUAGES = ("en", "hi", "ml", "ta")
SEGMENT_KEYS = (
    "prompt",
    "reprompt",
    "ack_confirm",
    "ack_decline",
    "ack_reschedule",
    "ack_call_later",
)
PLACEHOLDER_VALUES = {
    "org_name": "Demo Institute",
    "event_name": "AI Workshop",
    "date": "12 October",
    "venue": "Main Auditorium",
}


@dataclass(frozen=True)
class WavCheck:
    ok: bool
    duration_ms: int
    rms_dbfs: float | None
    errors: tuple[str, ...]


def seminar_segments() -> dict[str, str]:
    """Load exactly the prompt, reprompt, and four ordinary acknowledgements."""
    preset = json.loads(PRESET_PATH.read_text(encoding="utf-8"))
    script = preset["script"]
    return {key: script[key] for key in SEGMENT_KEYS}


def fill_placeholders(text: str) -> str:
    for name, value in PLACEHOLDER_VALUES.items():
        text = text.replace("{" + name + "}", value)
    return text


def check_wav(data: bytes) -> WavCheck:
    """Validate the contract WAV container and report an RMS loudness proxy.

    RMS dBFS is intentionally reported as a proxy: checking integrated LUFS
    requires an EBU R128 meter.  The range below catches silent, clipped, and
    obviously unnormalised output without claiming a precise LUFS measurement.
    """
    errors: list[str] = []
    duration_ms = 0
    rms_dbfs: float | None = None
    try:
        with wave.open(io.BytesIO(data), "rb") as stream:
            channels = stream.getnchannels()
            sample_width = stream.getsampwidth()
            sample_rate = stream.getframerate()
            frames = stream.getnframes()
            compression = stream.getcomptype()
            pcm = stream.readframes(frames)
    except (wave.Error, EOFError) as exc:
        return WavCheck(False, 0, None, (f"invalid WAV: {exc}",))

    duration_ms = round(frames / sample_rate * 1000) if sample_rate else 0
    if channels != 1:
        errors.append(f"expected mono, got {channels} channels")
    if sample_rate != 8000:
        errors.append(f"expected 8000 Hz, got {sample_rate} Hz")
    if sample_width != 2:
        errors.append(f"expected PCM16 (2 bytes), got {sample_width} bytes")
    if compression != "NONE":
        errors.append(f"expected uncompressed PCM, got {compression}")
    if not 200 <= duration_ms <= 60_000:
        errors.append(f"duration {duration_ms} ms is outside the 200–60000 ms sanity range")

    if sample_width == 2 and pcm:
        samples = memoryview(pcm).cast("h")
        mean_square = sum(sample * sample for sample in samples) / len(samples)
        if mean_square == 0:
            errors.append("audio is silent; cannot be loudness normalised")
        else:
            rms_dbfs = 20 * math.log10(math.sqrt(mean_square) / 32768)
            if not -30.0 <= rms_dbfs <= -8.0:
                errors.append(
                    f"RMS proxy {rms_dbfs:.1f} dBFS is outside the -30 to -8 dBFS sanity range"
                )

    return WavCheck(not errors, duration_ms, rms_dbfs, tuple(errors))


def _headers() -> dict[str, str]:
    token = os.getenv("AI_INTERNAL_TOKEN")
    if not token:
        raise RuntimeError("AI_INTERNAL_TOKEN is required for a live run")
    return {"X-Internal-Token": token}


async def run(base_url: str, *, dry_run: bool) -> int:
    segments = seminar_segments()
    if dry_run:
        for language in LANGUAGES:
            for key in SEGMENT_KEYS:
                print(f"DRY-RUN translate -> tts {language}/{key} -> {OUTPUT_DIR / f'{language}_{key}.wav'}")
        return 0

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    failures = 0
    async with httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=60.0) as client:
        for language in LANGUAGES:
            translate = await client.post(
                "/v1/translate",
                headers=_headers(),
                json={
                    "segments": segments,
                    "source_language": "en",
                    "target_language": language,
                },
            )
            if translate.is_error:
                print(f"FAIL translate {language}: HTTP {translate.status_code}", file=sys.stderr)
                failures += len(SEGMENT_KEYS)
                continue
            translated = translate.json().get("segments", {})
            for key, source in segments.items():
                text = translated.get(key, "")
                missing = [token for token in ("{org_name}", "{event_name}", "{date}", "{venue}") if token in source and token not in text]
                if missing:
                    print(f"FAIL translate {language}/{key}: lost placeholders {', '.join(missing)}", file=sys.stderr)
                    failures += 1
                    continue
                tts = await client.post(
                    "/v1/tts",
                    headers=_headers(),
                    json={"text": fill_placeholders(text), "language": language},
                )
                output = OUTPUT_DIR / f"{language}_{key}.wav"
                if tts.is_error:
                    print(f"FAIL tts {language}/{key}: HTTP {tts.status_code}", file=sys.stderr)
                    failures += 1
                    continue
                output.write_bytes(tts.content)
                result = check_wav(tts.content)
                detail = f"{result.duration_ms} ms, RMS proxy {result.rms_dbfs:.1f} dBFS" if result.rms_dbfs is not None else f"{result.duration_ms} ms"
                if result.ok:
                    print(f"PASS {language}/{key}: {detail}")
                else:
                    print(f"FAIL {language}/{key}: {detail}; {'; '.join(result.errors)}", file=sys.stderr)
                    failures += 1
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("AI_BASE_URL", "http://localhost:8200"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    return asyncio.run(run(args.base_url, dry_run=args.dry_run))


if __name__ == "__main__":
    raise SystemExit(main())
