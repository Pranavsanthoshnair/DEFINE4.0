"""
Keyed Scalable Bloom Filter for Privacy-Preserving Contact Suppression (H2).

Solves the erasure-vs-suppression tension:
- When a contact requests erasure, their personal record is deleted.
- To prevent them from ever being called again, their phone number is inserted into
  a keyed Bloom filter as HMAC-SHA256(BLOOM_HMAC_KEY, E.164(phone)).
- The filter has ZERO false negatives (guaranteed never to call an opted-out person).
- False positives only cause a number to be safely skipped.

Honest limitations:
- Hides the list, not membership for someone holding the key (attacker with key can test known numbers).
- Standard Bloom filters do not support deletion; opt-outs are permanent in v1.
"""

from __future__ import annotations

import hmac
import hashlib
import math
import re
from typing import List, Dict, Any, Tuple


class InvalidPhoneNumberError(ValueError):
    """Raised when a phone number cannot be normalised to E.164 standard."""
    pass


def normalize_e164(raw: str) -> str:
    """Canonicalize a phone number to standard E.164 format (+[country_code][number]).

    Examples:
    - '9876543210' -> '+919876543210' (defaults to India +91 if 10 digits)
    - '+91 98765 43210' -> '+919876543210'
    - '09876543210' -> '+919876543210'
    """
    cleaned = re.sub(r"[\s\-\(\)\.]+", "", raw.strip())
    if not cleaned:
        raise InvalidPhoneNumberError("Empty phone number")

    if cleaned.startswith("+"):
        digits = cleaned[1:]
        if not digits.isdigit() or len(digits) < 7 or len(digits) > 15:
            raise InvalidPhoneNumberError(f"Invalid E.164 length: {raw}")
        return cleaned
    
    # Strip leading 0 if standard 11-digit national
    if cleaned.startswith("0") and len(cleaned) == 11:
        cleaned = cleaned[1:]

    # Default 10 digits to +91
    if len(cleaned) == 10 and cleaned.isdigit():
        return f"+91{cleaned}"

    if cleaned.isdigit() and 7 <= len(cleaned) <= 15:
        return f"+{cleaned}"

    raise InvalidPhoneNumberError(f"Unparseable phone number: {raw}")


class KeyedBloomFilterLayer:
    """A single layer of the scalable Bloom filter."""

    def __init__(self, layer_no: int, capacity: int, target_fpr: float, hmac_key: bytes) -> None:
        self.layer_no = layer_no
        self.capacity = capacity
        self.target_fpr = target_fpr
        self.hmac_key = hmac_key
        self.n_items = 0

        # Optimal bit size m and hash count k
        self.m_bits = max(64, math.ceil(-capacity * math.log(target_fpr) / (math.log(2) ** 2)))
        self.k = max(1, round((self.m_bits / capacity) * math.log(2)))
        
        # Byte array for bit storage
        self.byte_count = (self.m_bits + 7) // 8
        self.bit_array = bytearray(self.byte_count)

    def _get_hashes(self, item: str) -> List[int]:
        """Derive k bit positions using Kirsch-Mitzenmacher double hashing from HMAC-SHA256."""
        h = hmac.new(self.hmac_key, item.encode("utf-8"), hashlib.sha256).digest()
        h1 = int.from_bytes(h[:16], byteorder="big")
        h2 = int.from_bytes(h[16:32], byteorder="big")
        if h2 == 0:
            h2 = 1

        positions = []
        for i in range(self.k):
            pos = (h1 + i * h2) % self.m_bits
            positions.append(pos)
        return positions

    def add(self, item: str) -> bool:
        """Add item to layer. Returns True if successfully added."""
        positions = self._get_hashes(item)
        for pos in positions:
            byte_idx = pos // 8
            bit_idx = pos % 8
            self.bit_array[byte_idx] |= (1 << bit_idx)
        self.n_items += 1
        return True

    def contains(self, item: str) -> bool:
        """Check if item is probably in layer (no false negatives)."""
        positions = self._get_hashes(item)
        for pos in positions:
            byte_idx = pos // 8
            bit_idx = pos % 8
            if not (self.bit_array[byte_idx] & (1 << bit_idx)):
                return False
        return True

    @property
    def is_full(self) -> bool:
        return self.n_items >= self.capacity

    @property
    def fill_ratio(self) -> float:
        set_bits = sum(bin(b).count("1") for b in self.bit_array)
        return set_bits / self.m_bits if self.m_bits > 0 else 0.0

    @property
    def estimated_fpr(self) -> float:
        """Theoretical false-positive rate: (1 - e^(-k*n/m))^k."""
        if self.m_bits == 0:
            return 0.0
        exp_factor = - (self.k * self.n_items) / self.m_bits
        return (1.0 - math.exp(exp_factor)) ** self.k


class ScalableSuppressionFilter:
    """Scalable Keyed Bloom Filter that adds tighter layers as entries grow."""

    def __init__(self, initial_capacity: int = 10_000, initial_fpr: float = 0.001, hmac_key: str | bytes = "change-me-bloom-hmac-key") -> None:
        self.initial_capacity = initial_capacity
        self.initial_fpr = initial_fpr
        self.hmac_key = hmac_key.encode("utf-8") if isinstance(hmac_key, str) else hmac_key
        self.layers: List[KeyedBloomFilterLayer] = []
        self._add_layer()

    def _add_layer(self) -> KeyedBloomFilterLayer:
        layer_no = len(self.layers)
        # Tighten FPR by factor of 0.85 per layer
        layer_fpr = self.initial_fpr * (0.85 ** layer_no)
        layer_capacity = int(self.initial_capacity * (2 ** layer_no))
        new_layer = KeyedBloomFilterLayer(layer_no, layer_capacity, layer_fpr, self.hmac_key)
        self.layers.append(new_layer)
        return new_layer

    def suppress(self, raw_number: str) -> bool:
        """Normalise phone and insert into active suppression layer."""
        canonical = normalize_e164(raw_number)
        active_layer = self.layers[-1]
        if active_layer.is_full:
            active_layer = self._add_layer()
        return active_layer.add(canonical)

    def is_suppressed(self, raw_number: str) -> bool:
        """Check all filter layers. True if suppressed in any layer."""
        try:
            canonical = normalize_e164(raw_number)
        except InvalidPhoneNumberError:
            return True # Malformed numbers are rejected at checkpoint
        
        for layer in self.layers:
            if layer.contains(canonical):
                return True
        return False

    def stats(self) -> Dict[str, Any]:
        """Summary metrics for the admin suppression panel and privacy audit."""
        total_items = sum(layer.n_items for layer in self.layers)
        layer_stats = []
        for l in self.layers:
            layer_stats.append({
                "layer_no": l.layer_no,
                "capacity": l.capacity,
                "n_items": l.n_items,
                "k": l.k,
                "m_bits": l.m_bits,
                "fill_ratio": round(l.fill_ratio, 4),
                "estimated_fpr": round(l.estimated_fpr, 6),
            })
        return {
            "total_items": total_items,
            "layer_count": len(self.layers),
            "layers": layer_stats,
        }


# Global in-process suppression instance
_filter_instance: ScalableSuppressionFilter | None = None


def get_suppression_filter() -> ScalableSuppressionFilter:
    global _filter_instance
    if _filter_instance is None:
        from app.core.config import settings
        _filter_instance = ScalableSuppressionFilter(hmac_key=settings.bloom_hmac_key)
    return _filter_instance
