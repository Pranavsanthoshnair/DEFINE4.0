"""
Cryptography helpers for Veylo.

All phone-number operations that produce logs must use phone_last4 / contact_id.
Never log the plaintext phone number, name, or transcript.

Key sources
-----------
settings.data_enc_key   : base64-encoded 32-byte AES-256-GCM key
settings.phone_hmac_key : base64-encoded 32-byte HMAC-SHA256 key

If either key is empty (dev mode) a deterministic fallback is used and a
WARNING is emitted once via structlog.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import warnings

import structlog
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings

log = structlog.get_logger()

# ---------------------------------------------------------------------------
# Supported language codes for validation elsewhere in the codebase
# ---------------------------------------------------------------------------
SUPPORTED_LANGUAGES: frozenset[str] = frozenset(
    ["en", "hi", "ml", "ta", "te", "kn", "bn", "mr", "gu"]
)

# ---------------------------------------------------------------------------
# Dev-mode fallback keys (deterministic, NOT secure)
# ---------------------------------------------------------------------------
_DEV_ENC_KEY = b"\x00" * 32
_DEV_HMAC_KEY = b"\x01" * 32
_warned_enc = False
_warned_hmac = False


def _get_enc_key() -> bytes:
    global _warned_enc
    raw = settings.data_enc_key
    if not raw:
        if not _warned_enc:
            log.warning(
                "data_enc_key_missing",
                msg="DATA_ENC_KEY not set – using insecure dev key. Set before production.",
            )
            _warned_enc = True
        return _DEV_ENC_KEY
    return base64.b64decode(raw)


def _get_hmac_key() -> bytes:
    global _warned_hmac
    raw = settings.phone_hmac_key
    if not raw:
        if not _warned_hmac:
            log.warning(
                "phone_hmac_key_missing",
                msg="PHONE_HMAC_KEY not set – using insecure dev key. Set before production.",
            )
            _warned_hmac = True
        return _DEV_HMAC_KEY
    return base64.b64decode(raw)


# ---------------------------------------------------------------------------
# AES-256-GCM helpers (strings)
# ---------------------------------------------------------------------------

def encrypt(plaintext: str) -> bytes:
    """Encrypt a UTF-8 string.

    Returns: nonce (12 bytes) || ciphertext+tag (variable length).
    """
    key = _get_enc_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return nonce + ct


def decrypt(blob: bytes) -> str:
    """Decrypt a blob produced by :func:`encrypt`.

    Raises ``ValueError`` on tampered / invalid data.
    """
    key = _get_enc_key()
    aesgcm = AESGCM(key)
    nonce = blob[:12]
    ct = blob[12:]
    return aesgcm.decrypt(nonce, ct, None).decode()


# ---------------------------------------------------------------------------
# AES-256-GCM helpers (bytes — for recordings)
# ---------------------------------------------------------------------------

def encrypt_bytes(data: bytes) -> bytes:
    """Encrypt raw bytes (e.g. a WAV recording).

    Returns: nonce (12 bytes) || ciphertext+tag.
    """
    key = _get_enc_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, data, None)
    return nonce + ct


def decrypt_bytes(blob: bytes) -> bytes:
    """Decrypt a blob produced by :func:`encrypt_bytes`."""
    key = _get_enc_key()
    aesgcm = AESGCM(key)
    nonce = blob[:12]
    ct = blob[12:]
    return aesgcm.decrypt(nonce, ct, None)


# ---------------------------------------------------------------------------
# HMAC-SHA256 phone hash (used for dedupe and DND lookup)
# ---------------------------------------------------------------------------

def phone_hash(e164: str) -> str:
    """Return HMAC-SHA256 hex digest of the E.164 phone number.

    This is deterministic for the same key and the same number.
    Never include this value in logs — use phone_last4 instead.
    """
    key = _get_hmac_key()
    return hmac.new(key, e164.encode(), hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# Phone normalisation
# ---------------------------------------------------------------------------

# Digits-only pattern after stripping formatting
_DIGITS_RE = re.compile(r"\D")


def normalise_phone(raw: str) -> str | None:
    """Normalise ``raw`` to E.164 format.

    Rules:
    - Strip all non-digit characters except a leading '+'.
    - A '+' prefix means the number is already international.
    - 10-digit numbers (without country code) are assumed to be Indian (+91).
    - 11-digit numbers starting with 0 are treated as Indian STD (strip the 0, add +91).
    - Any other format returns None.

    Returns:
        E.164 string (e.g. ``+919876543210``) or ``None`` if invalid.
    """
    if not raw:
        return None

    raw = raw.strip()

    if raw.startswith("+"):
        digits = _DIGITS_RE.sub("", raw[1:])
        candidate = "+" + digits
    else:
        digits = _DIGITS_RE.sub("", raw)
        if len(digits) == 10:
            candidate = "+91" + digits
        elif len(digits) == 11 and digits.startswith("0"):
            candidate = "+91" + digits[1:]
        elif len(digits) > 10:
            candidate = "+" + digits
        else:
            return None

    # Basic sanity: must start with +, then 7–15 digits
    if not re.fullmatch(r"\+\d{7,15}", candidate):
        return None

    return candidate


# ---------------------------------------------------------------------------
# Phone masking (for logs and API responses)
# ---------------------------------------------------------------------------

def mask_phone(e164: str) -> str:
    """Return a masked form of the E.164 number showing only the last 4 digits.

    Example: ``+919876543210`` → ``+91XXXXXX3210``
    """
    if len(e164) <= 5:
        return "XXXX"
    prefix = e164[:-4]
    # Replace all digits in prefix with X, keep the leading +CC
    masked_prefix = re.sub(r"\d", "X", prefix)
    return masked_prefix + e164[-4:]


# ---------------------------------------------------------------------------
# Phone reveal (ONLY to be imported inside telephony.place_call — never log)
# ---------------------------------------------------------------------------

def reveal_phone(contact: object) -> str:  # contact: Contact ORM row
    """Decrypt and return the E.164 phone number for a contact.

    This function writes NO logs by design — the caller is responsible for
    ensuring the result is not logged, stored, or returned in any API response.

    Only ``backend.app.telephony`` should import this function.
    """
    return decrypt(contact.phone_enc)  # type: ignore[attr-defined]
