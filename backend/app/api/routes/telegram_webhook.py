"""
Telegram bot webhook handler.

Activated ONLY when TELEGRAM_BOT_TOKEN is set.
When not configured, all routes return 503 with a clear message.

Webhook URL to register in BotFather:
  https://YOUR_BACKEND.onrender.com/api/v1/telegram/webhook

Security:
- Validates X-Telegram-Bot-Api-Secret-Token header
- Deduplicates update_id
- Never logs message contents beyond update_id and chat_id

Supported incoming message types:
- /start command       → send welcome + campaign list
- text message         → classify intent via AI
- voice note           → download → STT → classify → acknowledge
- photo/document       → politely decline

Bot capabilities (outbound):
- Text messages
- Audio invitations (MP3 from TTS)
- Inline keyboard buttons for fallback RSVP
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
import structlog
from fastapi import APIRouter, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.ai_client.client import get_ai_client
from app.core.config import settings
from app.db.supabase_client import get_supabase
from app.providers import elevenlabs

log = structlog.get_logger()
router = APIRouter()

_TG_API = "https://api.telegram.org/bot{token}"
_MAX_VOICE_BYTES = 8 * 1024 * 1024    # 8 MB
_SEEN_UPDATES: set[int] = set()        # in-process dedup; replace with Redis in prod
_MAX_SEEN = 10_000                     # cap memory growth


def _tg(path: str) -> str:
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set")
    return f"https://api.telegram.org/bot{settings.telegram_bot_token}{path}"


def _unavailable_response() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Telegram bot is not configured. Set TELEGRAM_BOT_TOKEN."},
    )


# ── Security ──────────────────────────────────────────────────────────────────

def _check_secret(secret_header: Optional[str]) -> bool:
    """Validate X-Telegram-Bot-Api-Secret-Token against configured secret."""
    if not settings.telegram_webhook_secret:
        return True   # no secret configured — allow (set one in prod)
    if not secret_header:
        return False
    return hmac.compare_digest(
        secret_header.encode(),
        settings.telegram_webhook_secret.encode(),
    )


# ── Telegram API helpers ──────────────────────────────────────────────────────

async def _send_message(chat_id: int | str, text: str, reply_markup: Optional[dict] = None) -> None:
    body: dict[str, Any] = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        body["reply_markup"] = reply_markup
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(_tg("/sendMessage"), json=body)


async def _send_audio(chat_id: int | str, audio_bytes: bytes, caption: str = "") -> None:
    async with httpx.AsyncClient(timeout=30) as client:
        await client.post(
            _tg("/sendAudio"),
            data={"chat_id": str(chat_id), "caption": caption},
            files={"audio": ("invite.mp3", audio_bytes, "audio/mpeg")},
        )


async def _get_file(file_id: str) -> bytes:
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(_tg(f"/getFile?file_id={file_id}"))
        r.raise_for_status()
        file_path = r.json()["result"]["file_path"]
        audio_r = await client.get(
            f"https://api.telegram.org/file/bot{settings.telegram_bot_token}/{file_path}"
        )
        audio_r.raise_for_status()
        return audio_r.content


def _rsvp_keyboard() -> dict:
    """Inline keyboard for text-fallback RSVP."""
    return {
        "inline_keyboard": [
            [
                {"text": "✅ Attending", "callback_data": "intent:confirm"},
                {"text": "❌ Not attending", "callback_data": "intent:decline"},
            ],
            [
                {"text": "📞 Request callback", "callback_data": "intent:call_later"},
            ],
        ]
    }


# ── Intent helpers ────────────────────────────────────────────────────────────

_INTENT_LABELS = {
    "confirm": "✅ Attending — thank you! Your response has been recorded.",
    "decline": "❌ Not attending — noted. Thank you for letting us know.",
    "call_later": "📞 Callback requested — we'll reach out again.",
    "reschedule": "🔄 Reschedule requested — we'll follow up with new timing.",
    "stop_calling": "🛑 Opted out — you won't receive further invitations.",
    "unclear": "🤔 We couldn't understand your response. Please try again or use the buttons below.",
}


async def _classify_text(text: str, language: str = "en") -> tuple[str, Optional[float], str]:
    """Returns (intent, confidence, method) using the unified cascade."""
    from app.services.intent_service import classify_intent
    intent, confidence, method = await classify_intent(text=text, language=language)
    return intent, confidence, method


async def _send_voice_reply(chat_id: int | str, text: str, language: str) -> None:
    """Send a spoken response, with a text fallback when TTS is unavailable."""
    try:
        from app.services.tts_service import synthesize_text
        audio, _provider = await synthesize_text(text, language)
        await _send_audio(chat_id, audio)
    except Exception as exc:
        log.warning("telegram_tts_failed", error_type=type(exc).__name__)
        await _send_message(chat_id, text)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _active_session(chat_id: int | str, campaign_id: Optional[str] = None) -> Optional[dict]:
    """Find the latest active Telegram session for this chat."""
    sb = get_supabase()
    query = (
        sb.table("execution_sessions")
        .select("*")
        .eq("telegram_chat_id", str(chat_id))
        .in_("status", ["active", "prompting"])
        .order("created_at", desc=True)
        .limit(1)
    )
    if campaign_id:
        query = query.eq("campaign_id", campaign_id)
    response = query.execute()
    return (response.data or [None])[0]


def _create_telegram_session(chat_id: int | str, campaign: dict, language: str, prompt: str) -> dict:
    session = {
        "id": str(uuid.uuid4()),
        "campaign_id": campaign["id"],
        "execution_type": "TELEGRAM",
        "language": language,
        "status": "active",
        "is_simulation": False,
        "prompt_text": prompt,
        "telegram_chat_id": str(chat_id),
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
    }
    get_supabase().table("execution_sessions").insert(session).execute()
    return session


async def _persist_telegram_response(
    chat_id: int | str,
    transcript: Optional[str],
    intent: str,
    confidence: Optional[float],
    method: str,
    campaign_id: Optional[str] = None,
) -> Optional[dict]:
    """Persist the reply to its active campaign session."""
    session = _active_session(chat_id, campaign_id)
    if not session:
        return None
    now = _utc_now()
    get_supabase().table("execution_sessions").update({
        "status": "completed",
        "transcript": transcript,
        "intent": intent,
        "confidence": confidence,
        "decision_method": method,
        "outcome": intent,
        "responded_at": now,
        "updated_at": now,
    }).eq("id", session["id"]).execute()
    return session


async def _respond_to_telegram(
    chat_id: int | str,
    transcript: Optional[str],
    intent: str,
    confidence: Optional[float],
    method: str,
    campaign_id: Optional[str] = None,
) -> None:
    """Send spoken acknowledgement and mark the matching site session complete."""
    session = await _persist_telegram_response(
        chat_id, transcript, intent, confidence, method, campaign_id
    )
    reply = _INTENT_LABELS.get(intent, _INTENT_LABELS["unclear"])
    language = (session or {}).get("language", "en")
    await _send_voice_reply(chat_id, reply, language)
    if intent == "unclear":
        await _send_message(chat_id, "Please choose an option:", reply_markup=_rsvp_keyboard())
    if not session:
        log.info("telegram_response_without_active_session", chat_id=str(chat_id))


# ── Update handlers ───────────────────────────────────────────────────────────

async def _handle_voice(chat_id: int, voice: dict, language: str = "en") -> None:
    active = _active_session(chat_id)
    language = (active or {}).get("language", language)
    """Download voice note → STT → classify → persist → reply."""
    file_id: Optional[str] = voice.get("file_id")
    file_size: int = voice.get("file_size", 0)

    if not file_id:
        await _send_message(chat_id, "⚠️ Could not read voice note file ID. Please try again.")
        return

    if file_size > _MAX_VOICE_BYTES:
        await _send_message(chat_id, "⚠️ Voice note too large (max 8 MB). Please send a shorter message.")
        return

    try:
        audio_bytes = await _get_file(file_id)
    except Exception as exc:
        log.error("telegram_get_file_failed", error=str(exc))
        await _send_message(chat_id, "⚠️ Could not download your voice note. Please try text.")
        return

    transcript: Optional[str] = None
    intent: Optional[str] = None
    confidence: Optional[float] = None
    method = "rules"

    try:
        ai = get_ai_client()
        result = await ai.speech_intent(
            audio_bytes=audio_bytes,
            language=language,
            allowed_intents=list(_INTENT_LABELS.keys()),
        )
        transcript = result.text
        intent = result.intent
        confidence = result.confidence
        method = result.source or "rules"
        await _respond_to_telegram(
            chat_id,
            transcript,
            intent or "unclear",
            confidence,
            method,
        )
        return
    except Exception as exc:
        log.warning("telegram_stt_failed", error=str(exc))
        await _send_message(
            chat_id,
            "⚠️ Could not process your voice note. Please use the buttons or type your response.",
            reply_markup=_rsvp_keyboard(),
        )
        return

    reply = _INTENT_LABELS.get(intent or "unclear", _INTENT_LABELS["unclear"])
    if transcript:
        reply = f'🎤 Heard: "<i>{transcript}</i>"\n\n{reply}'

    await _send_message(chat_id, reply, reply_markup=_rsvp_keyboard() if intent == "unclear" else None)

    # Persist to Supabase
    try:
        sb = get_supabase()
        sb.table("execution_sessions").insert({
            "id": __import__("uuid").uuid4().__str__(),
            "campaign_id": None,   # no campaign context in this flow yet
            "execution_type": "TELEGRAM",
            "language": language,
            "status": "completed",
            "is_simulation": False,
            "transcript": transcript,
            "intent": intent,
            "confidence": confidence,
            "decision_method": method,
            "outcome": intent or "unclear",
            "telegram_chat_id": str(chat_id),
            "created_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            "updated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        }).execute()
    except Exception as exc:
        log.error("telegram_persist_failed", error=str(exc))


async def _handle_callback_query(callback: dict) -> None:
    """Handle inline keyboard button presses."""
    chat_id = callback["message"]["chat"]["id"]
    data = callback.get("data", "")
    callback_query_id = callback["id"]

    campaign_id: Optional[str] = None
    if data.startswith("campaign:"):
        _, campaign_id, intent = data.split(":", 2)
    elif data.startswith("intent:"):
        intent = data.split("intent:", 1)[1]
    else:
        intent = "unclear"
    await _respond_to_telegram(chat_id, None, intent, None, "telegram_button", campaign_id)

    # Answer callback to remove loading spinner
    async with httpx.AsyncClient(timeout=5) as client:
        await client.post(_tg("/answerCallbackQuery"), json={"callback_query_id": callback_query_id})


# ── Webhook endpoint ──────────────────────────────────────────────────────────

@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(default=None),
):
    """
    Telegram webhook endpoint.
    Register at: https://api.telegram.org/bot{TOKEN}/setWebhook?url=YOUR_URL/api/v1/telegram/webhook
    """
    if not settings.telegram_bot_token:
        return _unavailable_response()

    if not _check_secret(x_telegram_bot_api_secret_token):
        return JSONResponse(status_code=404, content={})   # 404 = not discoverable

    try:
        update = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"detail": "Invalid JSON"})

    update_id = update.get("update_id")

    # Deduplication
    if update_id in _SEEN_UPDATES:
        log.info("telegram_duplicate_update", update_id=update_id)
        return JSONResponse({"ok": True})

    if len(_SEEN_UPDATES) < _MAX_SEEN:
        _SEEN_UPDATES.add(update_id)

    log.info("telegram_update", update_id=update_id)

    # Dispatch
    try:
        if "message" in update:
            msg = update["message"]
            chat_id = msg["chat"]["id"]
            text = msg.get("text", "")

            if text.startswith("/start"):
                parts = text.split(maxsplit=1)
                if len(parts) == 2:
                    campaign_id = parts[1].strip()
                    try:
                        campaign_resp = get_supabase().table("campaigns").select("*").eq("id", campaign_id).single().execute()
                        campaign = campaign_resp.data
                        if campaign:
                            language = (campaign.get("language") or "en").lower()
                            from app.services.tts_service import build_localized_prompt
                            prompt = await build_localized_prompt(campaign, language)
                            _create_telegram_session(chat_id, campaign, language, prompt)
                            await _send_voice_reply(chat_id, prompt, language)
                            await _send_message(chat_id, "Please reply by voice, text, or number:", reply_markup=_rsvp_keyboard())
                            return JSONResponse({"ok": True})
                    except Exception as exc:
                        log.warning("telegram_start_campaign_failed", error_type=type(exc).__name__)
                await _send_message(
                    chat_id,
                    "👋 Welcome to <b>Veylo</b>!\n\n"
                    "You'll receive campaign invitations here.\n"
                    "Reply with a voice note or use the buttons to respond.\n\n"
                    "Type /help for more information.",
                )

            elif text.startswith("/help"):
                await _send_message(
                    chat_id,
                    "📋 <b>How it works:</b>\n"
                    "• You'll receive invitations from campaigns.\n"
                    "• Reply with a voice note or tap the response buttons.\n"
                    "• Your response will be recorded automatically.\n\n"
                    "To opt out of all campaigns, reply: <code>stop</code>",
                )

            elif "voice" in msg:
                language = "en"   # TODO: detect from user profile
                asyncio.create_task(_handle_voice(chat_id, msg["voice"], language))

            elif text:
                intent, confidence, method = await _classify_text(text)
                if text.strip() in {"1", "2", "3", "0"}:
                    intent = {"1": "confirm", "2": "decline", "3": "call_later", "0": "unclear"}[text.strip()]
                    method = "telegram_keypad"
                await _respond_to_telegram(chat_id, text, intent, confidence, method)
                return JSONResponse({"ok": True})
                reply = _INTENT_LABELS.get(intent, _INTENT_LABELS["unclear"])
                await _send_message(
                    chat_id,
                    reply,
                    reply_markup=_rsvp_keyboard() if intent == "unclear" else None,
                )

        elif "callback_query" in update:
            asyncio.create_task(_handle_callback_query(update["callback_query"]))

    except Exception as exc:
        log.error("telegram_handler_error", update_id=update_id, error=str(exc))

    # Always return 200 to Telegram to prevent retry storms
    return JSONResponse({"ok": True})


@router.get("/webhook/info")
async def telegram_bot_info():
    """Return bot configuration info (no secrets). For dashboard display."""
    if not settings.telegram_bot_token:
        return {"configured": False, "reason": "TELEGRAM_BOT_TOKEN not set"}
    webhook_url = f"{settings.webhook_base_url}/api/v1/telegram/webhook"
    return {
        "configured": True,
        "webhook_url": webhook_url,
        "mode": settings.telegram_mode,
        "start_link": "https://t.me/YOUR_BOT_USERNAME",   # update after /setWebhook
        "setup_command": (
            f"curl 'https://api.telegram.org/bot{{TOKEN}}/setWebhook"
            f"?url={webhook_url}"
            f"&secret_token={{TELEGRAM_WEBHOOK_SECRET}}'"
        ),
    }
