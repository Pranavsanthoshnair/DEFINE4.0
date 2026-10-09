"""
Unit tests for TwilioProvider (calling, TwiML rendering, webhook parsing).
"""

from uuid import uuid4
import pytest
from app.telephony.providers.base import (
    PlaceCallRequest,
    Play,
    Gather,
    Record,
    Hangup,
)
from app.telephony.providers.twilio import TwilioProvider, _normalize_phone_for_twilio


def test_twilio_phone_normalization():
    assert _normalize_phone_for_twilio("8075485080") == "+918075485080"
    assert _normalize_phone_for_twilio("+918075485080") == "+918075485080"
    assert _normalize_phone_for_twilio("+14155552671") == "+14155552671"
    assert _normalize_phone_for_twilio("08075485080") == "+918075485080"


def test_twilio_render_twiml_steps():
    provider = TwilioProvider()
    steps = [
        Play(audio_url="https://api.veylo.live/audio/welcome.wav"),
        Gather(prompt_audio_url="https://api.veylo.live/audio/press.wav", max_digits=1, finish_on_key="#"),
        Record(max_seconds=5, play_beep=True, silence_timeout_sec=2),
        Hangup(),
    ]
    resp = provider.render_steps(steps)
    assert resp.media_type == "application/xml"
    content = resp.body.decode("utf-8")
    assert "<Response>" in content
    assert "<Play>https://api.veylo.live/audio/welcome.wav</Play>" in content
    assert '<Gather numDigits="1" timeout="6" finishOnKey="#">' in content
    assert "<Record maxLength=\"5\" playBeep=\"true\" timeout=\"2\"/>" in content
    assert "<Hangup/>" in content


def test_twilio_parse_webhook_dtmf():
    provider = TwilioProvider()
    body = {
        "CallSid": "CA1234567890abcdef",
        "Digits": "1",
        "CallStatus": "in-progress",
    }
    event = provider.parse_webhook(kind="flow", headers={}, query={}, body=body)
    assert event.type == "dtmf"
    assert event.provider_call_sid == "CA1234567890abcdef"
    assert event.data["digits"] == "1"


def test_twilio_parse_webhook_completion():
    provider = TwilioProvider()
    body = {
        "CallSid": "CA99999",
        "CallStatus": "completed",
        "CallDuration": "45",
    }
    event = provider.parse_webhook(kind="status", headers={}, query={}, body=body)
    assert event.type == "completed"
    assert event.data["status"] == "completed"
    assert event.data["duration"] == 45
