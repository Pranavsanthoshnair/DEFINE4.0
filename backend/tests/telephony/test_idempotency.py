"""
Tests for webhook idempotency key helper.
"""

from __future__ import annotations

from app.telephony.providers.base import make_idempotency_key


def test_idempotency_key_is_sha256():
    key = make_idempotency_key("mock", "abc123", "answered", "{}")
    assert len(key) == 64


def test_idempotency_key_same_inputs_same_output():
    k1 = make_idempotency_key("mock", "abc123", "dtmf", '{"digits":"1"}')
    k2 = make_idempotency_key("mock", "abc123", "dtmf", '{"digits":"1"}')
    assert k1 == k2


def test_idempotency_key_different_inputs_different_output():
    k1 = make_idempotency_key("mock", "abc123", "dtmf", '{"digits":"1"}')
    k2 = make_idempotency_key("mock", "abc123", "dtmf", '{"digits":"2"}')
    assert k1 != k2


def test_idempotency_key_different_provider():
    k1 = make_idempotency_key("mock", "abc123", "dtmf", "{}")
    k2 = make_idempotency_key("exotel", "abc123", "dtmf", "{}")
    assert k1 != k2
