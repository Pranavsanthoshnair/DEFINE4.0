"""
One working Sarvam API call — speech-to-text with Saaras v4.
Reads SARVAM_API_KEY from .env. Never prints the key.

Note: The chat/LLM endpoints (sarvam-105b) require separate beta access.
The STT, TTS, and translate endpoints work with this key — these are the
APIs Veylo AI actually uses.
"""

import io
import math
import os
import struct
import wave

import httpx
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("SARVAM_API_KEY")
if not api_key:
    raise SystemExit("SARVAM_API_KEY not found in .env — add it and try again.")

# Generate a 1-second 16kHz sine wave WAV to transcribe
sample_rate = 16000
n = sample_rate
samples = [int(8000 * math.sin(2 * math.pi * 440 * i / sample_rate)) for i in range(n)]
buf = io.BytesIO()
with wave.open(buf, "wb") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(sample_rate)
    wf.writeframes(struct.pack(f"<{n}h", *samples))
wav_bytes = buf.getvalue()

print("Calling Sarvam Saaras v4 STT...")

response = httpx.post(
    "https://api.sarvam.ai/speech-to-text",
    headers={"api-subscription-key": api_key},
    files={"file": ("test.wav", wav_bytes, "audio/wav")},
    data={"model": "saaras:v4", "language_code": "en-IN"},
    timeout=30,
)

response.raise_for_status()
data = response.json()

print(f"Status : {response.status_code} OK")
print(f"Transcript : '{data['transcript']}'")
print(f"Language   : {data['language_code']}")
print(f"Request ID : {data['request_id']}")
print("\nSarvam API is working.")
