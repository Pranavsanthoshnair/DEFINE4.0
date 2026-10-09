"""
Audio fixture generator — creates phone-quality WAV files for STT benchmarking.

Generates fixtures for all demo languages using Sarvam Bulbul TTS,
then converts them to 8kHz mono PCM16 (Exotel phone format).

Usage:
    python generate_fixtures.py

Output: fixtures/audio/{label}_{lang}.wav

Labels generated:
  yes, no, later, stop, noise (silence)

Languages: en, hi, ml, ta

These are SYNTHETIC fixtures (TTS-generated, not human recordings).
They test the STT pipeline end-to-end but do not replace human recordings
for WER evaluation. See docs/MODEL_REPORT.md for details.
"""

from __future__ import annotations

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import asyncio
import base64
import io
import os
import struct
import wave
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

SARVAM_KEY = os.getenv('SARVAM_API_KEY', '')
OUTPUT_DIR = Path(__file__).parent.parent / 'fixtures' / 'audio'

# Phrases for each label per language
FIXTURES: dict[str, dict[str, list[str]]] = {
    "en": {
        "yes":   ["Yes, I will come", "Sure, count me in", "Okay, I'll be there"],
        "no":    ["No, I cannot come", "Sorry, not coming", "No, I won't make it"],
        "later": ["Call me later please", "I am busy right now", "Call back later"],
        "stop":  ["Please stop calling", "Do not call me again", "Remove my number"],
    },
    "hi": {
        "yes":   ["हाँ, मैं आऊंगा", "ठीक है, आता हूं", "जी हाँ, जरूर आऊंगा"],
        "no":    ["नहीं, नहीं आ पाऊंगा", "माफ करें, नहीं आ सकता", "नहीं"],
        "later": ["बाद में कॉल करें", "अभी व्यस्त हूं", "बाद में फोन करो"],
        "stop":  ["कॉल मत करो", "फोन बंद करो", "मेरा नंबर हटाओ"],
    },
    "ml": {
        "yes":   ["അതെ, ഞാൻ വരാം", "ശരി, വരുന്നുണ്ട്", "ഹാൻ, ഞാൻ ഉണ്ടാകും"],
        "no":    ["ഇല്ല, വരില്ല", "പറ്റില്ല, വരാൻ സാധ്യമല്ല", "ഇല്ല"],
        "later": ["പിന്നെ വിളിക്കൂ", "ഇപ്പോൾ തിരക്കാണ്", "ഇപ്പോൾ സമയമില്ല"],
        "stop":  ["വിളിക്കരുത്", "ഇനി ഫോൺ ചെയ്യരുത്", "നമ്പർ എടുത്തുകളയൂ"],
    },
    "ta": {
        "yes":   ["ஆம், வருவேன்", "சரி, வருகிறேன்", "ஆம், நிச்சயமாக வருவேன்"],
        "no":    ["இல்லை, வர மாட்டேன்", "மன்னிக்கவும், வர இயலாது", "இல்லை"],
        "later": ["பிறகு அழையுங்கள்", "இப்போது பிஸியாக இருக்கிறேன்", "சற்று நேரம் கழித்து அழையுங்கள்"],
        "stop":  ["தொடர்பு கொள்ளாதீர்கள்", "இனி அழைக்காதீர்கள்", "என் எண்ணை நீக்கவும்"],
    },
}

# Sarvam BCP-47 and voice per language (bulbul:v3 compatible voices)
LANG_CONFIG = {
    "en": {"bcp47": "en-IN", "voice": "ritu"},
    "hi": {"bcp47": "hi-IN", "voice": "ritu"},
    "ml": {"bcp47": "ml-IN", "voice": "ritu"},
    "ta": {"bcp47": "ta-IN", "voice": "ritu"},
}
TTS_MODEL = "bulbul:v3"


def _make_silence_wav(duration_ms: int = 2000, sample_rate: int = 8000) -> bytes:
    """Generate a short silence WAV — used as the 'noise' fixture."""
    n = int(sample_rate * duration_ms / 1000)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{n}h", *([0] * n)))
    return buf.getvalue()


