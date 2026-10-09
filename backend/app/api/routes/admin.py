"""
Admin and Compliance API endpoints (H4, H2, H16).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.security.audit import verify_audit_chain
from app.security.suppression import get_suppression_filter

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/audit/verify")
async def verify_audit_log(db: AsyncSession = Depends(get_db)):
    """Walk and cryptographically verify SHA256 audit hash chain integrity (H4)."""
    is_valid, broken_id, head_or_reason = await verify_audit_chain(db)
    if not is_valid:
        return {
            "valid": False,
            "broken_row_id": broken_id,
            "error": head_or_reason,
            "head_hash": None,
        }
    return {
        "valid": True,
        "broken_row_id": None,
        "head_hash": head_or_reason,
    }


@router.get("/suppression/stats")
async def get_suppression_stats():
    """Retrieve Keyed Scalable Bloom Filter metrics and false positive estimation (H2)."""
    suppression = get_suppression_filter()
    return suppression.stats()
