"""
Cryptographic Hash-Chained Audit Log Writer & Verifier (H4).

Provides an append-only, tamper-evident audit trail:
- Each row contains:
  - ``prev_hash``: SHA256 of the previous row's ``row_hash``
  - ``row_hash``: SHA256(prev_hash || canonical_json(row_contents))
- Modification or deletion of any historical row breaks the cryptographic chain.
- Never include phone numbers, names, or transcripts in the metadata — IDs and counts only.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Tuple

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog

log = structlog.get_logger()

GENESIS_HASH = "0" * 64


def compute_row_hash(
    prev_hash: str,
    action: str,
    object_type: str,
    object_id: str,
    meta: dict[str, Any],
    timestamp: str,
) -> str:
    """Compute deterministic SHA256 hash of audit entry."""
    canonical = {
        "prev_hash": prev_hash,
        "action": action,
        "object_type": object_type,
        "object_id": object_id,
        "meta": meta,
        "timestamp": timestamp,
    }
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def write_audit(
    action: str,
    object_type: str,
    object_id: str,
    db: AsyncSession,
    *,
    user_id: uuid.UUID | None = None,
    ip: str | None = None,
    meta: dict[str, Any] | None = None,
) -> AuditLog:
    """Insert a cryptographically hash-chained audit log entry."""
    meta_dict = meta or {}
    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()

    # Get latest row hash for chaining
    stmt = select(AuditLog.row_hash).order_by(AuditLog.id.desc()).limit(1)
    res = await db.execute(stmt)
    prev_hash = res.scalar_one_or_none() or GENESIS_HASH

    row_hash = compute_row_hash(
        prev_hash=prev_hash,
        action=action,
        object_type=object_type,
        object_id=object_id,
        meta=meta_dict,
        timestamp=now_iso,
    )

    entry = AuditLog(
        user_id=user_id,
        action=action,
        object_type=object_type,
        object_id=object_id,
        ip=ip,
        meta=meta_dict,
        prev_hash=prev_hash,
        row_hash=row_hash,
        created_at=now_dt,
    )
    db.add(entry)
    await db.flush()
    log.info(
        "audit_written",
        action=action,
        object_type=object_type,
        object_id=object_id,
        row_hash=row_hash[:12],
    )
    return entry


async def verify_audit_chain(db: AsyncSession) -> Tuple[bool, int | None, str | None]:
    """Walk the audit log in sequential order and verify cryptographic chain integrity.

    Returns:
    --------
    (is_valid, broken_row_id, head_hash_or_reason)
    """
    stmt = select(AuditLog).order_by(AuditLog.id.asc())
    res = await db.execute(stmt)
    rows = list(res.scalars().all())

    if not rows:
        return True, None, GENESIS_HASH

    expected_prev = GENESIS_HASH
    for row in rows:
        if row.prev_hash is None or row.prev_hash != expected_prev:
            return False, row.id, f"Invalid prev_hash at row {row.id}"

        recomputed = compute_row_hash(
            prev_hash=row.prev_hash,
            action=row.action,
            object_type=row.object_type,
            object_id=row.object_id,
            meta=row.meta or {},
            timestamp=row.created_at.isoformat(),
        )
        if row.row_hash != recomputed:
            return False, row.id, f"Tampered row_hash at row {row.id}"

        expected_prev = row.row_hash

    return True, None, rows[-1].row_hash

