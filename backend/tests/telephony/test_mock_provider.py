"""
Unit tests for the MockProvider.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.telephony.providers.mock import MockProvider, _suffix, SCENARIOS
from app.telephony.providers.base import PlaceCallRequest, Gather, Play, Hangup, Record


def test_suffix_extracts_last_two_digits():
    assert _suffix("+919999900001") == "01"
    assert _suffix("+919999900010") == "10"
    assert _suffix("+919999900099") == "99"


def test_suffix_handles_short_number():
    assert _suffix("1") == "00"  # fallback default scenario


def test_scenarios_table_complete():
    """All 10 scenarios from the contract are present."""
    expected = {"01", "02", "03", "04", "05", "06", "07", "08", "09", "10"}
    assert expected == set(SCENARIOS.keys())


@pytest.mark.asyncio
async def test_place_call_returns_mock_sid():
    provider = MockProvider()
    req = PlaceCallRequest(
        call_id=uuid.uuid4(),
        to_number="+919999900001",
        caller_id="+918000000000",
        status_callback_url="http://localhost/webhooks/secret/status",
        flow_url="http://localhost/webhooks/secret/flow",
        custom_field=str(uuid.uuid4()),
    )
    with patch("asyncio.create_task"):
        result = await provider.place_call(req)
    assert result.accepted
    assert result.provider_call_sid.startswith("mock-")


def test_render_steps_play():
    provider = MockProvider()
    rendered = provider.render_steps([Play(audio_url="http://example.com/greeting.wav")])
    assert rendered["steps"][0]["action"] == "play"


def test_render_steps_gather():
    provider = MockProvider()
    rendered = provider.render_steps([Gather(prompt_audio_url="http://example.com/prompt.wav")])
    assert rendered["steps"][0]["action"] == "gather"


def test_render_steps_hangup():
    provider = MockProvider()
    rendered = provider.render_steps([Hangup()])
    assert rendered["steps"][0]["action"] == "hangup"


def test_render_steps_record():
    provider = MockProvider()
    rendered = provider.render_steps([Record()])
    assert rendered["steps"][0]["action"] == "record"


def test_parse_webhook_dtmf():
    provider = MockProvider()
    call_id = uuid.uuid4()
    event = provider.parse_webhook(
        kind="flow",
        headers={},
        query={"call_id": str(call_id)},
        body={
            "event_type": "dtmf",
            "provider_call_sid": "mock-abc123",
            "call_id": str(call_id),
            "digits": "1",
        },
    )
    assert event.type == "dtmf"
    assert event.data["digits"] == "1"
    assert event.call_id == call_id


def test_parse_webhook_amd_result():
    provider = MockProvider()
    call_id = uuid.uuid4()
    event = provider.parse_webhook(
        kind="flow",
        headers={},
        query={},
        body={
            "event_type": "amd_result",
            "provider_call_sid": "mock-abc",
            "call_id": str(call_id),
            "amd": "machine",
        },
    )
    assert event.type == "amd_result"
    assert event.data["amd"] == "machine"


def test_parse_webhook_completed():
    provider = MockProvider()
    call_id = uuid.uuid4()
    event = provider.parse_webhook(
        kind="status",
        headers={},
        query={},
        body={
            "event_type": "completed",
            "provider_call_sid": "mock-abc",
            "call_id": str(call_id),
            "status": "completed",
            "duration": 25,
        },
    )
    assert event.type == "completed"
    assert event.data["duration"] == 25


def test_idempotency_key_is_deterministic():
    provider = MockProvider()
    call_id = uuid.uuid4()
    body = {
        "event_type": "dtmf",
        "provider_call_sid": "mock-abc",
        "call_id": str(call_id),
        "digits": "1",
    }
    e1 = provider.parse_webhook("flow", {}, {}, body)
    e2 = provider.parse_webhook("flow", {}, {}, body)
    assert e1.idempotency_key == e2.idempotency_key
