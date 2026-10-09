#!/usr/bin/env python3
"""Run one voice path: prompt -> translate -> TTS -> speech-intent -> ack choice.

Live requests go only to the local AI service.  The service reads
SARVAM_API_KEY itself; this script reads AI_INTERNAL_TOKEN only and never logs
it.  ``--dry-run`` performs no HTTP requests and is suitable before keys exist.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
import time
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIO = ROOT / "fixtures" / "audio" / "yes_en.wav"
ALLOWED_INTENTS = ("confirm", "decline", "reschedule", "call_later", "stop_calling", "unclear")
ACK_BY_INTENT = {
    "confirm": "ack_confirm",
    "decline": "ack_decline",
    "reschedule": "ack_reschedule",
    "call_later": "ack_call_later",
    "stop_calling": "ack_stop",
    "unclear": "ack_unclear",
}
MIME_TYPES = {
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".mp3": "audio/mpeg",
    ".ogg": "audio/ogg",
    ".opus": "audio/ogg",
    ".webm": "audio/webm",
}


def audio_mime_type(path: Path) -> str:
    """Return an upload type for all formats supported by the fixture workflow."""
    try:
        return MIME_TYPES[path.suffix.lower()]
    except KeyError as exc:
        supported = ", ".join(sorted(MIME_TYPES))
        raise ValueError(f"unsupported audio extension {path.suffix!r}; supported: {supported}") from exc


def _headers() -> dict[str, str]:
    token = os.getenv("AI_INTERNAL_TOKEN")
    if not token:
        raise RuntimeError("AI_INTERNAL_TOKEN is required for a live run")
    return {"X-Internal-Token": token}


def _stage(name: str, started: float, detail: str) -> None:
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    print(f"{name}: {elapsed_ms} ms — {detail}")


async def run(
    base_url: str,
    audio_path: Path,
    language: str,
    prompt: str,
    *,
    dry_run: bool,
) -> int:
    if not audio_path.is_file():
        raise FileNotFoundError(f"recorded reply file does not exist: {audio_path}")
    mime_type = audio_mime_type(audio_path)
    ffmpeg_present = bool(shutil.which("ffmpeg"))

    if dry_run:
        print(f"translate: 0 ms — would translate prompt en -> {language}")
        print(f"tts: 0 ms — would synthesise translated prompt ({language})")
        print(
            f"speech-intent: 0 ms — would upload {audio_path.name} as {mime_type}; "
            f"ffmpeg available: {'yes' if ffmpeg_present else 'no'}"
        )
        print("acknowledgment: 0 ms — would choose ack from returned intent")
        return 0

    async with httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=60.0) as client:
        started = time.perf_counter()
        translation = await client.post(
            "/v1/translate",
            headers=_headers(),
            json={"segments": {"prompt": prompt}, "source_language": "en", "target_language": language},
        )
        translation.raise_for_status()
        translated_prompt = translation.json()["segments"]["prompt"]
        _stage("translate", started, f"{len(translated_prompt)} characters")

        started = time.perf_counter()
        tts = await client.post(
            "/v1/tts",
            headers=_headers(),
            json={"text": translated_prompt, "language": language},
        )
        tts.raise_for_status()
        _stage("tts", started, f"{len(tts.content)} audio bytes")

        started = time.perf_counter()
        reply = await client.post(
            "/v1/speech-intent",
            headers=_headers(),
            files={
                "audio": (audio_path.name, audio_path.read_bytes(), mime_type),
                "language": (None, language),
                "allowed_intents": (None, json.dumps(ALLOWED_INTENTS)),
            },
        )
        reply.raise_for_status()
        result = reply.json()
        _stage("speech-intent", started, f"{result['intent']} ({result['confidence']:.3f}, {result['source']})")

    intent = result["intent"]
    ack = ACK_BY_INTENT[intent]
    print(f"acknowledgment: 0 ms — {ack}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("AI_BASE_URL", "http://localhost:8200"))
    parser.add_argument("--audio", type=Path, default=DEFAULT_AUDIO, help="Recorded reply (wav/m4a/mp3/ogg/opus/webm)")
    parser.add_argument("--language", choices=("en", "hi", "ml", "ta"), default="en")
    parser.add_argument("--prompt", default="Please confirm whether you will attend the seminar.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    return asyncio.run(run(args.base_url, args.audio, args.language, args.prompt, dry_run=args.dry_run))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, RuntimeError, ValueError, httpx.HTTPError) as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
