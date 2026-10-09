"""
Generate intent classification training data via LLM (Gemini free tier).

Produces JSONL at ml/intent/data/raw.jsonl with fields:
  {"text": "...", "label": "...", "lang": "..."}

Labels: confirm, decline, reschedule, call_later, stop_calling, unclear
Languages: en, hi, ml, ta

Usage:
  set GEMINI_API_KEY=your_key
  python ml/intent/generate_data.py
  python ml/intent/generate_data.py --langs en hi --per-class 50  # quick smoke test
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[2] / ".env")

LABELS = ["confirm", "decline", "reschedule", "call_later", "stop_calling", "unclear"]
LANGUAGES = ["en", "hi", "ml", "ta"]
DEFAULT_PER_CLASS = 400  # per (lang, label) pair -> ~9 600 rows total
SEED_BATCH = 20
MAX_BATCH_ATTEMPTS = 50
DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
DEFAULT_MIN_INTERVAL_SECONDS = 1.5
DEFAULT_OLLAMA_MODEL = "qwen3:1.7b"
DEFAULT_OLLAMA_URL = "http://localhost:11434/api/chat"
DATA_DIR = Path(__file__).parent / "data"

SEEDS: dict[str, dict[str, list[str]]] = {
    "en": {
        "confirm": ["yes", "I will come", "sure", "okay", "count me in", "attending"],
        "decline": ["no", "not coming", "can't come", "not interested"],
        "reschedule": ["reschedule", "another time", "different time"],
        "call_later": ["call later", "busy now", "not now", "call me back"],
        "stop_calling": ["stop calling", "do not call", "remove my number", "DND"],
        "unclear": ["who is this", "what event", "hmm", "hello", "I don't know"],
    },
    "hi": {
        "confirm": ["haan", "theek hai", "aaunga", "ji haan", "haan haan"],
        "decline": ["nahi", "nahin", "nahi aa sakta", "no"],
        "reschedule": ["dusra time", "time badlo", "reschedule karo"],
        "call_later": ["baad mein", "abhi nahi", "busy hoon"],
        "stop_calling": ["call mat karo", "band karo", "phone mat karo"],
        "unclear": ["kaun ho", "kya event", "hmm", "pata nahi"],
    },
    "ml": {
        "confirm": ["athey", "sheri", "varam", "ok"],
        "decline": ["illa", "varilla", "pattilla"],
        "reschedule": ["vere samayam", "pinneedu", "schedule maaroo"],
        "call_later": ["pinne vilikku", "ippol busy", "pinne"],
        "stop_calling": ["vilikkaruth", "vilikalle"],
        "unclear": ["aarudu", "ethu event", "hmm", "ariyilla"],
    },
    "ta": {
        "confirm": ["aam", "sari", "varuven"],
        "decline": ["illai", "varamatten"],
        "reschedule": ["vere neram", "schedule maru", "piragu paarkalam"],
        "call_later": ["piragu", "appuram"],
        "stop_calling": ["azhaikkadheenga", "phone pannadheenga"],
        "unclear": ["yaar ithu", "enna event", "hmm", "theriyala"],
    },
}

PROMPT_TMPL = (
    "Generate {n} short utterances (1-12 words each) for the intent '{label}' "
    "in language '{lang}'. "
    "Mix these styles: "
    "(1) native script natural phrasing, "
    "(2) romanised Latin spelling as a person or ASR might write it, "
    "(3) code-mixed with English words like come/busy/sure/later, "
    "(4) polite and impolite forms with fillers like umm or haan haan, "
    "(5) ASR-noisy variants with typos or dropped letters. "
    "For 'unclear' include: unrelated statements, questions about who is calling, "
    "noise words, partial words, single fillers. "
    "Seed examples to diversify from: {seeds}. "
    "Return ONLY a JSON array of strings. No explanation. No duplicates."
)


class GroqRequestError(RuntimeError):
    def __init__(self, status: int, retry_after: float | None = None) -> None:
        super().__init__(f"Groq request failed with HTTP {status}")
        self.status = status
        self.retry_after = retry_after


class GroqKeyPool:
    """Round-robin pool with cooldowns; never prints or exposes key values."""

    def __init__(self, keys: list[str], min_interval: float) -> None:
        self.keys = keys
        self.min_interval = max(0.0, min_interval)
        self.cooldown_until = [0.0] * len(keys)
        self.next_index = 0
        self.last_request_at = 0.0

    def wait_for_slot(self) -> int:
        while True:
            now = time.monotonic()
            global_wait = self.last_request_at + self.min_interval - now
            available = [
                i for i, until in enumerate(self.cooldown_until)
                if until <= now
            ]
            if available and global_wait <= 0:
                for offset in range(len(self.keys)):
                    i = (self.next_index + offset) % len(self.keys)
                    if i in available:
                        self.next_index = (i + 1) % len(self.keys)
                        self.last_request_at = time.monotonic()
                        return i

            waits = [self.cooldown_until[i] - now for i in range(len(self.keys))]
            wait_for = max(global_wait, min((w for w in waits if w > 0), default=0.1))
            time.sleep(max(0.1, wait_for))

    def cooldown(self, index: int, seconds: float) -> None:
        self.cooldown_until[index] = time.monotonic() + max(1.0, seconds)


def _load_groq_keys() -> list[str]:
    numbered = []
    for name, value in os.environ.items():
        if re.fullmatch(r"GROQ_API_KEY_\d+", name) and value.strip():
            numbered.append((int(name.rsplit("_", 1)[1]), value.strip()))
    numbered.sort(key=lambda item: item[0])
    keys = [value for _, value in numbered]
    if not keys and os.environ.get("GROQ_API_KEY", "").strip():
        keys = [os.environ["GROQ_API_KEY"].strip()]
    return keys


def _parse_array(raw: str) -> list[str]:
    """Parse a JSON array even if the model adds a short preamble or code fence."""
    cleaned = raw.strip().removeprefix("```json").removeprefix("```").strip()
    cleaned = cleaned.removesuffix("```").strip()
    start = cleaned.find("[")
    if start < 0:
        raise ValueError("model response did not contain a JSON array")
    parsed, _ = json.JSONDecoder().raw_decode(cleaned[start:])
    if not isinstance(parsed, list):
        raise ValueError("model response JSON was not an array")
    return [item for item in parsed if isinstance(item, str)]


def _call_groq(prompt: str, api_key: str, model: str) -> list[str]:
    import httpx

    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 1024,
    }
    with httpx.Client(timeout=45.0) as client:
        resp = client.post(
            url, json=payload,
            headers={"Authorization": f"Bearer {api_key}"},
        )
    if resp.status_code != 200:
        retry_after = None
        try:
            retry_after = float(resp.headers.get("retry-after", ""))
        except ValueError:
            pass
        raise GroqRequestError(resp.status_code, retry_after)

    data = resp.json()
    raw = data["choices"][0]["message"]["content"]
    return _parse_array(raw)


def _call_ollama(prompt: str, model: str, url: str) -> list[str]:
    import httpx

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "think": False,
        "format": {"type": "array", "items": {"type": "string"}},
        "options": {"temperature": 0.7},
    }
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            with httpx.Client(timeout=180.0) as client:
                resp = client.post(url, json=payload)
            if resp.status_code in (502, 503, 504):
                raise RuntimeError(f"Ollama HTTP {resp.status_code}")
            if resp.status_code != 200:
                raise SystemExit(
                    f"Ollama HTTP {resp.status_code}. "
                    f"Check that model '{model}' is installed."
                )
            data = resp.json()
            return _parse_array(data["message"]["content"])
        except (httpx.HTTPError, RuntimeError, KeyError, ValueError) as exc:
            last_error = exc
            if attempt < 3:
                delay = 3 * attempt
                print(f"\n    Ollama temporary failure; retrying in {delay}s")
                time.sleep(delay)
    raise SystemExit(
        f"Could not reach Ollama at {url} after 3 attempts. "
        "Check that Ollama is running and retry."
    ) from last_error


def _dedup(rows: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out = []
    for row in rows:
        key = row["text"].lower().strip()
        if key and key not in seen:
            seen.add(key)
            out.append(row)
    return out


def _text_key(text: str) -> str:
    """Normalize text for duplicate detection without changing stored text."""
    return " ".join(text.casefold().split())


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main(args: argparse.Namespace) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    provider = os.environ.get("GENERATOR_PROVIDER", "groq").casefold()
    keys: list[str] = []
    pool: GroqKeyPool | None = None
    if provider == "ollama":
        model = os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
        ollama_url = os.environ.get("OLLAMA_URL", DEFAULT_OLLAMA_URL)
        print(f"Using local Ollama; model={model}; url={ollama_url}")
    elif provider == "groq":
        keys = _load_groq_keys()
        if not keys:
            raise SystemExit(
                "No Groq keys found. Add GROQ_API_KEY_1, GROQ_API_KEY_2, ... "
                "to ai/.env."
            )
        model = os.environ.get("GROQ_MODEL", DEFAULT_GROQ_MODEL)
        min_interval = float(
            os.environ.get("GROQ_MIN_INTERVAL_SECONDS", DEFAULT_MIN_INTERVAL_SECONDS)
        )
        pool = GroqKeyPool(keys, min_interval)
        print(f"Loaded {len(keys)} Groq key(s); model={model}; serial request queue")
    else:
        raise SystemExit("GENERATOR_PROVIDER must be 'groq' or 'ollama'.")

    out_path = DATA_DIR / "raw.jsonl"
    all_rows: list[dict] = []
    seen_texts: set[str] = set()
    if out_path.exists():
        for line in out_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if not all(key in row for key in ("text", "label", "lang")):
                raise SystemExit(f"Invalid row in existing file: {out_path}")
            key = _text_key(str(row["text"]))
            if key and key not in seen_texts:
                seen_texts.add(key)
                all_rows.append(row)
        if all_rows:
            print(f"Resuming with {len(all_rows)} existing rows from {out_path}")

    for lang in args.langs:
        for label in LABELS:
            print(f"  [{lang}] {label} ...", end=" ", flush=True)
            rows = [row for row in all_rows if row.get("lang") == lang and row.get("label") == label]
            seeds = SEEDS.get(lang, {}).get(label, [])
            target = args.per_class
            if len(rows) >= target:
                print(f"{len(rows)} rows (already complete)")
                continue
            starting_count = len(rows)
            attempts = 0

            while len(rows) < target:
                attempts += 1
                if attempts > MAX_BATCH_ATTEMPTS:
                    raise SystemExit(
                        f"Could not collect {target} unique rows for [{lang}] {label} "
                        f"after {MAX_BATCH_ATTEMPTS} API batches. "
                        "Reduce --per-class or retry later."
                    )
                n = min(SEED_BATCH, target - len(rows))
                prompt = PROMPT_TMPL.format(
                    n=n, label=label, lang=lang, seeds=", ".join(seeds[:5])
                )
                if provider == "ollama":
                    generated = _call_ollama(prompt, model, ollama_url)
                else:
                    generated = []
                    request_failures = 0
                    while not generated:
                        assert pool is not None
                        key_index = pool.wait_for_slot()
                        try:
                            generated = _call_groq(prompt, pool.keys[key_index], model)
                            if not generated:
                                request_failures += 1
                                if request_failures > len(keys) * 3:
                                    raise SystemExit(
                                        "Groq returned empty responses too many times; stopping."
                                    )
                                pool.cooldown(key_index, 2.0 + random.uniform(0.0, 1.0))
                        except GroqRequestError as exc:
                            request_failures += 1
                            if exc.status in (401, 403, 404):
                                raise SystemExit(
                                    f"Groq HTTP {exc.status}. Check the key and GROQ_MODEL."
                                )
                            if exc.status not in (408, 429, 500, 502, 503, 504):
                                raise SystemExit(f"Groq HTTP {exc.status}; stopping.")
                            if request_failures > len(keys) * 3:
                                raise SystemExit(
                                    "Too many Groq request failures; stop and check quotas."
                                )
                            delay = exc.retry_after or min(60.0, 2.0 ** min(request_failures, 5))
                            pool.cooldown(key_index, delay + random.uniform(0.0, 1.0))
                            print(
                                f"\n    Groq HTTP {exc.status}; key {key_index + 1} "
                                f"cooling down for {delay:.1f}s"
                            )
                        except (ValueError, KeyError, json.JSONDecodeError) as exc:
                            request_failures += 1
                            if request_failures > 3:
                                raise SystemExit(f"Invalid Groq response: {exc}")
                            time.sleep(2.0 + random.uniform(0.0, 1.0))
                for text in generated:
                    if isinstance(text, str) and text.strip():
                        clean_text = text.strip()
                        key = _text_key(clean_text)
                        if key and key not in seen_texts:
                            seen_texts.add(key)
                            rows.append({"text": clean_text, "label": label, "lang": lang})
                _write_jsonl(out_path, all_rows + rows[starting_count:])

            rows = rows[:target]
            print(f"{len(rows)} rows")
            all_rows.extend(rows[starting_count:])

    random.shuffle(all_rows)
    _write_jsonl(out_path, all_rows)

    print(f"\nWrote {len(all_rows)} rows -> {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--langs", nargs="+", default=LANGUAGES)
    parser.add_argument("--per-class", type=int, default=DEFAULT_PER_CLASS)
    main(parser.parse_args())
