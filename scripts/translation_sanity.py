#!/usr/bin/env python3
"""Check translated preset scripts against the AI translation contract.

The script calls the AI service, never the Sarvam API directly.  It therefore
uses AI_INTERNAL_TOKEN from the environment for live requests and never prints
credentials.  A dry run lists the exact requests without claiming a result.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[1]
PRESETS_DIR = ROOT / "backend" / "app" / "templates" / "presets"
TARGET_LANGUAGES = ("en", "hi", "ml", "ta")
SCRIPT_PATTERNS = {
    "en": re.compile(r"[A-Za-z]"),
    "hi": re.compile(r"[\u0900-\u097F]"),
    "ml": re.compile(r"[\u0D00-\u0D7F]"),
    "ta": re.compile(r"[\u0B80-\u0BFF]"),
}
PLACEHOLDER_RE = re.compile(r"\{[a-z_]+\}")


@dataclass(frozen=True)
class CheckResult:
    preset: str
    language: str
    segment: str
    ok: bool
    failures: tuple[str, ...]


def load_presets() -> dict[str, dict[str, str]]:
    """Return source-English scripts keyed by preset file stem."""
    presets: dict[str, dict[str, str]] = {}
    for path in sorted(PRESETS_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        presets[path.stem] = payload["script"]
    return presets


def _visible_length(text: str) -> int:
    return len(PLACEHOLDER_RE.sub("", text).strip())


def check_segment(source: str, translated: str, language: str) -> tuple[str, ...]:
    """Return contract failures for one translated segment."""
    failures: list[str] = []
    if not translated.strip():
        return ("empty translation",)

    tokens = PLACEHOLDER_RE.findall(source)
    missing_tokens = [token for token in tokens if token not in translated]
    if missing_tokens:
        failures.append("missing protected tokens: " + ", ".join(missing_tokens))

    source_length = _visible_length(source)
    translated_length = _visible_length(translated)
    ratio = translated_length / source_length if source_length else 1.0
    if not 0.5 <= ratio <= 3.0:
        failures.append(f"length ratio {ratio:.2f} is outside 0.50–3.00")

    pattern = SCRIPT_PATTERNS[language]
    if not pattern.search(PLACEHOLDER_RE.sub("", translated)):
        failures.append(f"target {language} script is absent")
    return tuple(failures)


def _headers() -> dict[str, str]:
    token = os.getenv("AI_INTERNAL_TOKEN")
    if not token:
        raise RuntimeError("AI_INTERNAL_TOKEN is required for a live run")
    return {"X-Internal-Token": token}


async def run(base_url: str, *, dry_run: bool, output: Path | None) -> int:
    presets = load_presets()
    if dry_run:
        for name, segments in presets.items():
            for language in TARGET_LANGUAGES:
                print(f"DRY-RUN translate {name} ({len(segments)} segments): en -> {language}")
        return 0

    results: list[CheckResult] = []
    async with httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=60.0) as client:
        for name, segments in presets.items():
            for language in TARGET_LANGUAGES:
                response = await client.post(
                    "/v1/translate",
                    headers=_headers(),
                    json={
                        "segments": segments,
                        "source_language": "en",
                        "target_language": language,
                    },
                )
                if response.is_error:
                    print(f"FAIL {name}/{language}: translate HTTP {response.status_code}", file=sys.stderr)
                    results.append(CheckResult(name, language, "*", False, (f"translate HTTP {response.status_code}",)))
                    continue
                translated = response.json().get("segments", {})
                for key, source in segments.items():
                    failures = check_segment(source, translated.get(key, ""), language)
                    result = CheckResult(name, language, key, not failures, failures)
                    results.append(result)
                    state = "PASS" if result.ok else "FAIL"
                    detail = "" if result.ok else ": " + "; ".join(failures)
                    print(f"{state} {name}/{language}/{key}{detail}")

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps([asdict(item) for item in results], indent=2), encoding="utf-8")
    return 1 if any(not item.ok for item in results) else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("AI_BASE_URL", "http://localhost:8200"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output", type=Path, help="Optional JSON result path for a live run")
    args = parser.parse_args()
    return asyncio.run(run(args.base_url, dry_run=args.dry_run, output=args.output))


if __name__ == "__main__":
    raise SystemExit(main())
