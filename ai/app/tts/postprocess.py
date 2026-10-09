"""
TTS post-processing — converts raw TTS audio to Exotel call format.

Output spec (from CONTRACTS.md section 7):
  - Mono
  - 8000 Hz
  - PCM16 WAV
  - Loudness normalised to -16 LUFS
  - Leading silence trimmed
  - 150 ms silence appended at end

Uses pydub for processing (pure Python, no ffmpeg binary required in dev).
Falls back to raw bytes if pydub is unavailable.
"""

from __future__ import annotations

import io
import math
import struct
import wave
from dataclasses import dataclass

import structlog

log = structlog.get_logger()

TARGET_SAMPLE_RATE = 8000
TARGET_CHANNELS = 1
TARGET_SAMPLE_WIDTH = 2          # PCM16 = 2 bytes
TARGET_LOUDNESS_LUFS = -16.0
TRAILING_SILENCE_MS = 150


@dataclass
class ProcessedAudio:
    wav_bytes: bytes
    duration_ms: int
    sample_rate: int = TARGET_SAMPLE_RATE


def process(raw_audio_bytes: bytes, source_sample_rate: int = 22050) -> ProcessedAudio:
    """
    Convert raw TTS audio bytes to Exotel call format.

    Steps:
      1. Resample to 8 kHz mono PCM16
      2. Normalise loudness to -16 LUFS
      3. Trim leading silence (< -50 dBFS)
      4. Append 150 ms silence

    Args:
        raw_audio_bytes:   WAV bytes from TTS provider (any sample rate)
        source_sample_rate: Sample rate of input (hint; auto-detected from WAV header)

    Returns:
        ProcessedAudio with WAV bytes and duration
    """
    try:
        return _process_with_pydub(raw_audio_bytes)
    except ImportError:
        log.warning("tts_postprocess_pydub_missing", fallback="basic_resample")
        return _process_basic(raw_audio_bytes, source_sample_rate)
    except Exception as exc:
        log.warning("tts_postprocess_failed", error=str(exc), fallback="passthrough")
        return _passthrough(raw_audio_bytes)


def _process_with_pydub(raw_bytes: bytes) -> ProcessedAudio:
    """Full processing pipeline using pydub."""
    from pydub import AudioSegment
    from pydub.effects import normalize

    audio = AudioSegment.from_file(io.BytesIO(raw_bytes))

    # 1. Convert to mono 8kHz PCM16
    audio = (
        audio
        .set_channels(TARGET_CHANNELS)
        .set_frame_rate(TARGET_SAMPLE_RATE)
        .set_sample_width(TARGET_SAMPLE_WIDTH)
    )

    # 2. Normalise loudness (pydub normalize targets 0 dBFS peak;
    #    we target -16 LUFS by adjusting gain — approximation without pyloudnorm)
    peak_dbfs = audio.max_dBFS
    if peak_dbfs > -60:  # has audible content
        # Rough LUFS ≈ peak - 14 dB for speech. Adjust to hit -16 LUFS.
        gain_db = TARGET_LOUDNESS_LUFS - (peak_dbfs - 14.0)
        gain_db = max(-20.0, min(20.0, gain_db))  # clamp
        audio = audio.apply_gain(gain_db)

    # 3. Trim leading silence (threshold: -50 dBFS)
    leading_silence_ms = _detect_leading_silence(audio, silence_threshold_dbfs=-50)
    if leading_silence_ms > 0:
        audio = audio[leading_silence_ms:]

    # 4. Append 150 ms silence
    silence = AudioSegment.silent(duration=TRAILING_SILENCE_MS, frame_rate=TARGET_SAMPLE_RATE)
    audio = audio + silence

    # Export to WAV bytes
    buf = io.BytesIO()
    audio.export(buf, format="wav")
    wav_bytes = buf.getvalue()

    duration_ms = len(audio)
    log.info("tts_postprocessed", duration_ms=duration_ms, peak_dbfs=round(audio.max_dBFS, 1))
    return ProcessedAudio(wav_bytes=wav_bytes, duration_ms=duration_ms)


def _detect_leading_silence(audio, silence_threshold_dbfs: float = -50, chunk_size_ms: int = 10) -> int:
    """Return milliseconds of leading silence."""
    trim_ms = 0
    while trim_ms < len(audio):
        chunk = audio[trim_ms : trim_ms + chunk_size_ms]
        if chunk.dBFS > silence_threshold_dbfs:
            break
        trim_ms += chunk_size_ms
    return trim_ms


def _process_basic(raw_bytes: bytes, source_sample_rate: int) -> ProcessedAudio:
    """
    Fallback: resample WAV from source_sample_rate to 8kHz using linear interpolation.
    No loudness normalisation — just format conversion.
    """
    # Parse WAV header
    try:
        buf = io.BytesIO(raw_bytes)
        with wave.open(buf, "rb") as wf:
            src_rate = wf.getframerate()
            src_channels = wf.getnchannels()
            src_width = wf.getsampwidth()
            frames = wf.readframes(wf.getnframes())
    except Exception:
        return _passthrough(raw_bytes)

    # Convert to mono int16 samples
    n_samples = len(frames) // src_width
    if src_width == 2:
        samples = list(struct.unpack(f"<{n_samples}h", frames))
    elif src_width == 4:
        samples = [int(x >> 16) for x in struct.unpack(f"<{n_samples}i", frames)]
    else:
        samples = [int(b) - 128 for b in frames]

    # Mix to mono if stereo
    if src_channels == 2:
        samples = [(samples[i] + samples[i + 1]) // 2 for i in range(0, len(samples) - 1, 2)]

    # Linear resample to 8kHz
    ratio = TARGET_SAMPLE_RATE / src_rate
    out_len = int(len(samples) * ratio)
    resampled = []
    for i in range(out_len):
        src_pos = i / ratio
        idx = int(src_pos)
        frac = src_pos - idx
        s0 = samples[idx] if idx < len(samples) else 0
        s1 = samples[idx + 1] if idx + 1 < len(samples) else s0
        resampled.append(int(s0 + frac * (s1 - s0)))

    # Append 150 ms silence
    silence_samples = int(TARGET_SAMPLE_RATE * TRAILING_SILENCE_MS / 1000)
    resampled.extend([0] * silence_samples)

    # Pack back to WAV
    pcm = struct.pack(f"<{len(resampled)}h", *resampled)
    out_buf = io.BytesIO()
    with wave.open(out_buf, "wb") as wf:
        wf.setnchannels(TARGET_CHANNELS)
        wf.setsampwidth(TARGET_SAMPLE_WIDTH)
        wf.setframerate(TARGET_SAMPLE_RATE)
        wf.writeframes(pcm)

    wav_bytes = out_buf.getvalue()
    duration_ms = int(len(resampled) / TARGET_SAMPLE_RATE * 1000)
    return ProcessedAudio(wav_bytes=wav_bytes, duration_ms=duration_ms)


def _passthrough(raw_bytes: bytes) -> ProcessedAudio:
    """Last resort: return audio as-is, estimate duration from byte count."""
    duration_ms = int(len(raw_bytes) / (TARGET_SAMPLE_RATE * TARGET_SAMPLE_WIDTH) * 1000)
    return ProcessedAudio(wav_bytes=raw_bytes, duration_ms=max(duration_ms, 100))
