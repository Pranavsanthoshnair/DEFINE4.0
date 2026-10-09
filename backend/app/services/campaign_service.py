"""Service stub: campaign orchestration."""

from __future__ import annotations

import structlog

log = structlog.get_logger()


class CampaignService:
    """
    Owns campaign lifecycle: draft → active → paused → completed.
    Delegates call initiation to ExotelService and script generation to AIService.
    (Stub — methods raise NotImplementedError until wired.)
    """

    async def create_campaign(self, payload: dict) -> dict:
        raise NotImplementedError("CampaignService.create_campaign not implemented")

    async def launch_campaign(self, campaign_id: str) -> None:
        raise NotImplementedError("CampaignService.launch_campaign not implemented")

    async def pause_campaign(self, campaign_id: str) -> None:
        raise NotImplementedError("CampaignService.pause_campaign not implemented")
