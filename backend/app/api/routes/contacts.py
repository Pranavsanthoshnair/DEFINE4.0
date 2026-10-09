"""Contacts routes — CSV import."""

import io
import csv
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

MAX_CSV_BYTES = 10 * 1024 * 1024  # 10 MB
REQUIRED_COLUMNS = {"phone"}
ALLOWED_COLUMNS = {"name", "phone", "language", "email"}


class ContactOut(BaseModel):
    id: str
    name: Optional[str]
    phone: str
    language: Optional[str]


@router.get("/", response_model=List[ContactOut])
async def list_contacts():
    """List contacts. (Stub — Supabase integration pending.)"""
    return []


@router.post("/import", status_code=status.HTTP_202_ACCEPTED)
async def import_contacts_csv(file: UploadFile = File(...)):
    """
    Accept a CSV file and queue contacts for validation and import.
    Required columns: phone
    Optional columns: name, language, email
    Max file size: 10 MB
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .csv files are accepted.",
        )

    content = await file.read()

    # Size guard
    if len(content) > MAX_CSV_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"CSV file exceeds maximum size of {MAX_CSV_BYTES // 1024 // 1024} MB.",
        )

    # Column validation
    try:
        text = content.decode("utf-8-sig")  # handle BOM
        reader = csv.DictReader(io.StringIO(text))
        headers = set(h.strip().lower() for h in (reader.fieldnames or []))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not parse CSV file. Ensure it is valid UTF-8.",
        )

    missing = REQUIRED_COLUMNS - headers
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"CSV is missing required columns: {sorted(missing)}. "
                   f"Expected at minimum: {sorted(REQUIRED_COLUMNS)}.",
        )

    # Count rows for response (full persistence pending)
    rows = list(reader)
    return {
        "message": f"CSV received — {len(rows)} rows queued for import.",
        "row_count": len(rows),
        "note": "Supabase persistence not yet implemented.",
    }

