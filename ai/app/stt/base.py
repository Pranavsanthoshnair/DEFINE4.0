"""
STT base interface.
All engines implement STTEngine so the router stays engine-agnostic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class STTResult:
    text: str
    language: str
    confidence: float       # 0..1
    duration_ms: int
    latency_ms: int
    model: str
    truncated: bool = False
    no_speech: bool = False


class STTEngine(ABC):
    """Abstract base for all STT engines."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def transcribe(
        self,
        audio_bytes: bytes,
        language: str | None = None,
    ) -> STTResult: ...
