"""Contacts routes — list and CSV import backed by Supabase."""

from __future__ import annotations

import csv
import hashlib
import io
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel

from app.db.supabase_client import get_supabase, is_supabase_configured

router = APIRouter()

_TABLE = "contacts"
_CC_TABLE = "campaign_contacts"

MAX_CSV_BYTES = 10 * 1024 * 1024  # 10 MB
REQUIRED_COLUMNS = {"phone"}


# ── Schemas ───────────────────────────────────────────────────────────────────

class ContactIn(BaseModel):
    campaign_id: Optional[str] = None
    name: Optional[str] = None
    phone: str
    language: str = "en"
    segment: Optional[str] = "General"
    notes: Optional[str] = None


class ContactOut(BaseModel):
    id: str
    name: Optional[str] = None
    phone: Optional[str] = None
    phone_last4: str
    language: str
    segment: Optional[str] = None
    status: str = "pending"
    campaign: Optional[str] = None
    consent: bool
    opted_out: bool
    created_at: str


class ImportResult(BaseModel):
    queued: int
    skipped: int
    errors: List[str]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_phone(raw: str) -> str:
    """Normalize phone: strip spaces/dashes, keep digits and leading +."""
    return raw.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")


def _decrypt_optional(enc: Optional[str]) -> Optional[str]:
    """Return None — name is stored encrypted, not returned raw."""
    return None


def _masked_phone(phone_last4: Optional[str]) -> Optional[str]:
    """Return masked phone like ••••7594."""
    if not phone_last4:
        return None
    return f"••••{phone_last4}"


def _get_suppression_filter():
    """Stub — returns an object that never suppresses (no suppression list configured)."""
    class _NoOp:
        def is_suppressed(self, _phone: str) -> bool:
            return False
    return _NoOp()


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/", response_model=ContactOut, status_code=status.HTTP_201_CREATED)
async def create_contact(body: ContactIn):
    """Add a single contact to the database."""
    phone = _parse_phone(body.phone)
    if len(phone) < 7:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Phone number too short — expected at least 7 digits.",
        )
    phone_hash = hashlib.sha256(phone.encode()).hexdigest()
    phone_last4 = phone[-4:] if len(phone) >= 4 else phone.ljust(4, "0")
    if _get_suppression_filter().is_suppressed(phone):
        raise HTTPException(status_code=409, detail="Contact is suppressed")
    try:
        sb = get_supabase()
        now = datetime.now(timezone.utc).isoformat()

        # Check if contact already exists by phone_hash to avoid FK violation
        existing = sb.table(_TABLE).select("id").eq("phone_hash", phone_hash).limit(1).execute()
        if existing.data:
            contact_id = existing.data[0]["id"]
        else:
            row = {
                "id": str(uuid.uuid4()),
                "phone_enc": phone.encode("utf-8").hex(),
                "phone_hash": phone_hash,
                "phone_last4": phone_last4,
                "language": body.language,
                "segment": body.segment,
                "consent": True,
                "consent_source": "single_import",
                "consent_at": now,
                "dnd": False,
                "opted_out": False,
                "created_at": now,
            }
            resp = sb.table(_TABLE).insert(row).execute()
            contact_id = (resp.data or [{}])[0].get("id", row["id"])

        # If campaign_id given, also insert into campaign_contacts
        if body.campaign_id:
            try:
                sb.table(_CC_TABLE).upsert({
                    "id": str(uuid.uuid4()),
                    "campaign_id": body.campaign_id,
                    "contact_id": contact_id,
                    "status": "pending",
                    "attempt_count": 0,
                    "created_at": now,
                }, on_conflict="campaign_id,contact_id").execute()
            except Exception:
                pass  # non-fatal

        return ContactOut(
            id=str(contact_id),
            name=None,
            phone_last4=phone_last4,
            language=body.language,
            segment=body.segment,
            status="pending",
            consent=True,
            opted_out=False,
            created_at=now,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database error: {exc}",
        )


