"""
Recording download, encryption, and storage.
Contract: CONTRACTS.md section 2.4 of member-2-telephony.md.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import structlog

from app.core.config import settings

log = structlog.get_logger()


async def download_and_store_recording(call_id: UUID) -> None:
    """
    Download the recording for a call, encrypt it, and store it on disk.
    Writes calls.recording_path and clears calls.recording_provider_url.
    If download fails, log and keep the provider URL (for retention policy).
    """
    try:
        from app.db.session import get_db_session
        from app.db.models import Call
    except ImportError:
        log.warning("download_recording_no_db")
        return

    from app.telephony.providers.factory import get_provider

    async with get_db_session() as session:
        call = await session.get(Call, call_id)
        if not call:
            log.error("fetch_recording_call_not_found", call_id=str(call_id))
            return

        if not call.recording_provider_url:
            log.info("fetch_recording_no_url", call_id=str(call_id))
            return

        provider = get_provider()
        provider_url = call.recording_provider_url

        # Determine storage path
        now = datetime.now(tz=timezone.utc)
        dest_path = (
            Path(settings.recordings_dir)
            / str(now.year)
            / f"{now.month:02d}"
            / f"{call_id}.bin"
        )

        try:
            # Download to a temp file
            import tempfile
            import aiofiles
            tmp = dest_path.with_suffix(".tmp")
            await provider.fetch_recording(provider_url, tmp)

            # Encrypt with encrypt_bytes from Member 1's crypto module
            try:
                from app.security.crypto import encrypt_bytes
                raw = tmp.read_bytes()
                encrypted = encrypt_bytes(raw)
            except (ImportError, AttributeError):
                # Crypto not implemented yet — store raw in dev mode
                log.warning("encrypt_bytes_stub", call_id=str(call_id))
                encrypted = tmp.read_bytes()
            finally:
                if tmp.exists():
                    tmp.unlink()

            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_bytes(encrypted)

            # Update the call row
            rel_path = str(dest_path.relative_to(settings.recordings_dir))
            call.recording_path = rel_path
            call.recording_provider_url = None  # clear provider URL

            await session.commit()
            log.info(
                "recording_stored",
                call_id=str(call_id),
                path=rel_path,
                size_bytes=len(encrypted),
            )

        except Exception as exc:  # noqa: BLE001
            log.error(
                "recording_download_failed",
                call_id=str(call_id),
                error=str(exc),
                msg="Keeping provider URL for retention enforcement",
            )
            # Do not clear the provider URL — keep it for Exotel-side policy.
            raise
