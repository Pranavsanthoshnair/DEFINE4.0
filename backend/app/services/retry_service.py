"""Database-backed retry decisions using the shared telephony policy."""

from __future__ import annotations

import uuid
from datetime import datetime, time, timezone

from app.db.models import Campaign, CampaignContact, RetryDecision
from app.db.session import AsyncSessionLocal
from app.telephony.retry import DEFAULT_RETRY_POLICY, RETRYABLE_OUTCOMES, schedule_next_attempt

DEFAULT_MAX_RETRIES = 3


class RetryService:
    """Evaluate and persist retry decisions for a campaign contact."""

    async def should_retry(self, campaign_id: str, recipient_id: str, attempt_count: int) -> bool:
        async with AsyncSessionLocal() as db:
            cc = await db.get(CampaignContact, uuid.UUID(str(recipient_id)))
            if cc is None:
                return False
            campaign = await db.get(Campaign, cc.campaign_id)
            if campaign is None or str(campaign.id) != str(campaign_id):
                return False
            limit = cc.max_attempts_override or campaign.max_attempts or DEFAULT_MAX_RETRIES
            return cc.last_outcome in RETRYABLE_OUTCOMES and attempt_count < limit and cc.state in {"pending", "waiting_retry"}

    async def schedule_retry(self, campaign_id: str, recipient_id: str) -> None:
        async with AsyncSessionLocal() as db:
            cc = await db.get(CampaignContact, uuid.UUID(str(recipient_id)))
            if cc is None:
                raise ValueError("Campaign contact not found")
            campaign = await db.get(Campaign, cc.campaign_id)
            if campaign is None or str(campaign.id) != str(campaign_id):
                raise ValueError("Campaign not found")
            now = datetime.now(timezone.utc)
            outcome = cc.last_outcome or "failed"
            state, next_at, final = schedule_next_attempt(
                outcome, cc.attempts,
                cc.max_attempts_override or campaign.max_attempts or DEFAULT_MAX_RETRIES,
                campaign.retry_policy or DEFAULT_RETRY_POLICY, now,
                campaign.timezone or "Asia/Kolkata",
                campaign.calling_window_start or time(9, 0),
                campaign.calling_window_end or time(21, 0),
            )
            cc.state, cc.next_attempt_at, cc.final_outcome = state, next_at, final
            db.add(RetryDecision(
                campaign_contact_id=cc.id, policy_mode="fixed",
                reason=f"outcome={outcome}; attempts={cc.attempts}",
                next_attempt_at=next_at,
            ))
            await db.commit()
