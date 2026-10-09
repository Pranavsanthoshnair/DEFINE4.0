"""
Webhooks route — receives Exotel & Twilio call-status callbacks.

POST /api/v1/webhooks/exotel/call-status
POST /api/v1/webhooks/twilio/call-status

Both handlers are idempotent — safe to receive duplicate posts.
"""

from fastapi import APIRouter, Request, status
from fastapi.responses import PlainTextResponse
import structlog

from app.db.supabase_client import get_supabase, is_supabase_configured

log = structlog.get_logger()
router = APIRouter()

_CALLS_TABLE = "calls"
_SESSIONS_TABLE = "execution_sessions"


def _status_to_outcome(status_str: str) -> str:
    """Normalise provider status strings to internal outcome values."""
    s = status_str.lower()
    if s in ("completed", "answered"):
        return "completed"
    if s in ("busy",):
        return "busy"
    if s in ("no-answer", "no_answer", "noanswer"):
        return "no_answer"
    if s in ("failed", "error"):
        return "failed"
    if s in ("canceled", "cancelled"):
        return "cancelled"
    return s


async def _upsert_call_record(
    provider: str,
    provider_call_sid: str,
    call_id: str | None,
    campaign_id: str | None,
    to_number: str | None,
    status_str: str,
    duration_sec: int | None,
) -> None:
    """Upsert a call record in Supabase (idempotent on provider_call_sid)."""
    if not is_supabase_configured():
        return
    try:
        sb = get_supabase()
        outcome = _status_to_outcome(status_str)
        row: dict = {
            "provider": provider,
            "provider_call_sid": provider_call_sid,
            "status": outcome,
            "outcome": outcome,
            "updated_at": __import__("datetime").datetime.utcnow().isoformat(),
        }
        if call_id:
            row["id"] = call_id
        if campaign_id:
            row["campaign_id"] = campaign_id
        if to_number:
            # Store only last-4 for PII compliance
            row["phone_last4"] = to_number[-4:] if len(to_number) >= 4 else to_number
        if duration_sec is not None:
            row["duration_sec"] = duration_sec

        sb.table(_CALLS_TABLE).upsert(row, on_conflict="provider_call_sid").execute()

        # Mirror outcome onto the matching execution session (if any)
        if call_id:
            sb.table(_SESSIONS_TABLE).update(
                {"status": "completed", "outcome": outcome, "updated_at": row["updated_at"]}
            ).eq("id", call_id).execute()

        log.info(
            "webhook_call_upserted",
            provider=provider,
            provider_call_sid=provider_call_sid,
            outcome=outcome,
        )
    except Exception as exc:
        log.error("webhook_upsert_failed", error=str(exc))


@router.post(
    "/exotel/call-status",
    status_code=status.HTTP_200_OK,
    response_class=PlainTextResponse,
)
async def exotel_call_status_webhook(request: Request) -> str:
    """
    Receives Exotel POST callback for call status updates.
    Expected form fields: CallSid, Status, From, To, Direction, Duration.
    Idempotent — upserts on CallSid.
    """
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "")
    call_status = form_data.get("Status", "unknown")
    to_number = str(form_data.get("To", ""))
    duration = form_data.get("Duration")
    custom_field = str(form_data.get("CustomField", ""))  # str(call_id) set by us

    log.info(
        "webhook_exotel_received",
        call_sid=call_sid,
        status=call_status,
    )

    duration_sec: int | None = None
    try:
        duration_sec = int(duration) if duration else None
    except (TypeError, ValueError):
        pass

    await _upsert_call_record(
        provider="exotel",
        provider_call_sid=call_sid,
        call_id=custom_field or None,
        campaign_id=None,
        to_number=to_number,
        status_str=call_status,
        duration_sec=duration_sec,
    )
    return "OK"


@router.post(
    "/twilio/call-status",
    status_code=status.HTTP_200_OK,
    response_class=PlainTextResponse,
)
async def twilio_call_status_webhook(request: Request) -> str:
    """
    Receives Twilio POST callback for call status updates.
    Expected form fields: CallSid, CallStatus, To, CallDuration.
    Idempotent — upserts on CallSid.
    """
    form_data = await request.form()
    call_sid = str(form_data.get("CallSid", ""))
    call_status = str(form_data.get("CallStatus", "unknown"))
    to_number = str(form_data.get("To", ""))
    duration = form_data.get("CallDuration")
    custom_field = str(form_data.get("StatusCallbackEvent", ""))

    log.info(
        "webhook_twilio_received",
        call_sid=call_sid,
        status=call_status,
    )

    duration_sec_val: int | None = None
    try:
        duration_sec_val = int(duration) if duration else None
    except (TypeError, ValueError):
        pass

    await _upsert_call_record(
        provider="twilio",
        provider_call_sid=call_sid,
        call_id=None,
        campaign_id=None,
        to_number=to_number,
        status_str=call_status,
        duration_sec=duration_sec_val,
    )
    return ""
