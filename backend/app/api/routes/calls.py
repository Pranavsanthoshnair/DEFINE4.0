"""Calls routes — call initiation stub."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class InitiateCallRequest(BaseModel):
    campaign_id: str
    recipient_id: str


class CallAttemptOut(BaseModel):
    id: str
    status: str
    message: str


@router.post("/initiate", response_model=CallAttemptOut, status_code=status.HTTP_202_ACCEPTED)
async def initiate_call(payload: InitiateCallRequest):
    """
    Initiate an outbound call for a campaign recipient via Exotel.
    (Stub — Exotel integration NOT YET IMPLEMENTED.)
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Exotel call initiation is not yet implemented.",
    )
