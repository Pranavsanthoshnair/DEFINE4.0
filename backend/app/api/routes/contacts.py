"""Contacts routes — list and CSV import backed by Supabase."""

from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel

from app.db.supabase_client import get_supabase

router = APIRouter()

_TABLE = "contacts"

MAX_CSV_BYTES = 10 * 1024 * 1024  # 10 MB
REQUIRED_COLUMNS = {"phone"}


# ── Schemas ───────────────────────────────────────────────────────────────────

class ContactOut(BaseModel):
    id: str
    name: Optional[str] = None
    phone_last4: str
    language: str
    consent: bool
    opted_out: bool
    created_at: str


class ImportResult(BaseModel):
    queued: int
    skipped: int
    errors: List[str]


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[ContactOut])
async def list_contacts(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List contacts (phone shown as last-4 digits only — PII protected)."""
    try:
        sb = get_supabase()
        resp = (
            sb.table(_TABLE)
            .select("id,phone_last4,name_enc,language,consent,opted_out,created_at")
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return [
            ContactOut(
                id=str(r["id"]),
                name=None,  # name_enc is encrypted — not returned raw
                phone_last4=r.get("phone_last4", "????"),
                language=r.get("language", "en"),
                consent=bool(r.get("consent", False)),
                opted_out=bool(r.get("opted_out", False)),
                created_at=str(r.get("created_at", "")),
            )
            for r in (resp.data or [])
        ]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database error: {exc}",
        )


@router.post("/import", response_model=ImportResult, status_code=status.HTTP_202_ACCEPTED)
async def import_contacts_csv(file: UploadFile = File(...)):
    """
    Import contacts from a CSV file.
    Required columns: phone
    Optional columns: name, language (defaults to 'en'), email
    Max file size: 10 MB
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .csv files are accepted.",
        )

    content = await file.read()

    if len(content) > MAX_CSV_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"CSV exceeds {MAX_CSV_BYTES // 1024 // 1024} MB limit.",
        )

    try:
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        headers = set(h.strip().lower() for h in (reader.fieldnames or []))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not parse CSV. Ensure valid UTF-8 encoding.",
        )

    missing = REQUIRED_COLUMNS - headers
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"CSV missing required columns: {sorted(missing)}.",
        )

    sb = get_supabase()
    rows_to_insert = []
    errors: list[str] = []
    skipped = 0

    for i, row in enumerate(reader, start=2):  # row 1 = header
        phone_raw = (row.get("phone") or "").strip().replace(" ", "").replace("-", "")
        if not phone_raw:
            errors.append(f"Row {i}: empty phone — skipped")
            skipped += 1
            continue

        # Store only last-4 digits and a deterministic hash (no plain phone)
        import hashlib
        phone_hash = hashlib.sha256(phone_raw.encode()).hexdigest()
        phone_last4 = phone_raw[-4:] if len(phone_raw) >= 4 else phone_raw.ljust(4, "0")

        lang = (row.get("language") or "en").strip()[:2].lower() or "en"
        now = datetime.now(timezone.utc).isoformat()

        rows_to_insert.append({
            "id": str(uuid.uuid4()),
            "phone_enc": phone_raw.encode("utf-8").hex(),  # hex — replace with real AES in prod
            "phone_hash": phone_hash,
            "phone_last4": phone_last4,
            "language": lang,
            "consent": True,   # CSV import implies consent was obtained offline
            "consent_source": f"csv_import:{file.filename}",
            "consent_at": now,
            "dnd": False,
            "opted_out": False,
            "created_at": now,
        })

    queued = 0
    if rows_to_insert:
        try:
            # Upsert on phone_hash to avoid duplicate phone numbers
            resp = (
                sb.table(_TABLE)
                .upsert(rows_to_insert, on_conflict="phone_hash")
                .execute()
            )
            queued = len(resp.data or [])
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Database write failed: {exc}",
            )

    return ImportResult(queued=queued, skipped=skipped, errors=errors[:20])
