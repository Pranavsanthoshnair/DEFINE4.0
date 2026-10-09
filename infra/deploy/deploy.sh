#!/usr/bin/env bash
# infra/deploy/deploy.sh
# Veylo PR 002 — Idempotent deploy script
# Owner: Member 4
#
# Run as pr002 from /home/pr002/pr002/
# Usage: bash infra/deploy/deploy.sh

set -euo pipefail

REPO_DIR="/home/pr002/pr002"
COMPOSE="docker compose"

echo "======================================================"
echo " Veylo PR 002 — Deploy  $(date -Iseconds)"
echo "======================================================"

cd "$REPO_DIR"

# 1. Pull latest code
echo "→ Pulling latest code..."
git pull --ff-only

# 2. Rebuild images (only changed layers are rebuilt)
echo "→ Building images..."
$COMPOSE build

# 3. Bring up all services (recreate only changed containers)
echo "→ Starting services..."
$COMPOSE up -d --remove-orphans

# 4. Wait for postgres to be healthy
echo "→ Waiting for postgres..."
for i in $(seq 1 30); do
  if $COMPOSE exec -T postgres pg_isready -U pr002 -d pr002 &>/dev/null; then
    echo "   postgres ready."
    break
  fi
  echo "   attempt $i/30..."
  sleep 3
done

# 5. Run migrations
echo "→ Running migrations..."
$COMPOSE exec -T api alembic -c /app/alembic.ini upgrade head

# 6. Health checks
echo "→ Health checks..."
for svc in api web; do
  STATUS=$($COMPOSE ps --format json "$svc" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('Health','unknown'))" 2>/dev/null || echo "unknown")
  echo "   $svc: $STATUS"
done

# 7. Print versions
echo "→ Versions:"
$COMPOSE exec -T api python -c "import app; print('api:', getattr(app, '__version__', 'n/a'))"
$COMPOSE exec -T web node -e "const p=require('/app/package.json');console.log('web:',p.version)"
echo "   git: $(git rev-parse --short HEAD)"

echo "======================================================"
echo " Deploy complete  $(date -Iseconds)"
echo "======================================================"
