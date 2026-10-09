"""
Faster-Whisper STT engine.
Loaded once at startup from the models volume.
Uses int8 quantisation on CPU. Whisper settings follow the contract spec.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

import structlog

from app.audio.io import load_audio_bytes, audio_duration_ms
from app.audio.resample import resample_to_16k
from app.audio.vad import trim_silence
from app.config import settings
from app.stt.base import STTEngine, STTResult

log = structlog.get_logger()

# Language-specific initial prompts to bias Whisper toward short telephony replies
INITIAL_PROMPTS: dict[str, str] = {
    "en": "yes, no, sure, okay, later, busy, stop calling, I will come",
    "hi": "हाँ, नहीं, ठीक है, बाद में, रुको, haan, nahi, theek hai, baad mein",
    "ml": "അതെ, ഇല്ല, ശരി, pinne, haan, okay",
    "ta": "ஆம், இல்லை, சரி, piragu, okay",
    "te": "అవును, కాదు, సరే, తర్వాత",
    "kn": "ಹೌದು, ಇಲ್ಲ, ಸರಿ, ನಂತರ",
}


class FasterWhisperEngine(STTEngine):
    """
    faster-whisper (CTranslate2) STT engine.
    Requires faster-whisper to be installed in the environment.
    """

    def __init__(self) -> None:
        self._model = None
        self._load()

    def _load(self) -> None:
        try:
            from faster_whisper import WhisperModel  # type: ignore[import]

            model_path = Path(settings.models_dir) / f"whisper-{settings.whisper_model_size}"
            if not model_path.exists():
                log.info(
                    "faster_whisper_loading_from_hub",
                    size=settings.whisper_model_size,
                )
                model_id = settings.whisper_model_size
            else:
                model_id = str(model_path)

            self._model = WhisperModel(
                model_id,
                device=settings.whisper_device,
                compute_type=settings.whisper_compute_type,
                cpu_threads=4,
                num_workers=1,
            )
            log.info("faster_whisper_loaded", size=settings.whisper_model_size)
        except Exception as exc:
            log.error("faster_whisper_load_failed", error=str(exc))
            self._model = None

    @property
    def name(self) -> str:
        return f"faster-whisper-{settings.whisper_model_size}"

    @property
    def available(self) -> bool:
        return self._model is not None

    async def transcribe(
        self,
        audio_bytes: bytes,
        language: str | None = None,
    ) -> STTResult:
        if self._model is None:
            raise RuntimeError("FasterWhisper model not loaded")

        t0 = time.monotonic()

        samples, sr = load_audio_bytes(audio_bytes)
        duration_ms = audio_duration_ms(samples, sr)

        # Cap at max_audio_sec
        max_samples = settings.stt_max_audio_sec * sr
        truncated = len(samples) > max_samples
        if truncated:
            samples = samples[:max_samples]
            duration_ms = settings.stt_max_audio_sec * 1000

        # VAD trim (we run VAD ourselves — pass vad_filter=False to whisper)
        samples, speech_dur, no_speech = trim_silence(samples, sr)
        if no_speech:
            return STTResult(
                text="", language=language or "en",
                confidence=0.0, duration_ms=duration_ms,
                latency_ms=int((time.monotonic() - t0) * 1000),
                model=self.name, truncated=truncated, no_speech=True,
            )

        samples_16k = resample_to_16k(samples, sr)

        initial_prompt = INITIAL_PROMPTS.get(language or "en", "")

        # Run blocking transcription in a thread pool
        loop = asyncio.get_event_loop()
        segments_list, info = await loop.run_in_executor(
            None,
            lambda: self._model.transcribe(  # type: ignore[union-attr]
                samples_16k,
                language=language,
                beam_size=1,
                temperature=0,
                vad_filter=False,
                condition_on_previous_text=False,
                initial_prompt=initial_prompt,
            ),
        )
        segments_list = list(segments_list)

        text = " ".join(s.text.strip() for s in segments_list).strip()

        # Confidence: mean of per-segment avg_logprob converted to 0..1
        if segments_list:
            raw_conf = sum(
                min(max(s.avg_logprob + 1.0, 0.0), 1.0)
                for s in segments_list
            ) / len(segments_list)
        else:
            raw_conf = 0.0

        latency_ms = int((time.monotonic() - t0) * 1000)
        detected_lang = info.language if info.language else (language or "en")

        return STTResult(
            text=text,
            language=detected_lang,
            confidence=round(raw_conf, 3),
            duration_ms=duration_ms,
            latency_ms=latency_ms,
            model=self.name,
            truncated=truncated,
            no_speech=not text,
        )
