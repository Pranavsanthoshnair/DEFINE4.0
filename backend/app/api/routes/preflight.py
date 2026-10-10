"""H8 — Preflight check endpoint."""
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from app.db.supabase_client import get_supabase, is_supabase_configured
from app.core.config import settings
from app.telephony.providers.factory import active_provider_name

router = APIRouter()


@router.get("/{campaign_id}/preflight")
async def preflight_check(campaign_id: str):
    """
    H8: Pre-launch checklist. Returns pass/fail for every launch requirement.
    Launch should be blocked until all critical checks pass.
    """
    checks = []

    def check(name: str, passed: bool, detail: str, critical: bool = True):
        checks.append({"name": name, "passed": passed, "detail": detail, "critical": critical})

    if not is_supabase_configured():
        return {"ready": False, "checks": [{"name": "Database", "passed": False,
                "detail": "Supabase not configured", "critical": True}]}

    sb = get_supabase()

    # 1. Campaign exists
    try:
        camp = sb.table("campaigns").select("*").eq("id", campaign_id).single().execute().data
        if not camp:
            raise ValueError()
        check("Campaign found", True, f"Campaign '{camp.get('name')}' loaded")
    except Exception:
        return {"ready": False, "checks": [{"name": "Campaign found", "passed": False,
                "detail": "Campaign not found", "critical": True}]}

    # 2. Contacts loaded
    try:
        cc = sb.table("campaign_contacts").select("id", count="exact")\
               .eq("campaign_id", campaign_id).eq("status", "pending").execute()
        count = cc.count or 0
        check("Pending contacts", count > 0,
              f"{count} pending contact(s)" if count > 0 else "No contacts — add contacts first")
    except Exception as e:
        check("Pending contacts", False, str(e))

    # 3. Audio pre-generated
    audio_ready = False
    try:
        audio_urls = camp.get("audio_urls") or {}
        if not audio_urls:
            import json as _j
            brief = camp.get("brief") or ""
            if isinstance(brief, str) and brief.startswith("{"):
                audio_urls = _j.loads(brief).get("audio_urls") or {}
        segments = sum(1 for v in audio_urls.values() if v)
        audio_ready = segments > 0
        check("Audio pre-generated", audio_ready,
              f"{segments} audio segment(s) ready" if audio_ready else "Click 'Prepare Audio' first")
    except Exception as e:
        check("Audio pre-generated", False, str(e))

    # 4. Telephony provider configured
    provider = active_provider_name()
    check("Telephony provider", provider != "mock",
          f"Active provider: {provider}" if provider != "mock"
          else "No Exotel/Twilio credentials — calls will use mock provider")

    # 5. Caller ID set
    caller_id = settings.exotel_caller_id or settings.twilio_phone_number
    check("Caller ID configured", bool(caller_id),
          f"Caller ID: {caller_id}" if caller_id else "Set EXOTEL_CALLER_ID in environment")

    # 6. Webhook URL set
    webhook_ok = (settings.webhook_base_url and
                  "your-backend" not in settings.webhook_base_url and
                  "localhost" not in settings.webhook_base_url)
    check("Webhook URL", webhook_ok,
          f"Webhook base: {settings.webhook_base_url}" if webhook_ok
          else f"Set WEBHOOK_BASE_URL to your public backend URL (currently: {settings.webhook_base_url})")

    # 7. Campaign not already running
    status_val = camp.get("status", "draft")
    check("Campaign status", status_val not in ("running", "completed"),
          f"Status: {status_val}" if status_val not in ("running", "completed")
          else f"Campaign is already {status_val}")

    critical_failed = [c for c in checks if c["critical"] and not c["passed"]]
    ready = len(critical_failed) == 0

    return {
        "ready": ready,
        "campaign_id": campaign_id,
        "campaign_name": camp.get("name"),
        "checks": checks,
        "summary": f"{'✅ Ready to launch' if ready else f'❌ {len(critical_failed)} check(s) failed'}",
    }
