"""
FastAPI auth dependency — requires X-Internal-Token header.
Returns 401 with contract-exact error body if missing or wrong.
Uses constant-time comparison to prevent timing attacks.
"""

from __future__ import annotations

import hmac
from typing import Optional

from fastapi import Header, HTTPException, status

from app.config import settings

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"error": {"code": "unauthorized", "message": "Invalid or missing X-Internal-Token"}},
)


async def require_token(
    x_internal_token: Optional[str] = Header(default=None, alias="X-Internal-Token"),
) -> None:
    """Raise 401 when token is absent or incorrect."""
    if x_internal_token is None:
        raise _UNAUTHORIZED

    expected = settings.ai_internal_token.encode()
    received = x_internal_token.encode()

    if not hmac.compare_digest(expected, received):
        raise _UNAUTHORIZED
