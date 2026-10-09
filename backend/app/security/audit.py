"""
Audit log writer.

Provides a single async helper ``write_audit`` that inserts a row into
``audit_log``. Never include phone numbers, names, or transcripts in the
``meta`` argument — use IDs and counts only.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog

log = structlog.get_logger()


async def write_audit(
    action: str,
    object_type: str,
    object_id: str,
    db: AsyncSession,
    *,
    user_id: uuid.UUID | None = None,
    ip: str | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    """Insert an audit log entry.

    Parameters
    ----------
    action      : Dot-separated action code, e.g. ``contacts.import``.
    object_type : The resource type, e.g. ``campaign``.
    object_id   : UUID or identifier of the object being acted on.
    db          : Current async SQLAlchemy session.
    user_id     : Optional authenticated user performing the action.
    ip          : Optional client IP address.
    meta        : Optional JSON-serialisable metadata dict (IDs and counts only).
    """
    entry = AuditLog(
        user_id=user_id,
        action=action,
        object_type=object_type,
        object_id=str(object_id),
        ip=ip,
        meta=meta or {},
        created_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    # Flush so the row is visible within the same transaction if needed.
    await db.flush()
    log.info("audit_written", action=action, object_type=object_type, object_id=str(object_id))
