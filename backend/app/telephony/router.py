"""
Telephony router — mounts webhook routes under /webhooks/...
Included by main.py.
"""

from fastapi import APIRouter

from app.telephony.webhooks import router as webhooks_router

router = APIRouter()
router.include_router(webhooks_router, prefix="/webhooks")
