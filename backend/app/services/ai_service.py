"""
Service stub: AI script generation behind a provider abstraction.
Supports OpenAI, Anthropic, and Google Gemini via a common interface.
"""

from __future__ import annotations

from typing import Optional
import structlog

from app.core.config import settings

log = structlog.get_logger()


class AIService:
    """
    Provider-agnostic wrapper for LLM calls.
    Switch provider by setting AI_PROVIDER env var.
    (Stub — LLM calls NOT YET IMPLEMENTED.)
    """

    def __init__(self) -> None:
        self.provider = settings.ai_provider
        self.model = settings.ai_model
        self.api_key = settings.ai_api_key

    async def generate_script(
        self,
        brief: str,
        language: str = "en",
        tone: Optional[str] = None,
    ) -> str:
        """
        Generate a call script from a campaign brief.
        Returns raw script text.
        (NOT YET IMPLEMENTED.)
        """
        raise NotImplementedError("AIService.generate_script is not implemented")

    async def translate_script(self, script: str, target_language: str) -> str:
        """
        Translate an existing script to a target language.
        (NOT YET IMPLEMENTED.)
        """
        raise NotImplementedError("AIService.translate_script is not implemented")
