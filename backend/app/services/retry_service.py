"""Service stub: configurable retry logic for failed call attempts."""

from __future__ import annotations

import structlog

log = structlog.get_logger()

DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY_MINUTES = 30


class RetryService:
    """
    Evaluates whether a failed call attempt should be retried and
    schedules the next attempt according to campaign retry rules.
    (Stub — retry scheduling NOT YET IMPLEMENTED.)
    """

    async def should_retry(
        self,
        campaign_id: str,
        recipient_id: str,
        attempt_count: int,
    ) -> bool:
        """Return True if another attempt should be made."""
        raise NotImplementedError("RetryService.should_retry not implemented")

    async def schedule_retry(
        self,
        campaign_id: str,
        recipient_id: str,
    ) -> None:
        """Queue a retry attempt for the given recipient."""
        raise NotImplementedError("RetryService.schedule_retry not implemented")
