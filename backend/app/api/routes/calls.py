"""Calls routes — call list, initiation and testing."""

import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.db.supabase_client import get_supabase, is_supabase_configured
from app.telephony.providers.base import PlaceCallRequest
from app.telephony.providers.factory import active_provider_name, get_provider

router = APIRouter()


class TestCallRequest(BaseModel):
    phone_number: str = Field(..., description="Phone number to call (e.g. +919876543210 or 9876543210)")
    message: Optional[str] = Field(
        None,
        description="Optional custom message to say when the call connects"
    )
    language: str = Field("en-IN", description="Language code for speech (e.g. en-IN, hi-IN)")


class InitiateCallRequest(BaseModel):
    campaign_id: Optional[str] = None
    recipient_id: Optional[str] = None
    phone_number: Optional[str] = None
    message: Optional[str] = None


class CallAttemptOut(BaseModel):
    id: str
    status: str
    provider: str
    provider_call_sid: str
    message: str


class CallRecord(BaseModel):
    id: str
    campaign_id: Optional[str] = None
    campaign_contact_id: Optional[str] = None
    status: str
    outcome: Optional[str] = None
    duration_sec: Optional[int] = None
    created_at: str
    contact: Optional[str] = None
    intent: Optional[str] = None
    confidence: Optional[float] = None
    method: Optional[str] = None
    lang: Optional[str] = None
    transcript: Optional[str] = None


@router.get("/", response_model=List[CallRecord])
async def list_calls(
    campaign_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List call records, optionally filtered by campaign via campaign_contacts join."""
    if not is_supabase_configured():
        return []
    try:
        sb = get_supabase()
        if campaign_id:
            # calls has no campaign_id — join via campaign_contacts
            cc_resp = (
                sb.table("campaign_contacts")
                .select("id")
                .eq("campaign_id", campaign_id)
                .execute()
            )
            cc_ids = [r["id"] for r in (cc_resp.data or [])]
            if not cc_ids:
                return []
            q = (
                sb.table("calls")
                .select("id,campaign_contact_id,status,outcome,duration_sec,created_at")
                .in_("campaign_contact_id", cc_ids)
                .order("created_at", desc=True)
                .range(offset, offset + limit - 1)
            )
        else:
            q = (
                sb.table("calls")
                .select("id,campaign_contact_id,status,outcome,duration_sec,created_at")
                .order("created_at", desc=True)
                .range(offset, offset + limit - 1)
            )
        resp = q.execute()
        rows = resp.data or []

        # Telegram replies are stored as execution_sessions, but belong in the
        # same history returned to the dashboard.
        session_query = (
            sb.table("execution_sessions")
            .select("id,campaign_id,status,outcome,created_at,intent,confidence,decision_method,language")
            .eq("execution_type", "TELEGRAM")
            .order("created_at", desc=True)
            .limit(limit)
        )
        if campaign_id:
            session_query = session_query.eq("campaign_id", campaign_id)
        rows.extend(session_query.execute().data or [])

        # Resolve contact details through campaign_contacts because calls stores
        # the campaign-contact link rather than a direct contact_id.
        link_by_id: dict[str, dict] = {}
        contact_by_id: dict[str, dict] = {}
        row_cc_ids = [str(r.get("campaign_contact_id")) for r in rows if r.get("campaign_contact_id")]
        if row_cc_ids:
            links_resp = (
                sb.table("campaign_contacts")
                .select("id,contact_id")
                .in_("id", row_cc_ids)
                .execute()
            )
            links = links_resp.data or []
            link_by_id = {str(link["id"]): link for link in links}
            contact_ids = [str(link["contact_id"]) for link in links if link.get("contact_id")]
            if contact_ids:
                contacts_resp = (
                    sb.table("contacts")
                    .select("id,phone_last4,language")
                    .in_("id", contact_ids)
                    .execute()
                )
                contact_by_id = {str(contact["id"]): contact for contact in (contacts_resp.data or [])}
        return [
            CallRecord(
                id=str(r["id"]),
                campaign_id=campaign_id or r.get("campaign_id"),
                campaign_contact_id=r.get("campaign_contact_id"),
                status=r.get("status", "unknown"),
                outcome=r.get("outcome"),
                duration_sec=r.get("duration_sec"),
                created_at=str(r.get("created_at", "")),
                contact=(f"••••{contact_by_id[str(link_by_id[str(r.get('campaign_contact_id'))].get('contact_id'))].get('phone_last4')}"
                         if str(r.get("campaign_contact_id")) in link_by_id and link_by_id[str(r.get("campaign_contact_id"))].get("contact_id") in contact_by_id else None),
                intent=r.get("intent"),
                confidence=r.get("confidence"),
                method=r.get("decision_method"),
                lang=(r.get("language") or contact_by_id.get(str(link_by_id.get(str(r.get("campaign_contact_id")), {}).get("contact_id")), {}).get("language")
                      or None),
            )
            for r in rows
        ]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database error: {exc}",
        )


@router.post("/test-call", response_model=CallAttemptOut, status_code=status.HTTP_200_OK)
async def test_call(payload: TestCallRequest):
    """
    Trigger a direct test call to any phone number using the active telephony provider (Twilio).
    """
    call_id = uuid.uuid4()
    provider = get_provider()

    twiml_say = payload.message or (
        "Hello! This is a test call from your Veylo multilingual outbound campaign platform. "
        "Your telephony integration is configured and working properly."
    )
    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<Response><Say language="{payload.language}">{twiml_say}</Say></Response>'
    )

    req = PlaceCallRequest(
        call_id=call_id,
        to_number=payload.phone_number,
        caller_id=settings.twilio_phone_number if provider.name == "twilio" else settings.exotel_caller_id,
        status_callback_url=f"{settings.public_base_url}/webhooks/{settings.webhook_secret}/status?call_id={call_id}",
        flow_url=f"{settings.public_base_url}/webhooks/{settings.webhook_secret}/flow?call_id={call_id}",
        custom_field=str(call_id),
        twiml=twiml,
    )

    result = await provider.place_call(req)
    if not result.accepted:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Telephony provider ({provider.name}) rejected the call: {result.raw_status}",
        )

    return CallAttemptOut(
        id=str(call_id),
        status=result.raw_status,
        provider=provider.name,
        provider_call_sid=result.provider_call_sid,
        message=f"Call successfully queued to {payload.phone_number} via {provider.name}.",
    )


@router.post("/initiate", response_model=CallAttemptOut, status_code=status.HTTP_202_ACCEPTED)
async def initiate_call(payload: InitiateCallRequest):
    """
    Initiate an outbound call for a recipient or direct phone number.
    """
    phone = payload.phone_number
    if not phone and payload.recipient_id:
        # In mock/dev without database lookup, construct placeholder or lookup contact
        phone = f"+9199999{payload.recipient_id[-4:]}"

    if not phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either phone_number or recipient_id must be provided.",
        )

    return await test_call(
        TestCallRequest(
            phone_number=phone,
            message=payload.message,
        )
    )

