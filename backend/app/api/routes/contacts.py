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
from app.security.suppression import get_suppression_filter, normalize_e164

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
    telegram_chat_id: Optional[str] = None


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


LANGUAGE_NAME_TO_CODE = {
    "english": "en",
    "en": "en",
    "hindi": "hi",
    "hi": "hi",
    "tamil": "ta",
    "ta": "ta",
    "telugu": "te",
    "te": "te",
    "kannada": "kn",
    "kn": "kn",
    "ka": "kn",
    "malayalam": "ml",
    "ml": "ml",
    "marathi": "mr",
    "mr": "mr",
    "bengali": "bn",
    "bn": "bn",
    "bangla": "bn",
    "gujarati": "gu",
    "gu": "gu",
    "punjabi": "pa",
    "pa": "pa",
    "odia": "or",
    "or": "or",
}


def _parse_language(raw: Optional[str]) -> str:
    """Normalize language name or code to standard 2-letter ISO code."""
    if not raw:
        return "en"
    cleaned = str(raw).strip().lower()
    if cleaned in LANGUAGE_NAME_TO_CODE:
        return LANGUAGE_NAME_TO_CODE[cleaned]
    for name, code in LANGUAGE_NAME_TO_CODE.items():
        if cleaned.startswith(name):
            return code
    if len(cleaned) >= 2:
        prefix = cleaned[:2]
        if prefix in LANGUAGE_NAME_TO_CODE:
            return LANGUAGE_NAME_TO_CODE[prefix]
    return "en"


def _extract_col(row: dict, *candidates: str) -> str:
    """Case-insensitive, whitespace-insensitive column extractor from a CSV row."""
    normalized_row = {
        str(k).strip().lower().replace("_", "").replace(" ", ""): v
        for k, v in row.items()
        if k is not None
    }
    for c in candidates:
        norm_c = c.lower().replace("_", "").replace(" ", "")
        if norm_c in normalized_row and normalized_row[norm_c] is not None:
            return str(normalized_row[norm_c]).strip()
    return ""


def _has_phone_column(fieldnames: list) -> bool:
    """Check if any header corresponds to a phone number column."""
    norm_fields = {
        str(f).strip().lower().replace("_", "").replace(" ", "")
        for f in fieldnames
        if f
    }
    phone_candidates = {"phone", "phonenumber", "mobile", "mobilenumber", "contact", "contactnumber", "number", "tel", "telephone"}
    return bool(norm_fields & phone_candidates)


def _parse_phone(raw: str) -> str:
    """Normalize phone: strip spaces/dashes, keep digits and leading +."""
    return raw.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "").replace(".", "").replace("\t", "")


def _decrypt_optional(enc: Optional[str], raw_name: Optional[str] = None) -> Optional[str]:
    """Return raw name if present, or decode hex/utf-8 if encrypted."""
    if raw_name:
        return raw_name
    if not enc:
        return None
    try:
        return bytes.fromhex(enc).decode("utf-8")
    except Exception:
        return enc


def _masked_phone(phone_last4: Optional[str]) -> Optional[str]:
    """Return masked phone like ••••7594."""
    if not phone_last4:
        return None
    return f"••••{phone_last4}"


