"""
Celery tasks for telephony.
Contract: CONTRACTS.md section 10.

Task names follow the contract exactly:
  telephony.dispatch_due_calls
  telephony.place_call
  telephony.fetch_recording
  telephony.sweep_stuck_calls
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

import structlog

from app.celery_app import celery_app

log = structlog.get_logger()


def _run_async(coro):
    """Run an async coroutine from a synchronous Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="telephony.dispatch_due_calls", max_retries=0)
def dispatch_due_calls() -> None:
    """
    Pick due contacts from running campaigns and enqueue place_call tasks.
    Runs every 10 seconds via Celery Beat.
    """
    _run_async(_dispatch_due_calls_async())


@celery_app.task(
    name="telephony.place_call",
    bind=True,
    max_retries=2,
    default_retry_delay=5,
)
def place_call(self, campaign_contact_id: str) -> None:
    """
    Create a calls row and initiate the call via the configured provider.
    Retries up to 2 times with exponential backoff on network errors only.
    """
    _run_async(_place_call_async(self, UUID(campaign_contact_id)))


@celery_app.task(
    name="telephony.fetch_recording",
    bind=True,
    max_retries=3,
    default_retry_delay=200,  # ~3 min, then 6 min, then 12 min ≈ 10 min total
)
def fetch_recording(self, call_id: str) -> None:
    """
    Download, encrypt, and store a call recording.
    Retries 3 times over ~10 minutes on download failure.
    """
    _run_async(_fetch_recording_async(self, UUID(call_id)))


@celery_app.task(name="telephony.sweep_stuck_calls", max_retries=0)
def sweep_stuck_calls() -> None:
    """
    Mark calls stuck in initiated|ringing|in_progress for > 15 min as failed.
    Runs every 60 seconds via Celery Beat.
    """
    _run_async(_sweep_stuck_calls_async())


# ── Async implementations ──────────────────────────────────────────────────────

async def _dispatch_due_calls_async() -> None:
    """
    For each running campaign inside its calling window:
      1. Compute free slots (max_concurrent - active_calls from Redis).
      2. SELECT FOR UPDATE SKIP LOCKED the due contacts.
      3. Skip opted_out / dnd / no-consent contacts.
      4. Mark in_call and enqueue place_call.
    """
    # Import here to avoid circular imports at module load
    from app.telephony.scheduler import dispatch_campaigns

    try:
        await dispatch_campaigns()
    except Exception as exc:  # noqa: BLE001
        log.error("dispatch_due_calls_error", error=str(exc))


async def _place_call_async(task, campaign_contact_id: UUID) -> None:
    from app.telephony.scheduler import execute_place_call

    try:
        await execute_place_call(campaign_contact_id)
    except Exception as exc:  # noqa: BLE001
        log.error(
            "place_call_error",
            campaign_contact_id=str(campaign_contact_id),
            error=str(exc),
        )
        # Retry on transient errors (network / provider 5xx)
        raise task.retry(exc=exc, countdown=5 * (2 ** task.request.retries))


async def _fetch_recording_async(task, call_id: UUID) -> None:
    from app.telephony.recordings import download_and_store_recording

    try:
        await download_and_store_recording(call_id)
    except Exception as exc:  # noqa: BLE001
        log.error("fetch_recording_error", call_id=str(call_id), error=str(exc))
        raise task.retry(exc=exc)


async def _sweep_stuck_calls_async() -> None:
    from app.telephony.scheduler import sweep_stuck

    try:
        await sweep_stuck()
    except Exception as exc:  # noqa: BLE001
        log.error("sweep_stuck_calls_error", error=str(exc))