@router.get("/", response_model=List[ContactOut])
async def list_contacts(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List contacts (phone shown as last-4 digits only — PII protected)."""
    if not is_supabase_configured():
        return []
    try:
        sb = get_supabase()
        resp = (
            sb.table(_TABLE)
            .select("id,phone_last4,name_enc,language,segment,consent,opted_out,created_at")
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        contacts = resp.data or []
        contact_ids = [str(r["id"]) for r in contacts]
        campaign_by_contact: dict[str, tuple[str, str]] = {}
        if contact_ids:
            links = (
                sb.table("campaign_contacts")
                .select("contact_id,campaign_id,status")
                .in_("contact_id", contact_ids)
                .execute()
                .data
                or []
            )
            campaign_ids = list({str(link["campaign_id"]) for link in links if link.get("campaign_id")})
            campaigns_by_id = {}
            if campaign_ids:
                campaigns_by_id = {
                    str(c["id"]): c.get("name")
                    for c in sb.table("campaigns").select("id,name").in_("id", campaign_ids).execute().data or []
                }
            campaign_by_contact = {
                str(link["contact_id"]): (
                    str(link.get("status") or "pending"),
                    campaigns_by_id.get(str(link.get("campaign_id"))) or "",
                )
                for link in links
                if link.get("contact_id")
            }
        return [
            ContactOut(
                id=str(r["id"]),
                name=_decrypt_optional(r.get("name_enc")),
                phone=_masked_phone(r.get("phone_last4")),
                phone_last4=r.get("phone_last4", "????"),
                language=r.get("language", "en"),
                segment=r.get("segment"),
                status=campaign_by_contact.get(str(r["id"]), ("pending", ""))[0],
                campaign=campaign_by_contact.get(str(r["id"]), ("pending", ""))[1] or None,
                consent=bool(r.get("consent", False)),
                opted_out=bool(r.get("opted_out", False)),
                created_at=str(r.get("created_at", "")),
            )
            for r in contacts
        ]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database error: {exc}",
        )


@router.post("/import", response_model=ImportResult, status_code=status.HTTP_202_ACCEPTED)
async def import_contacts_csv(
    file: UploadFile = File(...),
    campaign_id: Optional[str] = Query(None),
):
    """
    Import contacts from a CSV file (no campaign link).
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
        phone_raw = _parse_phone(row.get("phone") or "")
        if not phone_raw:
            errors.append(f"Row {i}: empty phone — skipped")
            skipped += 1
            continue

        phone_hash = hashlib.sha256(phone_raw.encode()).hexdigest()
        phone_last4 = phone_raw[-4:] if len(phone_raw) >= 4 else phone_raw.ljust(4, "0")
        lang = (row.get("language") or "en").strip()[:2].lower() or "en"
        now = datetime.now(timezone.utc).isoformat()

        rows_to_insert.append({
            "id": str(uuid.uuid4()),
            "phone_enc": phone_raw.encode("utf-8").hex(),
            "phone_hash": phone_hash,
            "phone_last4": phone_last4,
            "name_enc": encrypt((row.get("name") or "").strip()).hex() if (row.get("name") or "").strip() else None,
            "language": lang,
            "consent": True,
            "consent_source": f"csv_import:{file.filename}",
            "consent_at": now,
            "dnd": False,
            "opted_out": False,
            "created_at": now,
        })

    queued = 0
    if rows_to_insert:
        try:
            resp = (
                sb.table(_TABLE)
                .upsert(rows_to_insert, on_conflict="phone_hash")
                .execute()
            )
            inserted = resp.data or []
            queued = len(inserted)
            if campaign_id and inserted:
                sb.table("campaign_contacts").upsert(
                    [
                        {
                            "id": str(uuid.uuid4()),
                            "campaign_id": campaign_id,
                            "contact_id": row["id"],
                            "language": row["language"],
                            "segment": row.get("segment"),
                            "status": "pending",
                        }
                        for row in rows_to_insert
                    ],
                    on_conflict="campaign_id,contact_id",
                ).execute()
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Database write failed: {exc}",
            )

    return ImportResult(queued=queued, skipped=skipped, errors=errors[:20])


