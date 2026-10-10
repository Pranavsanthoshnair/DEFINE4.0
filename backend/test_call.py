"""
Quick CLI tool to place a live test call via Twilio (or active telephony provider).
Usage:
    python test_call.py <phone_number> [optional_message]

Example:
    python test_call.py +919876543210 "Hello, this is a test call from Veylo."
"""

import asyncio
import sys
import uuid

from app.core.config import settings
from app.telephony.providers.base import PlaceCallRequest
from app.telephony.providers.factory import active_provider_name, get_provider


async def main():
    if len(sys.argv) < 2:
        print("\nUsage: python test_call.py <phone_number> [optional_message]")
        print("Example: python test_call.py +919876543210 \"Hello from Veylo!\"\n")
        sys.exit(1)

    to_number = sys.argv[1].strip()
    custom_msg = sys.argv[2] if len(sys.argv) > 2 else (
        "Hello! This is a live test call from your Veylo multilingual campaign platform. "
        "Your Twilio phone integration is fully operational."
    )

    provider = get_provider()
    active_name = active_provider_name()
    caller_id = (
        settings.twilio_phone_number if active_name == "twilio"
        else settings.exotel_caller_id
    )
    print(f"\n==========================================")
    print(f" Veylo Telephony Test Caller")
    print(f" Active Provider: {active_name.upper()}")
    print(f" Destination:     {to_number}")
    print(f" Caller ID:       {caller_id}")
    print(f"==========================================\n")

    call_id = uuid.uuid4()
    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<Response><Say language="en-IN">{custom_msg}</Say></Response>'
    )

    req = PlaceCallRequest(
        call_id=call_id,
        to_number=to_number,
        caller_id=caller_id,
        status_callback_url=f"{settings.public_base_url}/webhooks/{settings.webhook_secret}/status?call_id={call_id}",
        flow_url=f"{settings.public_base_url}/webhooks/{settings.webhook_secret}/flow?call_id={call_id}",
        custom_field=str(call_id),
        twiml=twiml,
    )

    print("Placing outbound call...")
    try:
        res = await provider.place_call(req)
        if res.accepted:
            print("\n>>> Call successfully queued!")
            print(f"Call SID: {res.provider_call_sid}")
            print(f"Status:   {res.raw_status}")
            print("\nYour phone should ring shortly.")
        else:
            print(f"\n[ERROR] Provider rejected call: {res.raw_status}")
    except Exception as exc:
        print(f"\n[EXCEPTION] Failed to place call: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
