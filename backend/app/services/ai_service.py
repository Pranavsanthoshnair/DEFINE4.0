"""
Service stub: AI script generation behind a provider abstraction.
Supports OpenAI, Anthropic, and Google Gemini via a common interface.
"""

from __future__ import annotations

from typing import Optional
import structlog

from app.ai_client.client import get_ai_client
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
        tone_text = f" Tone: {tone}." if tone else ""
        return (f"Hello. {brief.strip()}{tone_text} "
                "Please press 1 to confirm, 2 to decline, or 3 to request a later call.")

    async def translate_script(self, script: str, target_language: str) -> str:
        """
        Translate an existing script to a target language.
        (NOT YET IMPLEMENTED.)
        """
        result = await get_ai_client().translate(
            {"script": script}, source_lang="en", target_lang=target_language
        )
        return result.segments.get("script", script)