def _wav_to_8k_mono(raw_bytes: bytes) -> bytes:
    """Convert WAV (any rate) → 8kHz mono PCM16."""
    # Use pydub if available for quality resampling
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_file(io.BytesIO(raw_bytes))
        audio = audio.set_channels(1).set_frame_rate(8000).set_sample_width(2)
        out = io.BytesIO()
        audio.export(out, format="wav")
        return out.getvalue()
    except ImportError:
        pass

    # Fallback: if already 8kHz WAV, return as-is
    try:
        buf = io.BytesIO(raw_bytes)
        with wave.open(buf, "rb") as wf:
            if wf.getframerate() == 8000 and wf.getnchannels() == 1:
                return raw_bytes
    except Exception:
        pass

    return raw_bytes  # passthrough


async def _synthesize(text: str, lang: str) -> bytes | None:
    """Call Sarvam TTS and return WAV bytes, or None on failure."""
    if not SARVAM_KEY:
        return None

    cfg = LANG_CONFIG[lang]
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                "https://api.sarvam.ai/text-to-speech",
                headers={"api-subscription-key": SARVAM_KEY},
                json={
                    "text": text,
                    "target_language_code": cfg["bcp47"],
                    "speaker": cfg["voice"],
                    "model": TTS_MODEL,
                    "speech_sample_rate": 8000,
                    "output_audio_codec": "wav",
                    "enable_preprocessing": True,
                },
            )
        if r.status_code != 200:
            print(f"    [WARN] TTS {lang} failed: {r.status_code} — {r.text[:80]}")
            return None

        data = r.json()
        audio_b64 = data.get("audios", [None])[0]
        if not audio_b64:
            return None

        wav_bytes = base64.b64decode(audio_b64)
        return _wav_to_8k_mono(wav_bytes)

    except Exception as exc:
        print(f"    [WARN] TTS exception for {lang}: {exc}")
        return None


async def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {OUTPUT_DIR}\n")

    if not SARVAM_KEY:
        print("[WARN] SARVAM_API_KEY not set — generating silence placeholders only")

    total, ok, skipped = 0, 0, 0

    for lang, labels in FIXTURES.items():
        print(f"Language: {lang}")
        for label, phrases in labels.items():
            # Use first phrase as primary fixture; also save alternates
            for idx, phrase in enumerate(phrases):
                suffix = "" if idx == 0 else f"_{idx + 1}"
                filename = f"{label}_{lang}{suffix}.wav"
                out_path = OUTPUT_DIR / filename
                total += 1

                if out_path.exists():
                    print(f"  [SKIP] {filename} already exists")
                    skipped += 1
                    continue

                print(f"  Generating {filename}: \"{phrase}\"")
                wav = await _synthesize(phrase, lang)

                if wav is None:
                    # Fallback: save a 1-second silence so the file exists
                    wav = _make_silence_wav(1000)
                    print(f"    [FALLBACK] silence placeholder written")

                out_path.write_bytes(wav)
                ok += 1

        # Noise fixture (silence) for each language
        noise_path = OUTPUT_DIR / f"noise_{lang}.wav"
        if not noise_path.exists():
            noise_path.write_bytes(_make_silence_wav(2000))
            print(f"  Written noise_{lang}.wav (2s silence)")
            ok += 1
            total += 1
        else:
            print(f"  [SKIP] noise_{lang}.wav already exists")

        print()

    # Short-name aliases required by CONTRACTS.md section 13
    aliases = {
        "yes_en.wav": "yes_en.wav",
        "no_en.wav": "no_en.wav",
        "yes_hi.wav": "yes_hi.wav",
        "no_hi.wav": "no_hi.wav",
        "yes_ml.wav": "yes_ml.wav",
        "no_ml.wav": "no_ml.wav",
        "yes_ta.wav": "yes_ta.wav",
        "no_ta.wav": "no_ta.wav",
        "noise.wav": "noise_en.wav",   # generic noise alias
    }
    print("Writing contract-required short-name aliases...")
    for alias, source in aliases.items():
        alias_path = OUTPUT_DIR / alias
        source_path = OUTPUT_DIR / source
        if not alias_path.exists() and source_path.exists():
            import shutil
            shutil.copy2(source_path, alias_path)
            print(f"  {alias} -> {source}")

    print(f"\nDone. {ok} generated, {skipped} skipped, {total} total.")
    print(f"Fixtures: {OUTPUT_DIR}")
    print("\nNOTE: These are TTS-synthesized fixtures, not human recordings.")
    print("For accurate WER, record real speakers and replace these files.")


if __name__ == "__main__":
    asyncio.run(main())
