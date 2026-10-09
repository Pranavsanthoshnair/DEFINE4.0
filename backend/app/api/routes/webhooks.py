"""
Webhooks route — receives Exotel call-status callbacks.

IMPORTANT: This handler is a STUB.
Real idempotent event processing is not yet implemented.
"""

from fastapi import APIRouter, Request, status
from fastapi.responses import PlainTextResponse
import structlog

log = structlog.get_logger()
router = APIRouter()


@router.post(
    "/exotel/call-status",
    status_code=status.HTTP_200_OK,
    response_class=PlainTextResponse,
)
async def exotel_call_status_webhook(request: Request) -> str:
    """
    Receives Exotel POST callback for call status updates.
    Expected form fields: CallSid, Status, From, To, Direction, etc.
    (Stub — idempotent event processing NOT YET IMPLEMENTED.)
    """
    form_data = await request.form()
    log.info(
        "webhook_received",
        source="exotel",
        call_sid=form_data.get("CallSid"),
        call_status=form_data.get("Status"),
    )
    # TODO: Parse, validate, and persist CallEvent; update CampaignRecipient outcome.
    return "OK"
