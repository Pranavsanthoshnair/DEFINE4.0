"""
Dispatcher and scheduler logic (CONTRACTS.md section 9.5).

Functions:
  dispatch_campaigns()      — called by the Celery beat task
  execute_place_call()      — called by the place_call Celery task
  sweep_stuck()             — called by the sweep task
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, time, timedelta, timezone
from uuid import UUID

import structlog

from app.core.config import settings
from app.telephony.retry import (
    DEFAULT_RETRY_POLICY,
    TERMINAL_OUTCOMES,
    in_window,
    schedule_next_attempt,
)

log = structlog.get_logger()

# ── Redis key helpers ─────────────────────────────────────────────────────────

def _active_calls_key(campaign_id: str) -> str:
    return f"pr002:camp:{campaign_id}:active_calls"


def _rate_key() -> str:
    return "pr002:rate:exotel"


# ── Redis helpers (lazy import to avoid import-time connection) ───────────────

def _get_redis():
    import redis as redis_lib
    return redis_lib.from_url(settings.redis_url, decode_responses=True)


def _incr_active_calls(campaign_id: str) -> int:
    r = _get_redis()
    key = _active_calls_key(campaign_id)
    val = r.incr(key)
    r.expire(key, 900)  # safety TTL
    return val


def _decr_active_calls(campaign_id: str) -> int:
    r = _get_redis()
    key = _active_calls_key(campaign_id)
    # Lua script to clamp at zero
    lua = """
    local val = redis.call('DECR', KEYS[1])
    if val < 0 then
        redis.call('SET', KEYS[1], 0)
        return 0
    end
    return val
    """
    result = r.eval(lua, 1, key)
    r.expire(key, 900)
    return int(result)


def _get_active_calls(campaign_id: str) -> int:
    r = _get_redis()
    val = r.get(_active_calls_key(campaign_id))
    return int(val) if val else 0


# ── Main dispatch loop ─────────────────────────────────────────────────────────

async def dispatch_campaigns() -> None:
    """
    For each running campaign:
    1. Check calling window.
    2. Compute free slots.
    3. Lock and pick due contacts.
    4. Mark in_call, enqueue place_call.
    """
    # NOTE: DB access depends on Member 1's session and models being available.
    # Using a try/except so the scheduler gracefully degrades if DB is not set up.
    try:
        from app.db.session import get_db_session
        from app.db.models import Campaign, CampaignContact, Contact
    except ImportError:
        log.warning("dispatch_campaigns_no_db", msg="DB layer not available yet")
        return

    now_utc = datetime.now(tz=timezone.utc)

    async with get_db_session() as session:
        # Fetch all running campaigns
        from sqlalchemy import select, update
        result = await session.execute(
            select(Campaign).where(Campaign.status == "running")
        )
        campaigns = result.scalars().all()

        for campaign in campaigns:
            tz = campaign.timezone or "Asia/Kolkata"
            window_start = campaign.calling_window_start or time(9, 0)
            window_end = campaign.calling_window_end or time(21, 0)

            if not in_window(now_utc, tz, window_start, window_end):
                continue

            active = _get_active_calls(str(campaign.id))
            max_concurrent = min(
                campaign.max_concurrent_calls or 3,
                settings.exotel_max_concurrent,
            )
            free_slots = max(0, max_concurrent - active)

            if free_slots == 0:
                continue

            # SELECT FOR UPDATE SKIP LOCKED
            from sqlalchemy import and_, or_
            due_result = await session.execute(
                select(CampaignContact)
                .where(
                    and_(
                        CampaignContact.campaign_id == campaign.id,
                        or_(
                            CampaignContact.state == "pending",
                            CampaignContact.state == "waiting_retry",
                        ),
                        CampaignContact.next_attempt_at <= now_utc,
                    )
                )
                .order_by(CampaignContact.next_attempt_at)
                .limit(free_slots)
                .with_for_update(skip_locked=True)
            )
            due_contacts = due_result.scalars().all()

            for cc in due_contacts:
                # Defence: skip opted_out / dnd / no consent
                contact = await session.get(Contact, cc.contact_id)
                if not contact:
                    cc.state = "skipped"
                    continue
                if contact.opted_out or contact.dnd or not contact.consent:
                    cc.state = "skipped"
                    continue

                cc.state = "in_call"
                _incr_active_calls(str(campaign.id))

                from app.telephony.tasks import place_call as place_call_task
                place_call_task.delay(str(cc.id))

        await session.commit()


# ── Place call ────────────────────────────────────────────────────────────────

async def execute_place_call(campaign_contact_id: UUID) -> None:
    """
    Create a calls row and initiate the call via the provider.
    """
    try:
        from app.db.session import get_db_session
        from app.db.models import Call, CampaignContact, Contact, Campaign
    except ImportError:
        log.warning("execute_place_call_no_db")
        return

    from app.telephony.providers.factory import get_provider

    now_utc = datetime.now(tz=timezone.utc)
    provider = get_provider()

    async with get_db_session() as session:
        cc = await session.get(CampaignContact, campaign_contact_id)
        if not cc:
            log.error("place_call_cc_not_found", cc_id=str(campaign_contact_id))
            return

        campaign = await session.get(Campaign, cc.campaign_id)
        contact = await session.get(Contact, cc.contact_id)

        if not campaign or not contact:
            log.error("place_call_missing_data", cc_id=str(campaign_contact_id))
            return

        # Decrypt phone (only here)
        try:
            from app.security.crypto import reveal_phone
            phone = reveal_phone(contact)
        except Exception:  # noqa: BLE001
            # Crypto not implemented yet — use a safe stub for development
            log.warning("reveal_phone_stub", contact_id=str(contact.id))
            phone = f"+9199999{str(contact.id)[-4:]}"

        call_id = uuid.uuid4()
        attempt_no = (cc.attempts or 0) + 1

        flow_url = (
            f"{settings.public_base_url}/webhooks/{settings.webhook_secret}"
            f"/flow?call_id={call_id}"
        )
        status_callback_url = (
            f"{settings.public_base_url}/webhooks/{settings.webhook_secret}"
            f"/status?call_id={call_id}"
        )

        from app.telephony.providers.base import PlaceCallRequest
        req = PlaceCallRequest(
            call_id=call_id,
            to_number=phone,
            caller_id=campaign.caller_id or settings.exotel_caller_id,
            status_callback_url=status_callback_url,
            flow_url=flow_url,
            custom_field=str(call_id),
            time_limit_sec=120,
        )

        # Create the call row
        call = Call(
            id=call_id,
            campaign_contact_id=campaign_contact_id,
            attempt_no=attempt_no,
            provider=provider.name,
            status="initiated",
            flow_state={},
            created_at=now_utc,
        )
        session.add(call)
        cc.attempts = attempt_no
        await session.flush()

        # Initiate with the provider
        try:
            result = await provider.place_call(req)
            call.provider_call_sid = result.provider_call_sid
            call.status = result.raw_status
        except Exception as exc:  # noqa: BLE001
            log.error(
                "place_call_provider_error",
                call_id=str(call_id),
                error=str(exc),
            )
            call.status = "failed"
            call.outcome = "failed"
            call.ended_at = now_utc

            retry_policy = campaign.retry_policy or DEFAULT_RETRY_POLICY
            tz = campaign.timezone or "Asia/Kolkata"
            window_start = campaign.calling_window_start or time(9, 0)
            window_end = campaign.calling_window_end or time(21, 0)
            max_attempts = cc.max_attempts_override or campaign.max_attempts or 3

            new_state, next_at, final_outcome = schedule_next_attempt(
                "failed", attempt_no, max_attempts,
                retry_policy, now_utc, tz, window_start, window_end,
            )
            cc.state = new_state
            cc.last_outcome = "failed"
            cc.next_attempt_at = next_at
            cc.last_call_at = now_utc
            if final_outcome:
                cc.final_outcome = final_outcome

            _decr_active_calls(str(campaign.id))
            await session.commit()
            raise

        await session.commit()
        log.info(
            "place_call_initiated",
            call_id=str(call_id),
            sid=result.provider_call_sid,
            phone_last4=phone[-4:],
        )


# ── Sweeper ───────────────────────────────────────────────────────────────────

async def sweep_stuck() -> None:
    """
    Any call stuck in initiated|ringing|in_progress for >15 min → failed.
    Release the concurrency slot and apply retry logic.
    """
    try:
        from app.db.session import get_db_session
        from app.db.models import Call, CampaignContact, Campaign
    except ImportError:
        log.warning("sweep_stuck_no_db")
        return

    now_utc = datetime.now(tz=timezone.utc)
    cutoff = now_utc - timedelta(minutes=15)

    from sqlalchemy import select, and_, or_

    async with get_db_session() as session:
        stuck_result = await session.execute(
            select(Call).where(
                and_(
                    or_(
                        Call.status == "initiated",
                        Call.status == "ringing",
                        Call.status == "in_progress",
                    ),
                    Call.created_at <= cutoff,
                )
            ).with_for_update(skip_locked=True)
        )
        stuck_calls = stuck_result.scalars().all()

        for call in stuck_calls:
            log.warning(
                "sweep_stuck_call",
                call_id=str(call.id),
                status=call.status,
                age_minutes=int((now_utc - call.created_at).total_seconds() / 60),
            )
            call.status = "failed"
            call.outcome = "failed"
            call.hangup_cause = "timeout"
            call.ended_at = now_utc

            cc = await session.get(CampaignContact, call.campaign_contact_id)
            if cc:
                campaign = await session.get(Campaign, cc.campaign_id)
                retry_policy = (campaign.retry_policy or DEFAULT_RETRY_POLICY) if campaign else DEFAULT_RETRY_POLICY
                tz = (campaign.timezone or "Asia/Kolkata") if campaign else "Asia/Kolkata"
                window_start = (campaign.calling_window_start or time(9, 0)) if campaign else time(9, 0)
                window_end = (campaign.calling_window_end or time(21, 0)) if campaign else time(21, 0)
                max_attempts = (cc.max_attempts_override or (campaign.max_attempts if campaign else 3) or 3)

                new_state, next_at, final_outcome = schedule_next_attempt(
                    "failed", cc.attempts, max_attempts,
                    retry_policy, now_utc, tz, window_start, window_end,
                )
                cc.state = new_state
                cc.last_outcome = "failed"
                cc.next_attempt_at = next_at
                cc.last_call_at = now_utc
                if final_outcome:
                    cc.final_outcome = final_outcome

                if campaign:
                    _decr_active_calls(str(campaign.id))

        await session.commit()
        if stuck_calls:
            log.info("sweep_stuck_complete", swept=len(stuck_calls))


# ── Concurrency slot release ──────────────────────────────────────────────────

def release_slot(campaign_id: str) -> None:
    """Decrement the active-calls counter. Called on call finalisation."""
    _decr_active_calls(campaign_id)
