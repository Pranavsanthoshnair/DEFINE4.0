"""
Engine registry — reads models.yaml to dispatch STT engine per language.
Provides the model status dict for /healthz.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import yaml
import structlog

if TYPE_CHECKING:
    from app.stt.base import STTEngine

log = structlog.get_logger()

# Default language → engine name mapping (overridden by models.yaml)
_DEFAULT_ROUTING: dict[str, str] = {
    "en": "faster-whisper",
    "hi": "faster-whisper",
    "ml": "faster-whisper",
    "ta": "faster-whisper",
    "te": "faster-whisper",
    "kn": "faster-whisper",
    "bn": "faster-whisper",
    "mr": "faster-whisper",
    "gu": "faster-whisper",
}

_language_routing: dict[str, str] = dict(_DEFAULT_ROUTING)


def load_models_yaml(path: str | Path) -> dict:
    p = Path(path)
    if not p.exists():
        log.warning("models_yaml_not_found", path=str(p))
        return {}
    cfg: dict = yaml.safe_load(p.read_text())
    routing = cfg.get("stt_routing", {})
    _language_routing.update(routing)
    log.info("models_yaml_loaded", routing=_language_routing)
    return cfg


def engine_for_language(
    language: str | None,
    engines: dict[str, "STTEngine"],
) -> "STTEngine":
    """Pick the best engine for the given language hint."""
    engine_name = _language_routing.get(language or "en", "faster-whisper")
    if engine_name in engines:
        return engines[engine_name]
    # Fallback: return any available engine
    for eng in engines.values():
        return eng
    raise RuntimeError("No STT engine registered")
