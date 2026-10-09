"""
Pydantic v2 schemas for the Templates API.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Template schemas
# ---------------------------------------------------------------------------

class VariableDef(BaseModel):
    key: str
    label: str
    required: bool = True


class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    use_case: str
    source_language: str = "en"
    variables: list[VariableDef] | None = None
    script: dict[str, str] | None = None
    dtmf_map: dict[str, str] | None = None
    speech_enabled: bool = True
    voicemail_policy: str = "leave_message"


class TemplateUpdate(BaseModel):
    name: str | None = None
    variables: list[VariableDef] | None = None
    script: dict[str, str] | None = None
    dtmf_map: dict[str, str] | None = None
    speech_enabled: bool | None = None
    voicemail_policy: str | None = None


class TemplateResponse(BaseModel):
    id: uuid.UUID
    name: str
    use_case: str
    source_language: str
    variables: list[Any] | None
    script: dict[str, Any] | None
    dtmf_map: dict[str, Any] | None
    speech_enabled: bool
    voicemail_policy: str
    is_preset: bool
    created_by: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Translation schemas
# ---------------------------------------------------------------------------

class TranslationUpdate(BaseModel):
    segments: dict[str, str]


class TranslationResponse(BaseModel):
    id: uuid.UUID
    template_id: uuid.UUID
    language: str
    segments: dict[str, Any] | None
    status: str
    source: str
    approved_by: uuid.UUID | None
    approved_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
