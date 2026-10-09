"""Service stub: campaign analytics aggregation."""

from __future__ import annotations

import structlog

log = structlog.get_logger()


class AnalyticsService:
    """
    Aggregates call outcome data for a campaign from Supabase.
    (Stub — aggregation queries NOT YET IMPLEMENTED.)
    """

    async def get_campaign_stats(self, campaign_id: str) -> dict:
        """Return aggregate call statistics for a campaign."""
        raise NotImplementedError("AnalyticsService.get_campaign_stats not implemented")

    async def get_recipient_history(self, recipient_id: str) -> list:
        """Return full call attempt history for a single recipient."""
        raise NotImplementedError("AnalyticsService.get_recipient_history not implemented")
