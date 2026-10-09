"""Contacts routes — CSV import stub."""

from fastapi import APIRouter, UploadFile, File, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()


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
    Columns expected: name, phone, language (optional).
    (Stub — CSV parsing and Supabase write pending.)
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .csv files are accepted.",
        )
    return {"message": "CSV received — import processing not yet implemented."}
