"""
Template service — async business logic.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_client.client import get_ai_client
from app.db.models import Template, TemplateTranslation, User
from app.templates.schemas import (
    TemplateCreate,
    TemplateResponse,
    TemplateUpdate,
    TranslationResponse,
    TranslationUpdate,
)

log = structlog.get_logger()


async def list_templates(db: AsyncSession) -> list[TemplateResponse]:
    """Return all templates (presets first)."""
    result = await db.execute(
        select(Template).order_by(Template.is_preset.desc(), Template.created_at)
    )
    return [TemplateResponse.model_validate(t) for t in result.scalars().all()]


async def get_template(template_id: uuid.UUID, db: AsyncSession) -> TemplateResponse:
    """Fetch a single template by id; raises 404 if not found."""
    tmpl = await _get_or_404(template_id, db)
    return TemplateResponse.model_validate(tmpl)


async def create_template(
    data: TemplateCreate,
    user: User,
    db: AsyncSession,
) -> TemplateResponse:
    """Create a new template and persist it."""
    tmpl = Template(
        name=data.name,
        use_case=data.use_case,
        source_language=data.source_language,
        variables=[v.model_dump() for v in data.variables] if data.variables else [],
        script=data.script or {},
        dtmf_map=data.dtmf_map or {},
        speech_enabled=data.speech_enabled,
        voicemail_policy=data.voicemail_policy,
        is_preset=False,
        created_by=user.id,
    )
    db.add(tmpl)
    await db.commit()
    await db.refresh(tmpl)
    log.info("template_created", template_id=str(tmpl.id), name=tmpl.name)
    return TemplateResponse.model_validate(tmpl)


async def update_template(
    template_id: uuid.UUID,
    data: TemplateUpdate,
    db: AsyncSession,
) -> TemplateResponse:
    """Update mutable fields on an existing template.

    Raises 409 if a running campaign references this template.
    """
    tmpl = await _get_or_404(template_id, db)

    from app.db.models import Campaign  # avoid circular at module level
    active = await db.execute(
        select(Campaign).where(
            Campaign.template_id == template_id,
            Campaign.status == "running",
        )
    )
    if active.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "template_in_use", "message": "Cannot edit template while a running campaign uses it."}},
        )

    for field, value in data.model_dump(exclude_none=True).items():
        if field == "variables" and value is not None:
            value = [v if isinstance(v, dict) else v.model_dump() for v in value]
        setattr(tmpl, field, value)

    await db.commit()
    await db.refresh(tmpl)
    return TemplateResponse.model_validate(tmpl)


async def get_translations(
    template_id: uuid.UUID, db: AsyncSession
) -> list[TranslationResponse]:
    """Return all translations for a template."""
    await _get_or_404(template_id, db)
    result = await db.execute(
        select(TemplateTranslation).where(
            TemplateTranslation.template_id == template_id
        )
    )
    return [TranslationResponse.model_validate(t) for t in result.scalars().all()]


async def update_translation(
    template_id: uuid.UUID,
    lang: str,
    data: TranslationUpdate,
    user: User,
    db: AsyncSession,
) -> TranslationResponse:
    """Upsert a manual translation (sets status=draft, source=manual)."""
    await _get_or_404(template_id, db)

    result = await db.execute(
        select(TemplateTranslation).where(
            TemplateTranslation.template_id == template_id,
            TemplateTranslation.language == lang,
        )
    )
    trans = result.scalar_one_or_none()
    if trans is None:
        trans = TemplateTranslation(
            template_id=template_id,
            language=lang,
            segments=data.segments,
            status="draft",
            source="manual",
        )
        db.add(trans)
    else:
        trans.segments = data.segments
        trans.status = "draft"
        trans.source = "manual"
        trans.approved_by = None
        trans.approved_at = None

    await db.commit()
    await db.refresh(trans)
    return TranslationResponse.model_validate(trans)


async def approve_translation(
    template_id: uuid.UUID,
    lang: str,
    user: User,
    db: AsyncSession,
) -> TranslationResponse:
    """Approve a translation and re-trigger preparation of campaigns in needs_review."""
    await _get_or_404(template_id, db)
    trans = await _get_trans_or_404(template_id, lang, db)

    trans.status = "approved"
    trans.approved_by = user.id
    trans.approved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(trans)

    # Re-trigger prepare for campaigns in needs_review that use this template
    from app.db.models import Campaign  # avoid circular
    from app.campaigns.prepare import prepare_campaign  # Celery task
    campaigns_result = await db.execute(
        select(Campaign).where(
            Campaign.template_id == template_id,
            Campaign.status == "needs_review",
        )
    )
    for camp in campaigns_result.scalars().all():
        prepare_campaign.delay(str(camp.id))
        log.info("prepare_triggered_after_approval", campaign_id=str(camp.id))

    return TranslationResponse.model_validate(trans)


async def regenerate_translation(
    template_id: uuid.UUID,
    lang: str,
    db: AsyncSession,
) -> TranslationResponse:
    """Re-call the AI service to regenerate translation; stores as draft/ai."""
    tmpl = await _get_or_404(template_id, db)

    ai = get_ai_client()
    try:
        result = await ai.translate(
            segments=tmpl.script or {},
            source_lang=tmpl.source_language,
            target_lang=lang,
        )
    except Exception as exc:
        log.error("translation_ai_error", lang=lang, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": {"code": "ai_error", "message": "AI translation service failed."}},
        )

    res_trans = await db.execute(
        select(TemplateTranslation).where(
            TemplateTranslation.template_id == template_id,
            TemplateTranslation.language == lang,
        )
    )
    trans = res_trans.scalar_one_or_none()
    if trans is None:
        trans = TemplateTranslation(
            template_id=template_id,
            language=lang,
            segments=result.segments,
            status="draft",
            source="ai",
        )
        db.add(trans)
    else:
        trans.segments = result.segments
        trans.status = "draft"
        trans.source = "ai"
        trans.approved_by = None
        trans.approved_at = None

    await db.commit()
    await db.refresh(trans)
    return TranslationResponse.model_validate(trans)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_or_404(template_id: uuid.UUID, db: AsyncSession) -> Template:
    result = await db.execute(select(Template).where(Template.id == template_id))
    tmpl = result.scalar_one_or_none()
    if tmpl is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "not_found", "message": "Template not found."}},
        )
    return tmpl


async def _get_trans_or_404(
    template_id: uuid.UUID, lang: str, db: AsyncSession
) -> TemplateTranslation:
    result = await db.execute(
        select(TemplateTranslation).where(
            TemplateTranslation.template_id == template_id,
            TemplateTranslation.language == lang,
        )
    )
    trans = result.scalar_one_or_none()
    if trans is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "not_found", "message": f"Translation for '{lang}' not found."}},
        )
    return trans
