"""Campaign analytics aggregation over the SQLAlchemy data model."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select

from app.db.models import Call, CampaignContact
from app.db.session import AsyncSessionLocal


class AnalyticsService:
    async def get_campaign_stats(self, campaign_id: str) -> dict:
        cid = uuid.UUID(str(campaign_id))
        async with AsyncSessionLocal() as db:
            total = await db.scalar(select(func.count()).select_from(CampaignContact).where(CampaignContact.campaign_id == cid)) or 0
            rows = (await db.execute(
                select(Call.status, func.count())
                .join(CampaignContact, Call.campaign_contact_id == CampaignContact.id)
                .where(CampaignContact.campaign_id == cid)
                .group_by(Call.status)
            )).all()
            counts = {str(status): int(count) for status, count in rows}
            attempted = sum(counts.values())
            answered = counts.get("in_progress", 0) + counts.get("completed", 0)
            failed = sum(counts.get(s, 0) for s in ("failed", "busy", "no_answer", "canceled"))
            pending = counts.get("initiated", 0) + counts.get("ringing", 0)
            return {
                "campaign_id": str(cid), "total_recipients": int(total),
                "calls_attempted": attempted, "calls_answered": answered,
                "calls_failed": failed, "calls_pending": pending,
                "completion_rate": round(attempted / total, 4) if total else 0.0,
                "answer_rate": round(answered / attempted, 4) if attempted else 0.0,
            }

    async def get_recipient_history(self, recipient_id: str) -> list[dict]:
        rid = uuid.UUID(str(recipient_id))
        async with AsyncSessionLocal() as db:
            calls = (await db.execute(
                select(Call).where(Call.campaign_contact_id == rid).order_by(Call.attempt_no)
            )).scalars().all()
            return [{
                "id": str(call.id), "attempt_no": call.attempt_no,
                "provider": call.provider, "status": call.status, "outcome": call.outcome,
                "duration_sec": call.duration_sec,
                "started_at": call.started_at.isoformat() if call.started_at else None,
                "ended_at": call.ended_at.isoformat() if call.ended_at else None,
            } for call in calls]
