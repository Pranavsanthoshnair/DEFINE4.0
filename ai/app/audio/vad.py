"""
Voice Activity Detection (VAD) using silero-vad.
Returns trimmed audio and speech duration, or signals no_speech.

Spec: if speech_duration < 0.3 s → return (samples, 0, no_speech=True)
"""

from __future__ import annotations

import numpy as np
import structlog

log = structlog.get_logger()

NO_SPEECH_MIN_DURATION_SEC = 0.3


def _stub_vad(samples: np.ndarray, sample_rate: int) -> tuple[np.ndarray, float, bool]:
    """Stub VAD — always says the whole audio is speech."""
    duration = len(samples) / sample_rate
    if duration < NO_SPEECH_MIN_DURATION_SEC:
        return samples, 0.0, True
    return samples, duration, False


def _load_silero():
    try:
        import torch

        model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
            trust_repo=True,
        )
        get_speech_ts = utils[0]
        return model, get_speech_ts
    except Exception as exc:
        log.warning("silero-vad not available, using stub VAD", error=str(exc))
        return None, None


_vad_model = None
_get_speech_ts = None


def _ensure_loaded():
    global _vad_model, _get_speech_ts
    if _vad_model is None:
        _vad_model, _get_speech_ts = _load_silero()


def trim_silence(
    samples: np.ndarray, sample_rate: int
) -> tuple[np.ndarray, float, bool]:
    """
    Trim leading/trailing silence with silero-vad.

    Returns:
        (trimmed_samples, speech_duration_sec, no_speech: bool)
    """
    _ensure_loaded()

    if _vad_model is None:
        return _stub_vad(samples, sample_rate)

    try:
        import torch

        tensor = torch.tensor(samples)
        if sample_rate != 16000:
            # VAD works at 16 kHz; resample if needed
            from app.audio.resample import resample_to_16k
            samples_16k = resample_to_16k(samples, sample_rate)
            tensor = torch.tensor(samples_16k)
            sr_for_vad = 16000
        else:
            sr_for_vad = sample_rate

        speeches = _get_speech_ts(tensor, _vad_model, sampling_rate=sr_for_vad)

        if not speeches:
            return samples, 0.0, True

        start = int(speeches[0]["start"] / sr_for_vad * sample_rate)
        end = int(speeches[-1]["end"] / sr_for_vad * sample_rate)
        trimmed = samples[start:end]
        speech_dur = len(trimmed) / sample_rate

        if speech_dur < NO_SPEECH_MIN_DURATION_SEC:
            return samples, 0.0, True

        return trimmed, speech_dur, False

    except Exception as exc:
        log.error("VAD failed, falling back to stub", error=str(exc))
        return _stub_vad(samples, sample_rate)
