"""
Audio resampling utilities.
Resample 8 kHz phone audio → 16 kHz (Whisper / IndicConformer requirement).
"""

from __future__ import annotations

import numpy as np
import structlog

log = structlog.get_logger()

_RESAMPLE_FN = None


def _get_resample():
    global _RESAMPLE_FN
    if _RESAMPLE_FN is not None:
        return _RESAMPLE_FN

    # Prefer soxr via resampy or torchaudio; fall back to librosa
    try:
        import librosa
        _RESAMPLE_FN = librosa.resample
        return _RESAMPLE_FN
    except ImportError:
        pass

    log.warning("No resampling library available — install librosa or torchaudio")
    return None


def resample_to_16k(samples: np.ndarray, orig_sr: int) -> np.ndarray:
    """Resample mono float32 audio to 16 kHz. Returns original array if already 16k."""
    if orig_sr == 16000:
        return samples

    fn = _get_resample()
    if fn is None:
        raise RuntimeError("No resampling library installed (install librosa)")

    # librosa.resample signature: (y, orig_sr=, target_sr=)
    return fn(samples, orig_sr=orig_sr, target_sr=16000).astype(np.float32)
