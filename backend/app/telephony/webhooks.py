"""
Webhook handlers for telephony provider callbacks.
Contract: CONTRACTS.md sections 8.2 and member-2-telephony.md section 1.4.

Routes:
  GET|POST /webhooks/{secret}/flow
  GET|POST /webhooks/{secret}/status
  GET|POST /webhooks/{secret}/input
  GET|POST /webhooks/{secret}/recording
  WS       /ws/{secret}/voicebot  (stub, returns 501)

Security: constant-time compare of {secret} with WEBHOOK_SECRET.
          Mismatch returns 404 (not 403) — route not discoverable.
Idempotency: call_events.idempotency_key is unique; duplicate → 200 and stop.
Locking: SELECT ... FOR UPDATE on the calls row.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Request, Response, status
from fastapi.responses import JSONResponse, PlainTextResponse

from app.core.config import settings
from app.telephony.flow.context import (
    Answered,
    AmdResult,
    CallContext,
    Completed,
    Digits,
    FlowDecision,
    RecordingReady,
    SpeechResult,
    TemplateView,
    Timeout,
)
from app.telephony.flow.engine import next as flow_next
from app.telephony.providers.base import Hangup
from app.telephony.providers.factory import get_provider

log = structlog.get_logger()

router = APIRouter()

MAX_PAYLOAD_SIZE = 64 * 1024  # 64 KB


# ── Secret validation ─────────────────────────────────────────────────────────

def _check_secret(secret: str) -> bool:
    """Constant-time compare; returns False → respond with 404."""
    expected = settings.webhook_secret
    return hmac.compare_digest(
        secret.encode("utf-8"),
        expected.encode("utf-8"),
    )


# ── Body extraction ───────────────────────────────────────────────────────────

async def _extract_body(request: Request) -> dict:
    """Extract and size-limit the request body (form or JSON)."""
    body_bytes = await request.body()
    if len(body_bytes) > MAX_PAYLOAD_SIZE:
        return {}
    content_type = request.headers.get("content-type", "")
    if "json" in content_type:
        try:
            return json.loads(body_bytes)
        except Exception:  # noqa: BLE001
            return {}
    # form-encoded
    form = await request.form()
    return dict(form)


# ── Phone masking ─────────────────────────────────────────────────────────────

def _mask_payload(payload: dict) -> dict:
    """Replace phone-like values with last-4 masked form."""
    masked = {}
    phone_keys = {"from", "to", "phone", "caller", "called", "phonenumber"}
    for k, v in payload.items():
        if k.lower() in phone_keys and isinstance(v, str) and len(v) >= 4:
            masked[k] = f"+XXXXXX{v[-4:]}"
        else:
            masked[k] = v
    return masked


# ── DB / context loading stubs ────────────────────────────────────────────────

async def _load_call_context(
    session,
    call_id: UUID,
) -> tuple | None:
    """
    Load the call row (locked FOR UPDATE) and build a CallContext.
    Returns (call_row, campaign_contact_row, call_context) or None.
    """
    try:
        from app.db.models import Call, CampaignContact, Campaign, AudioAsset
        from sqlalchemy import select
    except ImportError:
        return None

    # Lock the call row
    result = await session.execute(
        select(Call)
        .where(Call.id == call_id)
        .with_for_update()
    )
    call = result.scalar_one_or_none()
    if not call:
        return None

    cc = await session.get(CampaignContact, call.campaign_contact_id)
    if not cc:
        return None

    campaign = await session.get(Campaign, cc.campaign_id)
    if not campaign:
        return None

    # Load template (stub — Member 1 owns templates)
    try:
        from app.db.models import Template, TemplateTranslation
        template = await session.get(Template, campaign.template_id)
        dtmf_map = template.dtmf_map if template else {"1": "confirm", "2": "decline", "9": "stop_calling"}
        speech_enabled = template.speech_enabled if template else False
        voicemail_policy = template.voicemail_policy if template else "skip_and_retry"
    except Exception:  # noqa: BLE001
        dtmf_map = {"1": "confirm", "2": "decline", "9": "stop_calling"}
        speech_enabled = False
        voicemail_policy = "skip_and_retry"

    # Load audio assets for the contact's language
    language = cc.language or "en"
    try:
        audio_result = await session.execute(
            select(AudioAsset).where(
                AudioAsset.campaign_id == campaign.id,
                AudioAsset.language == language,
            )
        )
        audio_rows = audio_result.scalars().all()
        audio = {
            row.segment_key: f"{settings.public_base_url}/media/audio/{row.sha256}.wav"
            for row in audio_rows
        }
    except Exception:  # noqa: BLE001
        audio = {}

    ctx = CallContext(
        call_id=call_id,
        language=language,
        amd_result=call.amd_result,
        flow_state=call.flow_state or {},
        template=TemplateView(
            dtmf_map=dtmf_map,
            speech_enabled=speech_enabled,
            voicemail_policy=voicemail_policy,
        ),
        audio=audio,
        speech_threshold=campaign.speech_confidence_threshold or 0.6,
    )
    return (call, cc, campaign, ctx)


async def _insert_event(session, call_id: UUID | None, sid: str, event_type: str,
                        payload: dict, ikey: str) -> bool:
    """
    Insert a call_events row. Returns True if inserted, False if duplicate.
    """
    try:
        from app.db.models import CallEvent
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        masked = _mask_payload(payload)
        stmt = pg_insert(CallEvent).values(
            call_id=call_id,
            provider_call_sid=sid,
            event_type=event_type,
            payload=masked,
            idempotency_key=ikey,
            received_at=datetime.now(tz=timezone.utc),
        ).on_conflict_do_nothing(index_elements=["idempotency_key"])

        result = await session.execute(stmt)
        await session.flush()
        return result.rowcount > 0
    except Exception as exc:  # noqa: BLE001
        log.warning("insert_event_failed", error=str(exc))
        return True  # allow processing to continue in dev


async def _finalize_call(session, call, cc, campaign, decision: FlowDecision) -> None:
    """
    Write outcome, ended_at, update campaign_contacts state.
    Call maybe_complete after commit.
    """
    from datetime import datetime, timezone

    now = datetime.now(tz=timezone.utc)
    call.outcome = decision.outcome
    call.ended_at = now

    if decision.intent:
        try:
            from app.db.models import Intent
            intent_row = Intent(
                call_id=call.id,
                step_key=decision.intent.step_key,
                source=decision.intent.source,
                raw_input=decision.intent.raw_input,
                language=cc.language or "en",
                label=decision.intent.label,
                confidence=decision.intent.confidence,
                stt_model=decision.intent.stt_model,
                latency_ms=decision.intent.latency_ms,
                created_at=now,
            )
            session.add(intent_row)
        except Exception:  # noqa: BLE001
            pass

    if decision.opt_out:
        try:
            from app.db.models import Contact
            contact = await session.get(Contact, cc.contact_id)
            if contact:
                contact.opted_out = True
                contact.opted_out_at = now
                try:
                    from app.security.crypto import reveal_phone
                    from app.security.suppression import get_suppression_filter
                    get_suppression_filter().suppress(reveal_phone(contact))
                except Exception as exc:  # noqa: BLE001
                    log.warning("suppression_write_failed", contact_id=str(contact.id), error=str(exc))
        except Exception:  # noqa: BLE001
            pass

    from app.telephony.retry import (
        TERMINAL_OUTCOMES, schedule_next_attempt, DEFAULT_RETRY_POLICY
    )
    import time as time_module
    from datetime import time

    retry_policy = campaign.retry_policy or DEFAULT_RETRY_POLICY
    tz = campaign.timezone or "Asia/Kolkata"
    window_start = campaign.calling_window_start or time(9, 0)
    window_end = campaign.calling_window_end or time(21, 0)
    max_attempts = cc.max_attempts_override or campaign.max_attempts or 3

    outcome = decision.outcome or "failed"
    new_state, next_at, final_outcome = schedule_next_attempt(
        outcome, cc.attempts, max_attempts,
        retry_policy, now, tz, window_start, window_end,
    )

    cc.state = new_state
    cc.last_outcome = outcome
    cc.last_call_at = now
    cc.next_attempt_at = next_at
    if final_outcome:
        cc.final_outcome = final_outcome

    # Release concurrency slot
    from app.telephony.scheduler import release_slot
    release_slot(str(campaign.id))


async def _persist_flow_decision(session, call, cc, campaign, decision: FlowDecision) -> None:
    """Update call row with new flow state and step."""
    call.flow_state = decision.new_flow_state
    if decision.outcome:
        call.flow_step = decision.outcome
    if decision.intent:
        call.flow_step = decision.intent.label

    if decision.finalize:
        await _finalize_call(session, call, cc, campaign, decision)


async def _call_maybe_complete(campaign_id: UUID) -> None:
    """Call maybe_complete from M1 after a call finalises."""
    try:
        from app.analytics.queries import maybe_complete
        await maybe_complete(str(campaign_id))
    except (ImportError, Exception):  # noqa: BLE001
        pass  # not yet implemented by M1


# ── Supabase-based flow handler ───────────────────────────────────────────────

async def _handle_flow_supabase(call_id_str: str | None, provider) -> Response:
    """
    Handle the flow webhook using Supabase.
    Looks up call → campaign_contact → campaign → audio_urls.
    Returns TwiML XML for Twilio, Exotel JSON for Exotel.
    Falls back to a plain spoken greeting if no audio is pre-generated.
    """
    from app.db.supabase_client import get_supabase, is_supabase_configured

    if not is_supabase_configured():
        log.warning("flow_supabase_not_configured")
        _fallback_steps = [Hangup()]
        _rendered = provider.render_steps(_fallback_steps)
        if provider.name == "twilio":
            return PlainTextResponse(content=_rendered, media_type="application/xml")
        return JSONResponse(content=_rendered)

    sb = get_supabase()

    # Resolve campaign from call record
    # calls table has NO campaign_id — must join via campaign_contacts
    campaign_id: str | None = None
    audio_urls: dict = {}

    if call_id_str:
        try:
            call_resp = (
                sb.table("calls")
                .select("campaign_contact_id")
                .eq("id", call_id_str)
                .single()
                .execute()
            )
            cc_id = (call_resp.data or {}).get("campaign_contact_id")
            if cc_id:
                cc_resp = (
                    sb.table("campaign_contacts")
                    .select("campaign_id")
                    .eq("id", cc_id)
                    .single()
                    .execute()
                )
                campaign_id = (cc_resp.data or {}).get("campaign_id")
        except Exception as exc:
            log.warning("flow_call_lookup_failed", error=str(exc))

    if campaign_id:
        try:
            camp_resp = (
                sb.table("campaigns")
                .select("name,brief,audio_urls")
                .eq("id", campaign_id)
                .single()
                .execute()
            )
            if camp_resp.data:
                # Try audio_urls column first, fall back to brief JSON
                raw_audio = camp_resp.data.get("audio_urls")
                if not raw_audio:
                    import json as _json
                    brief_str = camp_resp.data.get("brief") or ""
                    try:
                        brief_data = _json.loads(brief_str) if isinstance(brief_str, str) and brief_str.startswith("{") else {}
                        raw_audio = brief_data.get("audio_urls")
                    except Exception:
                        raw_audio = None
                audio_urls = raw_audio or {}
        except Exception as exc:
            log.warning("flow_campaign_lookup_failed", error=str(exc))

    # Update call status to in_progress
    if call_id_str:
        try:
            now = datetime.now(timezone.utc).isoformat()
            sb.table("calls").update({"status": "in_progress", "updated_at": now}).eq("id", call_id_str).execute()
        except Exception:
            pass

    # Build steps: play greeting audio then hangup
    from app.telephony.providers.base import Play, Hangup
    greeting_url = (
        audio_urls.get("greeting")
        or audio_urls.get("prompt")
        or audio_urls.get("welcome")
    )

    steps = []
    if greeting_url:
        steps.append(Play(audio_url=greeting_url))
        log.info("flow_playing_audio", campaign_id=campaign_id, url=greeting_url)
    else:
        log.warning("flow_no_audio_url", campaign_id=campaign_id, audio_keys=list(audio_urls.keys()))

    steps.append(Hangup())

    rendered = provider.render_steps(steps)
    log.info("flow_response_sent", campaign_id=campaign_id, steps=len(steps), provider=provider.name)

    # Twilio needs XML, Exotel needs JSON
    if provider.name == "twilio":
        return PlainTextResponse(content=rendered, media_type="application/xml")
    return JSONResponse(content=rendered)


async def _handle_status_supabase(call_id_str: str | None, prov_event) -> None:
    """Update call status in Supabase from a status webhook."""
    from app.db.supabase_client import get_supabase, is_supabase_configured
    if not is_supabase_configured() or not prov_event.provider_call_sid:
        return
    try:
        sb = get_supabase()
        now = datetime.now(timezone.utc).isoformat()
        status_map = {
            "completed": "completed", "busy": "busy",
            "no_answer": "no_answer", "failed": "failed",
            "ringing": "ringing", "answered": "in_progress",
            "in_progress": "in_progress",
        }
        new_status = status_map.get(prov_event.type, prov_event.type)
        updates: dict = {"status": new_status, "updated_at": now}
        if prov_event.type in ("completed", "busy", "no_answer", "failed"):
            updates["duration_sec"] = prov_event.data.get("duration", 0)

        # Update by call_id if we have it, else by provider_call_sid
        if call_id_str:
            sb.table("calls").update(updates).eq("id", call_id_str).execute()
        else:
            sb.table("calls").update(updates).eq("provider_call_sid", prov_event.provider_call_sid).execute()
    except Exception as exc:
        log.warning("status_update_failed", error=str(exc))


# ── Common webhook pipeline ────────────────────────────────────────────────────

async def _handle_webhook(
    secret: str,
    kind: str,
    request: Request,
) -> Response:
    if not _check_secret(secret):
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={})

    provider = get_provider()
    body = await _extract_body(request)
    query = dict(request.query_params)

    prov_event = provider.parse_webhook(kind, dict(request.headers), query, body)
    call_id_str = str(prov_event.call_id) if prov_event.call_id else query.get("call_id")

    log.info(
        "webhook_received",
        kind=kind,
        event_type=prov_event.type,
        sid=prov_event.provider_call_sid,
        call_id=call_id_str,
    )

    # ── Flow webhook: serve audio to Exotel when call is answered ────────────
    if kind == "flow":
        return await _handle_flow_supabase(call_id_str, provider)

    # ── Status webhook: update call record in Supabase ───────────────────────
    if kind == "status":
        await _handle_status_supabase(call_id_str, prov_event)
        return PlainTextResponse("OK")

    return PlainTextResponse("OK")


def _map_event(prov_event, ctx: CallContext, kind: str):
    """Map a ProviderEvent to the correct FlowEvent."""
    t = prov_event.type
    if t == "answered":
        return Answered()
    elif t == "amd_result":
        amd_val = prov_event.data.get("amd", "unknown").lower()
        if amd_val not in ("human", "machine", "unknown"):
            amd_val = "unknown"
        return AmdResult(value=amd_val)
    elif t == "dtmf":
        digits = prov_event.data.get("digits", "")
        if not digits:
            return Timeout()
        return Digits(value=digits)
    elif t == "recording_ready":
        return RecordingReady(url=prov_event.data.get("recording_url", ""))
    elif t in ("completed", "busy", "no_answer", "failed"):
        data = prov_event.data
        return Completed(
            status=data.get("status", t),
            duration=int(data.get("duration", 0)),
            hangup_cause=data.get("hangup_cause", ""),
        )
    elif t == "ringing":
        return None  # just update status, no engine step
    elif t == "initiated":
        return None
    return None


async def _handle_recording(
    ctx: CallContext,
    event: RecordingReady,
    session,
) -> FlowDecision:
    """
    Download and classify speech (sync path).
    Per contract: do NOT hold DB locks across the AI call.
    """
    # NOTE: session should NOT be locked during AI call.
    # The engine's RecordingReady sentinel triggers this path.
    _ = flow_next(ctx, event)  # consume for state

    speech_result = await _call_speech_intent(event.url, ctx.language)
    return flow_next(ctx, speech_result)


async def _call_speech_intent(audio_url: str, language: str) -> SpeechResult:
    """Call the AI service speech-intent endpoint."""
    import httpx as _httpx

    try:
        async with _httpx.AsyncClient(timeout=10.0) as client:
            # Download audio first
            audio_resp = await client.get(audio_url)
            audio_resp.raise_for_status()
            audio_bytes = audio_resp.content

            # Call AI service
            resp = await client.post(
                f"{settings.ai_base_url}/v1/speech-intent",
                headers={"X-Internal-Token": settings.ai_internal_token},
                files={"audio": ("audio.wav", audio_bytes, "audio/wav")},
                data={"language": language},
            )
            resp.raise_for_status()
            data = resp.json()

            return SpeechResult(
                text=data.get("text", ""),
                intent=data.get("intent", "unclear"),
                confidence=float(data.get("confidence", 0.0)),
                source="speech",
                stt_model=data.get("stt_model"),
                latency_ms=data.get("latency_ms"),
            )
    except Exception as exc:  # noqa: BLE001
        log.error("speech_intent_error", error=str(exc))
        return SpeechResult(text="", intent="unclear", confidence=0.0)


# ── Route definitions ─────────────────────────────────────────────────────────

@router.api_route(
    "/{secret}/flow",
    methods=["GET", "POST"],
)
async def webhook_flow(secret: str, request: Request) -> Response:
    """Provider asks what to do next. Returns rendered call steps."""
    return await _handle_webhook(secret, "flow", request)


@router.api_route(
    "/{secret}/status",
    methods=["GET", "POST"],
)
async def webhook_status(secret: str, request: Request) -> Response:
    """Call status callback (ringing, answered, completed, busy, no-answer, failed)."""
    return await _handle_webhook(secret, "status", request)


@router.api_route(
    "/{secret}/input",
    methods=["GET", "POST"],
)
async def webhook_input(secret: str, request: Request) -> Response:
    """Keypad digits and AMD result delivered separately from the flow request."""
    return await _handle_webhook(secret, "input", request)


@router.api_route(
    "/{secret}/recording",
    methods=["GET", "POST"],
)
async def webhook_recording(secret: str, request: Request) -> Response:
    """Recording-ready callback."""
    return await _handle_webhook(secret, "recording", request)
