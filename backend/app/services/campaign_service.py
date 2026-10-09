"""Campaign lifecycle orchestration backed by SQLAlchemy."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.models import Campaign, CampaignContact, Template
from app.db.session import AsyncSessionLocal


class CampaignService:
    """Create and transition campaigns without placing calls directly."""

    async def create_campaign(self, payload: dict) -> dict:
        template_id = uuid.UUID(str(payload["template_id"]))
        created_by = uuid.UUID(str(payload["created_by"]))
        async with AsyncSessionLocal() as db:
            if await db.get(Template, template_id) is None:
                raise ValueError("Template not found")
            campaign = Campaign(
                name=payload["name"], template_id=template_id, created_by=created_by,
                event_details=payload.get("event_details") or {},
                variable_overrides=payload.get("variable_overrides") or {},
                languages=payload.get("languages"), caller_id=payload.get("caller_id"),
                timezone=payload.get("timezone", "Asia/Kolkata"),
                max_attempts=int(payload.get("max_attempts", 3)),
                max_concurrent_calls=int(payload.get("max_concurrent_calls", 3)),
                retry_policy=payload.get("retry_policy"),
            )
            db.add(campaign)
            await db.commit()
            await db.refresh(campaign)
            return {"id": str(campaign.id), "name": campaign.name, "status": campaign.status,
                    "created_at": campaign.created_at.isoformat()}

    async def launch_campaign(self, campaign_id: str) -> None:
        async with AsyncSessionLocal() as db:
            campaign = await db.get(Campaign, uuid.UUID(str(campaign_id)))
            if campaign is None:
                raise ValueError("Campaign not found")
            if campaign.status not in {"ready", "paused", "draft", "needs_review"}:
                raise ValueError(f"Campaign cannot be launched from {campaign.status}")
            has_contacts = await db.scalar(select(CampaignContact.id).where(
                CampaignContact.campaign_id == campaign.id).limit(1))
            if has_contacts is None:
                raise ValueError("Campaign has no contacts")
            campaign.status = "running"
            campaign.launched_at = datetime.now(timezone.utc)
            await db.commit()

    async def pause_campaign(self, campaign_id: str) -> None:
        async with AsyncSessionLocal() as db:
            campaign = await db.get(Campaign, uuid.UUID(str(campaign_id)))
            if campaign is None:
                raise ValueError("Campaign not found")
            if campaign.status != "running":
                raise ValueError(f"Campaign cannot be paused from {campaign.status}")
            campaign.status = "paused"
            await db.commit()
