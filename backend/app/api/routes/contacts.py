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
from app.security.crypto import decrypt, encrypt, phone_hash, normalise_phone
from app.security.suppression import get_suppression_filter

router = APIRouter()

_TABLE = "contacts"

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


def _decrypt_optional(value: object) -> Optional[str]:
    """Decode encrypted text returned by Supabase bytea columns."""
    if not value:
        return None
    try:
        if isinstance(value, str):
            raw = value[2:] if value.startswith("\\x") else value
            value = bytes.fromhex(raw)
        return decrypt(bytes(value))
    except (TypeError, ValueError):
        return None


def _masked_phone(phone_last4: object) -> str:
    last4 = str(phone_last4 or "????")
    return f"••••{last4}"


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("/", response_model=ContactOut, status_code=status.HTTP_201_CREATED)
async def create_contact(body: ContactIn):
    """Add a single contact to the database."""
    phone = normalise_phone(body.phone)
    if not phone:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Phone number too short — expected at least 7 digits.",
        )
    phone_last4 = phone[-4:] if len(phone) >= 4 else phone.ljust(4, "0")
    if get_suppression_filter().is_suppressed(phone):
        raise HTTPException(status_code=409, detail="Contact is suppressed")
    try:
        sb = get_supabase()
        now = datetime.now(timezone.utc).isoformat()
        row = {
            "id": str(uuid.uuid4()),
            "phone_enc": encrypt(phone).hex(),
            "phone_hash": phone_hash(phone),
            "phone_last4": phone_last4,
            "name_enc": encrypt(body.name).hex() if body.name else None,
            "language": body.language,
            "segment": body.segment,
            "consent": True,
            "consent_source": "single_import",
            "consent_at": now,
            "dnd": False,
            "opted_out": False,
            "created_at": now,
        }
        # Upsert on phone_hash to prevent duplicates
        resp = sb.table(_TABLE).upsert(row, on_conflict="phone_hash").execute()
        r = (resp.data or [{}])[0]
        contact_id = str(r.get("id", row["id"]))
        if body.campaign_id:
            sb.table("campaign_contacts").upsert(
                {
                    "id": str(uuid.uuid4()),
                    "campaign_id": body.campaign_id,
                    "contact_id": contact_id,
                    "status": "pending",
                },
                on_conflict="campaign_id,contact_id",
            ).execute()
        return ContactOut(
            id=contact_id,
            name=body.name,
            phone=_masked_phone(phone_last4),
            phone_last4=phone_last4,
            language=body.language,
            segment=body.segment,
            status="pending",
            consent=True,
            opted_out=False,
            created_at=now,
        )
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
        # CSV headers are user-supplied; make Name/PHONE/Language work the
        # same as lowercase headers used by the API contract.
        row = {(key or "").strip().lower(): value for key, value in row.items()}
        phone_raw = (row.get("phone") or "").strip()
        if not phone_raw:
            errors.append(f"Row {i}: empty phone — skipped")
            skipped += 1
            continue

        phone = normalise_phone(phone_raw)
        if not phone or get_suppression_filter().is_suppressed(phone):
            errors.append(f"Row {i}: invalid or suppressed phone - skipped")
            skipped += 1
            continue
        phone_digest = phone_hash(phone)
        phone_last4 = phone[-4:]

        lang = (row.get("language") or "en").strip()[:2].lower() or "en"
        now = datetime.now(timezone.utc).isoformat()

        rows_to_insert.append({
            "id": str(uuid.uuid4()),
            "phone_enc": encrypt(phone).hex(),
            "phone_hash": phone_digest,
            "phone_last4": phone_last4,
            "name_enc": encrypt((row.get("name") or "").strip()).hex() if (row.get("name") or "").strip() else None,
            "language": lang,
            "segment": (row.get("segment") or "General").strip() or "General",
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
