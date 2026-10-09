# Veylo AI Service — Dockerfile
# Multi-stage: base layer with system deps, then app layer.
# Model weights live in a mounted volume (/models), NOT baked into the image.

FROM python:3.12-slim AS base

# System deps: ffmpeg for audio post-processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Dependency layer (cached unless pyproject.toml changes) ──────────────────
FROM base AS deps
COPY pyproject.toml ./
RUN pip install --no-cache-dir \
    fastapi==0.115.5 \
    "uvicorn[standard]==0.32.1" \
    pydantic==2.10.3 \
    pydantic-settings==2.6.1 \
    python-dotenv==1.0.1 \
    python-multipart==0.0.20 \
    structlog==24.4.0 \
    "httpx>=0.26.0,<0.29.0" \
    pyyaml \
    soundfile \
    numpy \
    pytest==8.3.4 \
    pytest-asyncio==0.24.0

# ── App layer ─────────────────────────────────────────────────────────────────
FROM deps AS app
COPY . .

# Non-root user for security
RUN useradd -m -u 1000 veylo && chown -R veylo:veylo /app
USER veylo

# Models volume (mount with actual weights at runtime)
VOLUME ["/models"]

ENV AI_STUB=true \
    PORT=8200 \
    MODELS_DIR=/models \
    PYTHONUNBUFFERED=1 \
    OMP_NUM_THREADS=4

EXPOSE 8200

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8200/healthz')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8200", "--workers", "1"]
