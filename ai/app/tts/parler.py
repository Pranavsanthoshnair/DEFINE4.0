"""
Parler-TTS stub — placeholder for optional local Indic TTS.
Falls back to edge-tts when the model is not loaded.
"""

from __future__ import annotations

import structlog

log = structlog.get_logger()

_model_loaded = False


async def synthesize(
    text: str,
    language: str,
    voice: str | None = None,
) -> tuple[bytes, int, str]:
    """
    Parler-TTS synthesis. Currently a stub — uses edge-tts as fallback.
    When the Parler model is loaded via the models volume, this will use it instead.
    """
    log.info("parler_tts_stub_fallback_to_edge", language=language)
    from app.tts.edge import synthesize as edge_synthesize
    wav, dur, _ = await edge_synthesize(text, language, voice)
    return wav, dur, "parler-tts/stub→edge-fallback"