@router.post("/import-to-campaign", response_model=ImportResult, status_code=status.HTTP_202_ACCEPTED)
async def import_contacts_to_campaign(
    campaign_id: str,
    file: UploadFile = File(...),
):
    """
    ★ MAIN CALLING FLOW ENDPOINT ★

    Upload a CSV of phone numbers for a specific campaign.
    Creates contacts + campaign_contacts (status='pending').

    After this, call POST /api/v1/campaigns/{id}/launch to place calls.

    Required CSV column: phone
    Optional: name, language (default 'en')
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted.")

    content = await file.read()
    if len(content) > MAX_CSV_BYTES:
        raise HTTPException(status_code=413, detail=f"CSV exceeds {MAX_CSV_BYTES // 1024 // 1024} MB limit.")

    try:
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        headers = set(h.strip().lower() for h in (reader.fieldnames or []))
    except Exception:
        raise HTTPException(status_code=422, detail="Could not parse CSV. Ensure valid UTF-8 encoding.")

    if "phone" not in headers:
        raise HTTPException(status_code=422, detail="CSV missing required column: phone.")

    sb = get_supabase()

    # Verify campaign exists
    try:
        camp_resp = sb.table("campaigns").select("id").eq("id", campaign_id).single().execute()
        if not camp_resp.data:
            raise HTTPException(status_code=404, detail=f"Campaign '{campaign_id}' not found.")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database error: {exc}")

    contact_rows: list[dict] = []
    errors: list[str] = []
    skipped = 0
    now = datetime.now(timezone.utc).isoformat()

    for i, row in enumerate(reader, start=2):
        phone_raw = _parse_phone(row.get("phone") or "")
        if not phone_raw:
            errors.append(f"Row {i}: empty phone — skipped")
            skipped += 1
            continue

        phone_hash = hashlib.sha256(phone_raw.encode()).hexdigest()
        phone_last4 = phone_raw[-4:] if len(phone_raw) >= 4 else phone_raw.ljust(4, "0")
        lang = (row.get("language") or "en").strip()[:2].lower() or "en"

        contact_rows.append({
            "id": str(uuid.uuid4()),
            "phone_enc": phone_raw.encode("utf-8").hex(),
            "phone_hash": phone_hash,
            "phone_last4": phone_last4,
            "language": lang,
            "consent": True,
            "consent_source": f"csv_campaign_import:{file.filename}",
            "consent_at": now,
            "dnd": False,
            "opted_out": False,
            "created_at": now,
        })

    if not contact_rows:
        return ImportResult(queued=0, skipped=skipped, errors=errors[:20])

    queued = 0
    try:
        # 1. For each row: check existing by phone_hash to avoid FK violations,
        #    insert only truly new contacts, collect all final contact IDs.
        phone_hashes = [r["phone_hash"] for r in contact_rows]
        existing_resp = (
            sb.table(_TABLE)
            .select("id,phone_hash")
            .in_("phone_hash", phone_hashes)
            .execute()
        )
        existing_map = {r["phone_hash"]: r["id"] for r in (existing_resp.data or [])}

        new_rows = [r for r in contact_rows if r["phone_hash"] not in existing_map]
        if new_rows:
            insert_resp = sb.table(_TABLE).insert(new_rows).execute()
            for r in (insert_resp.data or []):
                existing_map[r["phone_hash"]] = r["id"]

        # 2. Link all contacts (new + existing) to this campaign via campaign_contacts
        cc_rows = [
            {
                "id": str(uuid.uuid4()),
                "campaign_id": campaign_id,
                "contact_id": contact_id,
                "status": "pending",
                "attempt_count": 0,
                "created_at": now,
            }
            for contact_id in existing_map.values()
        ]
        if cc_rows:
            sb.table(_CC_TABLE).upsert(
                cc_rows, on_conflict="campaign_id,contact_id"
            ).execute()
        queued = len(cc_rows)

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database write failed: {exc}",
        )

    return ImportResult(queued=queued, skipped=skipped, errors=errors[:20])