def _get_suppression_filter():
    """Return the real keyed Bloom filter suppression instance."""
    return get_suppression_filter()


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/", response_model=ContactOut, status_code=status.HTTP_201_CREATED)
async def create_contact(body: ContactIn):
    """Add a single contact to the database with customer name."""
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
        name_val = body.name.strip() if body.name else None
        name_enc_val = name_val.encode("utf-8").hex() if name_val else None

        # Check if contact already exists by phone_hash to avoid FK violation
        existing = sb.table(_TABLE).select("id").eq("phone_hash", phone_hash).limit(1).execute()
        if existing.data:
            contact_id = existing.data[0]["id"]
            update_data = {}
            if name_val:
                update_data["name"] = name_val
                update_data["name_enc"] = name_enc_val
            if body.telegram_chat_id:
                update_data["telegram_chat_id"] = body.telegram_chat_id
            if update_data:
                try:
                    sb.table(_TABLE).update(update_data).eq("id", contact_id).execute()
                except Exception:
                    # Fallback if name column not yet created in Supabase
                    update_data.pop("name", None)
                    if update_data:
                        sb.table(_TABLE).update(update_data).eq("id", contact_id).execute()
        else:
            row = {
                "id": str(uuid.uuid4()),
                "name": name_val,
                "name_enc": name_enc_val,
                "phone_enc": phone.encode("utf-8").hex(),
                "phone_hash": phone_hash,
                "phone_last4": phone_last4,
                "language": body.language,
                "segment": body.segment,
                "telegram_chat_id": body.telegram_chat_id,
                "consent": True,
                "consent_source": "single_import",
                "consent_at": now,
                "dnd": False,
                "opted_out": False,
                "created_at": now,
            }
            try:
                resp = sb.table(_TABLE).insert(row).execute()
            except Exception as insert_err:
                # If column 'name' doesn't exist yet in Supabase table, retry without 'name'
                if "name" in str(insert_err) and "column" in str(insert_err).lower():
                    row_fallback = dict(row)
                    row_fallback.pop("name", None)
                    resp = sb.table(_TABLE).insert(row_fallback).execute()
                else:
                    raise
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
            name=name_val,
            phone=_masked_phone(phone_last4),
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
    """List contacts (customer name resolved, phone shown as last-4 digits)."""
    if not is_supabase_configured():
        return []
    try:
        sb = get_supabase()
        try:
            resp = (
                sb.table(_TABLE)
                .select("id,name,name_enc,phone_last4,language,segment,consent,opted_out,created_at")
                .order("created_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )
        except Exception:
            resp = (
                sb.table(_TABLE)
                .select("id,name_enc,phone_last4,language,segment,consent,opted_out,created_at")
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
                name=_decrypt_optional(r.get("name_enc"), r.get("name")),
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
        fieldnames = reader.fieldnames or []
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not parse CSV. Ensure valid UTF-8 encoding.",
        )

    if not _has_phone_column(fieldnames):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="CSV missing required phone number column (expected 'phone', 'mobile', or 'contact').",
        )

    sb = get_supabase()
    rows_to_insert = []
    errors: list[str] = []
    skipped = 0

    for i, row in enumerate(reader, start=2):  # row 1 = header
        phone_raw = _parse_phone(_extract_col(row, "phone", "phonenumber", "phone_number", "mobile", "mobilenumber", "mobile_number", "contact", "contactnumber", "contact_number", "number", "tel"))
        if not phone_raw or len(phone_raw) < 7:
            errors.append(f"Row {i}: invalid or missing phone ({phone_raw}) — skipped")
            skipped += 1
            continue

        phone_hash = hashlib.sha256(phone_raw.encode()).hexdigest()
        phone_last4 = phone_raw[-4:] if len(phone_raw) >= 4 else phone_raw.ljust(4, "0")
        lang = _parse_language(_extract_col(row, "language", "lang", "primary_language", "locale"))
        segment_val = _extract_col(row, "segment", "category", "tag", "type", "role", "group") or "General"
        now = datetime.now(timezone.utc).isoformat()

        name_val = _extract_col(row, "name", "full_name", "contact_name", "customer_name", "first_name", "attendee", "person") or None
        name_enc_val = name_val.encode("utf-8").hex() if name_val else None

        rows_to_insert.append({
            "id": str(uuid.uuid4()),
            "name": name_val,
            "name_enc": name_enc_val,
            "phone_enc": phone_raw.encode("utf-8").hex(),
            "phone_hash": phone_hash,
            "phone_last4": phone_last4,
            "language": lang,
            "segment": segment_val,
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
            # Check existing contacts by phone_hash to preserve existing primary keys and avoid FK errors
            phone_hashes = [r["phone_hash"] for r in rows_to_insert]
            existing_resp = (
                sb.table(_TABLE)
                .select("id,phone_hash")
                .in_("phone_hash", phone_hashes)
                .execute()
            )
            existing_map = {r["phone_hash"]: r["id"] for r in (existing_resp.data or [])}

            new_rows = [r for r in rows_to_insert if r["phone_hash"] not in existing_map]
            if new_rows:
                try:
                    insert_resp = sb.table(_TABLE).insert(new_rows).execute()
                except Exception as ins_err:
                    if "name" in str(ins_err) and "column" in str(ins_err).lower():
                        stripped_new = [dict(r) for r in new_rows]
                        for r in stripped_new:
                            r.pop("name", None)
                        insert_resp = sb.table(_TABLE).insert(stripped_new).execute()
                    else:
                        raise
                for r in (insert_resp.data or []):
                    existing_map[r["phone_hash"]] = r["id"]

            # Update names and language for existing contacts if provided
            for r in rows_to_insert:
                p_hash = r["phone_hash"]
                if p_hash in existing_map:
                    try:
                        update_data = {
                            "language": r["language"],
                            "segment": r.get("segment") or "General",
                        }
                        if r.get("name"):
                            update_data["name"] = r["name"]
                        if r.get("name_enc"):
                            update_data["name_enc"] = r["name_enc"]
                        try:
                            sb.table(_TABLE).update(update_data).eq("id", existing_map[p_hash]).execute()
                        except Exception:
                            update_data.pop("name", None)
                            sb.table(_TABLE).update(update_data).eq("id", existing_map[p_hash]).execute()
                    except Exception:
                        pass

            if campaign_id and existing_map:
                cc_rows = [
                    {
                        "id": str(uuid.uuid4()),
                        "campaign_id": campaign_id,
                        "contact_id": existing_map[r["phone_hash"]],
                        "status": "pending",
                        "attempt_count": 0,
                        "created_at": now,
                    }
                    for r in rows_to_insert
                    if r["phone_hash"] in existing_map
                ]
                if cc_rows:
                    sb.table(_CC_TABLE).upsert(cc_rows, on_conflict="campaign_id,contact_id").execute()

            queued = len(rows_to_insert)
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
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted.")

    content = await file.read()
    if len(content) > MAX_CSV_BYTES:
        raise HTTPException(status_code=413, detail=f"CSV exceeds {MAX_CSV_BYTES // 1024 // 1024} MB limit.")

    try:
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        fieldnames = reader.fieldnames or []
    except Exception:
        raise HTTPException(status_code=422, detail="Could not parse CSV. Ensure valid UTF-8 encoding.")

    if not _has_phone_column(fieldnames):
        raise HTTPException(status_code=422, detail="CSV missing required phone number column (expected 'phone', 'mobile', or 'contact').")

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
        phone_raw = _parse_phone(_extract_col(row, "phone", "phonenumber", "phone_number", "mobile", "mobilenumber", "mobile_number", "contact", "contactnumber", "contact_number", "number", "tel"))
        if not phone_raw or len(phone_raw) < 7:
            errors.append(f"Row {i}: invalid or missing phone ({phone_raw}) — skipped")
            skipped += 1
            continue

        phone_hash = hashlib.sha256(phone_raw.encode()).hexdigest()
        phone_last4 = phone_raw[-4:] if len(phone_raw) >= 4 else phone_raw.ljust(4, "0")
        lang = _parse_language(_extract_col(row, "language", "lang", "primary_language", "locale"))
        segment_val = _extract_col(row, "segment", "category", "tag", "type", "role", "group") or "General"
        name_val = _extract_col(row, "name", "full_name", "contact_name", "customer_name", "first_name", "attendee", "person") or None
        name_enc_val = name_val.encode("utf-8").hex() if name_val else None

        contact_rows.append({
            "id": str(uuid.uuid4()),
            "name": name_val,
            "name_enc": name_enc_val,
            "phone_enc": phone_raw.encode("utf-8").hex(),
            "phone_hash": phone_hash,
            "phone_last4": phone_last4,
            "language": lang,
            "segment": segment_val,
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
            try:
                insert_resp = sb.table(_TABLE).insert(new_rows).execute()
            except Exception as ins_err:
                if "name" in str(ins_err) and "column" in str(ins_err).lower():
                    stripped_new = [dict(r) for r in new_rows]
                    for r in stripped_new:
                        r.pop("name", None)
                    insert_resp = sb.table(_TABLE).insert(stripped_new).execute()
                else:
                    raise
            for r in (insert_resp.data or []):
                existing_map[r["phone_hash"]] = r["id"]

        # Update existing contact details
        for r in contact_rows:
            p_hash = r["phone_hash"]
            if p_hash in existing_map:
                try:
                    update_data = {
                        "language": r["language"],
                        "segment": r.get("segment") or "General",
                    }
                    if r.get("name"):
                        update_data["name"] = r["name"]
                    if r.get("name_enc"):
                        update_data["name_enc"] = r["name_enc"]
                    try:
                        sb.table(_TABLE).update(update_data).eq("id", existing_map[p_hash]).execute()
                    except Exception:
                        update_data.pop("name", None)
                        sb.table(_TABLE).update(update_data).eq("id", existing_map[p_hash]).execute()
                except Exception:
                    pass

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


@router.delete("/{contact_id}", status_code=status.HTTP_200_OK)
async def delete_contact(contact_id: str):
    """
    H2 + H3: Erase a contact.
    If opted-out or on DND, their phone is added to the suppression filter first
    so they can never be called again — even after the record is deleted.
    """
    if not is_supabase_configured():
        raise HTTPException(status_code=503, detail="Database not configured")
    try:
        sb = get_supabase()
        row = sb.table(_TABLE).select("phone_enc,opted_out,dnd").eq("id", contact_id).single().execute().data
        if not row:
            raise HTTPException(status_code=404, detail="Contact not found")

        # Suppress before deleting if opted-out or DND
        suppressed = False
        phone_enc = row.get("phone_enc", "")
        if phone_enc and (row.get("opted_out") or row.get("dnd")):
            try:
                phone = bytes.fromhex(phone_enc).decode("utf-8")
                get_suppression_filter().suppress(phone)
                suppressed = True
            except Exception:
                pass

        sb.table(_TABLE).delete().eq("id", contact_id).execute()

        return {
            "deleted": True,
            "contact_id": contact_id,
            "suppressed": suppressed,
            "message": ("Contact deleted and phone added to suppression filter — "
                        "this number will never be called again, even after re-import."
                        if suppressed else "Contact deleted."),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database error: {exc}")
