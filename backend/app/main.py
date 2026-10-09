"""
Veylo — FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import health, campaigns, contacts, calls, analytics, webhooks, admin
from app.api.routes import capabilities, sessions, telegram_webhook, audio
from app.api.compat_router import compat_router
from app.telephony.router import router as telephony_router
from app.templates.router import router as templates_router

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    log.info("veylo_api_started", env=settings.environment)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Veylo API",
        description="AI-assisted multilingual calling campaign platform",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS ────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ─────────────────────────────────────────────────────────────
    app.include_router(health.router, tags=["health"])
    app.include_router(campaigns.router, prefix="/api/v1/campaigns", tags=["campaigns"])
    app.include_router(contacts.router, prefix="/api/v1/contacts", tags=["contacts"])
    app.include_router(calls.router, prefix="/api/v1/calls", tags=["calls"])
    app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
    app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["webhooks"])
    app.include_router(admin.router, prefix="/api/v1", tags=["admin"])
    app.include_router(capabilities.router, prefix="/api/v1", tags=["capabilities"])
    app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["sessions"])
    app.include_router(audio.router, prefix="/api/v1", tags=["audio"])  # public — telephony fetch
    app.include_router(
        telegram_webhook.router,
        prefix="/api/v1/telegram",
        tags=["telegram"],
    )
    app.include_router(telephony_router, tags=["telephony"])
    app.include_router(templates_router, tags=["templates"])  # GET /api/templates
    app.include_router(compat_router)  # /api/* aliases for frontend client

    return app


app = create_app()
