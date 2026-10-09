"""
Audio I/O utilities.
load_audio_bytes()  → mono float32 numpy array at original sample rate
"""

from __future__ import annotations

import io
import numpy as np
import structlog

log = structlog.get_logger()

try:
    import soundfile as sf
    _SF_AVAILABLE = True
except ImportError:
    _SF_AVAILABLE = False
    log.warning("soundfile not installed — audio loading will raise in non-stub mode")


def load_audio_bytes(data: bytes) -> tuple[np.ndarray, int]:
    """
    Load raw WAV or MP3 bytes.
    Returns (samples_float32, sample_rate).
    Raises ValueError on bad audio.
    """
    if not _SF_AVAILABLE:
        raise RuntimeError("soundfile is not installed")
    try:
        buf = io.BytesIO(data)
        samples, sr = sf.read(buf, dtype="float32", always_2d=False)
        # Collapse stereo to mono by averaging channels
        if samples.ndim == 2:
            samples = samples.mean(axis=1)
        return samples, sr
    except Exception as exc:
        raise ValueError(f"Audio decode failed: {exc}") from exc


def audio_duration_ms(samples: np.ndarray, sample_rate: int) -> int:
    return int(len(samples) / sample_rate * 1000)
