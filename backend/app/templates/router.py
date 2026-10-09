"""
Templates API router — CONTRACTS.md section 6.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.security.auth import get_current_user, require_role
from app.db.models import User
from app.templates import service
from app.templates.schemas import (
    TemplateCreate,
    TemplateResponse,
    TemplateUpdate,
    TranslationResponse,
    TranslationUpdate,
)

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("", response_model=list[TemplateResponse])
async def list_templates(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> list[TemplateResponse]:
    """List all templates, presets first."""
    return await service.list_templates(db)


@router.post("", response_model=TemplateResponse, status_code=201)
async def create_template(
    body: TemplateCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TemplateResponse:
    """Create a new template."""
    return await service.create_template(body, current_user, db)


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> TemplateResponse:
    return await service.get_template(template_id, db)


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: uuid.UUID,
    body: TemplateUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> TemplateResponse:
    return await service.update_template(template_id, body, db)


@router.get("/{template_id}/translations", response_model=list[TranslationResponse])
async def get_translations(
    template_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> list[TranslationResponse]:
    return await service.get_translations(template_id, db)


@router.put(
    "/{template_id}/translations/{lang}",
    response_model=TranslationResponse,
)
async def update_translation(
    template_id: uuid.UUID,
    lang: str,
    body: TranslationUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TranslationResponse:
    return await service.update_translation(template_id, lang, body, current_user, db)


@router.post(
    "/{template_id}/translations/{lang}/approve",
    response_model=TranslationResponse,
)
async def approve_translation(
    template_id: uuid.UUID,
    lang: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TranslationResponse:
    return await service.approve_translation(template_id, lang, current_user, db)


@router.post(
    "/{template_id}/translations/{lang}/regenerate",
    response_model=TranslationResponse,
)
async def regenerate_translation(
    template_id: uuid.UUID,
    lang: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> TranslationResponse:
    return await service.regenerate_translation(template_id, lang, db)
