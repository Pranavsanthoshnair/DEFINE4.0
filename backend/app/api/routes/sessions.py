"""
Browser voice session endpoints — the guaranteed demo path.

Execution type: BROWSER_VOICE
These sessions are completely separate from real telephony.
Synthetic events NEVER count in telephony campaign analytics.

Endpoints:
  POST /api/v1/sessions/browser/start       Start a browser voice session
  POST /api/v1/sessions/browser/{id}/tts    Get TTS audio for session prompt
  POST /api/v1/sessions/browser/{id}/respond Process audio/text response
  GET  /api/v1/sessions/browser/{id}        Get session state
  POST /api/v1/sessions/browser/{id}/end    End / abandon session
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

import structlog
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel

from app.ai_client.client import get_ai_client
from app.core.config import settings
from app.db.supabase_client import get_supabase
from app.providers import elevenlabs

log = structlog.get_logger()
router = APIRouter()

_TABLE = "execution_sessions"
_MAX_AUDIO_BYTES = 5 * 1024 * 1024   # 5 MB
_MAX_DURATION_S = 30                  # reject implausibly long recordings

EXECUTION_TYPE = "BROWSER_VOICE"

# Intent taxonomy used by browser sessions
BROWSER_INTENTS = ["confirm", "decline", "reschedule", "call_later", "stop_calling", "unclear"]


# ── Voices endpoint ───────────────────────────────────────────────────────────

@router.get("/voices")
async def list_voices():
    """
    Return available TTS voices — proxied safely from ElevenLabs.
    API key never leaves the backend.
    """
    if not elevenlabs.is_available():
        return {"provider": "none", "voices": [], "reason": "ELEVENLABS_API_KEY not configured"}
    try:
        voices = await elevenlabs.list_voices()
        simplified = [
            {"id": v["voice_id"], "name": v["name"], "description": v.get("description", "")}
            for v in voices
        ]
        return {"provider": "elevenlabs", "voices": simplified}
    except Exception as exc:
        return {"provider": "elevenlabs", "voices": [], "reason": str(exc)}


# ── Schemas ───────────────────────────────────────────────────────────────────

class StartSessionRequest(BaseModel):
    campaign_id: str
    language: str = "en"
    demo_participant_name: Optional[str] = None   # not stored in contact DB


class SessionOut(BaseModel):
    id: str
    campaign_id: str
    execution_type: str
    language: str
    status: str
    created_at: str
    prompt_text: Optional[str] = None


class RespondResult(BaseModel):
    session_id: str
    transcript: Optional[str]
    language: str
    intent: Optional[str]
    confidence: Optional[float]
    decision_method: str
    outcome: str
    is_simulation: bool = True
    error: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_session(session_id: str) -> dict:
    sb = get_supabase()
    resp = sb.table(_TABLE).select("*").eq("id", session_id).single().execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Session not found")
    return resp.data


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("/browser/start", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def start_browser_session(payload: StartSessionRequest):
    """
    Start a browser voice session for a campaign.
    Returns a session ID used for all subsequent calls.
    """
    # Verify campaign exists
    sb = get_supabase()
    camp_resp = sb.table("campaigns").select("id,name,language,status").eq("id", payload.campaign_id).single().execute()
    if not camp_resp.data:
        raise HTTPException(status_code=404, detail="Campaign not found")

    campaign = camp_resp.data
    lang = payload.language or campaign.get("language", "en")

    session_id = str(uuid.uuid4())
    now = _now()

    row = {
        "id": session_id,
        "campaign_id": payload.campaign_id,
        "execution_type": EXECUTION_TYPE,
        "language": lang,
        "status": "active",
        "is_simulation": True,
        "prompt_text": f"Hello! You have been invited to {campaign.get('name', 'a campaign')}. Please respond.",
        "created_at": now,
        "updated_at": now,
    }

    try:
        sb.table(_TABLE).insert(row).execute()
    except Exception as exc:
        log.error("browser_session_create_failed", error=str(exc))
        raise HTTPException(status_code=503, detail=f"Database error: {exc}")

    log.info("browser_session_started", session_id=session_id, campaign_id=payload.campaign_id, lang=lang)

    return SessionOut(
        id=session_id,
        campaign_id=payload.campaign_id,
        execution_type=EXECUTION_TYPE,
        language=lang,
        status="active",
        created_at=now,
        prompt_text=row["prompt_text"],
    )


@router.post("/browser/{session_id}/tts")
async def get_session_tts(session_id: str):
    """
    Generate TTS audio for the session's invitation prompt.
    Returns MP3 bytes directly.

    Provider priority:
    1. ElevenLabs (if ELEVENLABS_API_KEY set)
    2. AI service Sarvam TTS (if AI service reachable)
    3. 503 with explanation
    """
    session = _get_session(session_id)
    prompt = session.get("prompt_text", "Hello, please respond.")
    lang = session.get("language", "en")

    # 1. Try ElevenLabs
    if elevenlabs.is_available():
        try:
            audio = await elevenlabs.tts(prompt, language=lang)
            return Response(content=audio, media_type="audio/mpeg")
        except Exception as exc:
            log.warning("elevenlabs_tts_failed_fallback", error=str(exc))

    # 2. Try AI service TTS
    try:
        ai = get_ai_client()
        audio = await ai.tts(text=prompt, language=lang)
        return Response(content=audio, media_type="audio/wav")
    except Exception as exc:
        log.warning("ai_tts_failed", error=str(exc))

    raise HTTPException(
        status_code=503,
        detail="No TTS provider available. Set ELEVENLABS_API_KEY or configure the AI service.",
    )


@router.post("/browser/{session_id}/respond", response_model=RespondResult)
async def process_browser_response(
    session_id: str,
    audio: Optional[UploadFile] = File(default=None),
    text: Optional[str] = Form(default=None),
    dtmf: Optional[str] = Form(default=None),
    language: Optional[str] = Form(default=None),
):
    """
    Process a browser participant's response.

    Accepts one of:
    - audio: WAV/MP3 file upload (browser recording)
    - text:  Direct text input (fallback)
    - dtmf:  Key press ('1'=confirm, '2'=decline, '3'=callback, '0'=repeat)

    Runs: audio → STT → intent classification → persist → return explainability data.
    """
    session = _get_session(session_id)
    if session.get("status") not in ("active", "prompting"):
        raise HTTPException(status_code=409, detail=f"Session is already {session.get('status')}")

    lang = language or session.get("language", "en")
    transcript: Optional[str] = None
    intent: Optional[str] = None
    confidence: Optional[float] = None
    decision_method = "rules"
    error: Optional[str] = None

    # ── DTMF shortcut (no AI needed) ─────────────────────────────────────────
    if dtmf:
        dtmf_map = {"1": "confirm", "2": "decline", "3": "call_later", "0": "unclear"}
        intent = dtmf_map.get(dtmf.strip(), "unclear")
        transcript = f"[keypad:{dtmf}]"
        confidence = None
        decision_method = "dtmf_keypad"

    # ── Audio path ─────────────────────────────────────────────────────────────
    elif audio:
        audio_bytes = await audio.read()
        if len(audio_bytes) > _MAX_AUDIO_BYTES:
            raise HTTPException(status_code=413, detail=f"Audio exceeds {_MAX_AUDIO_BYTES // 1024 // 1024} MB limit")
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio upload")

        try:
            ai = get_ai_client()
            result = await ai.speech_intent(
                audio_bytes=audio_bytes,
                language=lang,
                allowed_intents=BROWSER_INTENTS,
            )
            transcript = result.text
            intent = result.intent
            confidence = result.confidence
            decision_method = result.source or "rules"
        except Exception as exc:
            log.warning("speech_intent_failed", error=str(exc))
            error = f"Speech processing failed: {exc}. Using fallback."
            intent = "unclear"
            decision_method = "fallback"

    # ── Text path ──────────────────────────────────────────────────────────────
    elif text:
        transcript = text.strip()
        try:
            ai = get_ai_client()
            result = await ai.intent(
                text=transcript,
                language=lang,
                allowed_intents=BROWSER_INTENTS,
            )
            intent = result.intent
            confidence = result.confidence
            decision_method = result.source or "rules"
        except Exception as exc:
            log.warning("text_intent_failed", error=str(exc))
            # Simple keyword fallback
            t_lower = transcript.lower()
            if any(w in t_lower for w in ["yes", "confirm", "attend", "coming", "will"]):
                intent = "confirm"
            elif any(w in t_lower for w in ["no", "can't", "cannot", "won't", "not"]):
                intent = "decline"
            else:
                intent = "unclear"
            decision_method = "keyword_fallback"
            error = str(exc)

    else:
        raise HTTPException(status_code=400, detail="Provide audio, text, or dtmf in the request")

    # ── Persist outcome ────────────────────────────────────────────────────────
    outcome = intent or "unclear"
    now = _now()

    sb = get_supabase()
    try:
        sb.table(_TABLE).update({
            "status": "completed",
            "transcript": transcript,
            "intent": intent,
            "confidence": confidence,
            "decision_method": decision_method,
            "outcome": outcome,
            "responded_at": now,
            "updated_at": now,
            "error_meta": {"error": error} if error else None,
        }).eq("id", session_id).execute()
    except Exception as exc:
        log.error("session_update_failed", error=str(exc))

    log.info(
        "browser_response_processed",
        session_id=session_id,
        intent=intent,
        method=decision_method,
        lang=lang,
    )

    return RespondResult(
        session_id=session_id,
        transcript=transcript,
        language=lang,
        intent=intent,
        confidence=confidence,
        decision_method=decision_method,
        outcome=outcome,
        is_simulation=True,
        error=error,
    )


@router.get("/browser/{session_id}", response_model=SessionOut)
async def get_browser_session(session_id: str):
    """Get current session state and outcome."""
    session = _get_session(session_id)
    return SessionOut(
        id=session["id"],
        campaign_id=session["campaign_id"],
        execution_type=session.get("execution_type", EXECUTION_TYPE),
        language=session.get("language", "en"),
        status=session.get("status", "unknown"),
        created_at=str(session.get("created_at", "")),
        prompt_text=session.get("prompt_text"),
    )


@router.post("/browser/{session_id}/end", status_code=status.HTTP_204_NO_CONTENT)
async def end_browser_session(session_id: str):
    """Mark session as abandoned if not already completed."""
    session = _get_session(session_id)
    if session.get("status") not in ("completed", "abandoned"):
        sb = get_supabase()
        sb.table(_TABLE).update({"status": "abandoned", "updated_at": _now()}).eq("id", session_id).execute()
