"""
Unit tests for Keyed Scalable Bloom Filter (Blueprint H2).
"""

import pytest
from app.security.suppression import (
    normalize_e164,
    InvalidPhoneNumberError,
    ScalableSuppressionFilter,
)


def test_normalize_e164():
    assert normalize_e164("+91 98765 43210") == "+919876543210"
    assert normalize_e164("9876543210") == "+919876543210"
    assert normalize_e164("09876543210") == "+919876543210"
    assert normalize_e164("+1 (415) 555-2671") == "+14155552671"

    with pytest.raises(InvalidPhoneNumberError):
        normalize_e164("123")

    with pytest.raises(InvalidPhoneNumberError):
        normalize_e164("abc-def")


def test_bloom_filter_no_false_negatives():
    bloom = ScalableSuppressionFilter(initial_capacity=1000, initial_fpr=0.01, hmac_key="test-key-secret")

    numbers = [f"+9198765{i:05d}" for i in range(500)]
    for n in numbers:
        bloom.suppress(n)

    # Every inserted number MUST be detected as suppressed (0 false negatives)
    for n in numbers:
        assert bloom.is_suppressed(n) is True


def test_bloom_filter_false_positive_rate():
    bloom = ScalableSuppressionFilter(initial_capacity=2000, initial_fpr=0.01, hmac_key="test-key-secret")

    # Insert 1000 numbers
    inserted = [f"+9191111{i:05d}" for i in range(1000)]
    for n in inserted:
        bloom.suppress(n)

    # Query 1000 completely different numbers
    unseen = [f"+9199999{i:05d}" for i in range(1000)]
    false_positives = sum(1 for n in unseen if bloom.is_suppressed(n))

    # FPR should be reasonably small (< 3% on random sample with 1% target)
    measured_fpr = false_positives / len(unseen)
    assert measured_fpr < 0.03


def test_bloom_filter_scaling_layers():
    # Small capacity to trigger new layer addition
    bloom = ScalableSuppressionFilter(initial_capacity=50, initial_fpr=0.01, hmac_key="test-key-secret")

    for i in range(150):
        bloom.suppress(f"+9198888{i:05d}")

    # Should have scaled across layers
    stats = bloom.stats()
    assert stats["layer_count"] >= 2
    assert stats["total_items"] == 150

    # All items still match across layers
    for i in range(150):
        assert bloom.is_suppressed(f"+9198888{i:05d}") is True
