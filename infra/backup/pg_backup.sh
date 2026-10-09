#!/usr/bin/env bash
# infra/backup/pg_backup.sh
# Veylo PR 002 — Nightly PostgreSQL backup
# Owner: Member 4
#
# Schedule: cron or systemd timer at 02:30 IST (21:00 UTC)
# crontab entry (as pr002):
#   0 21 * * * /home/pr002/pr002/infra/backup/pg_backup.sh >> /home/pr002/backups/backup.log 2>&1
#
# Requirements on the server:
#   - docker (to exec into the postgres container)
#   - age  (https://github.com/FiloSottile/age)  OR  gpg
#   - AGE_RECIPIENT env var set to the public key (stored in .env or exported before calling)
#
# The backup key (private) must NOT be stored on the server.
# Keep it on a team member's laptop or a separate secure store.

set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
BACKUP_DIR="/home/pr002/backups"
CONTAINER="pr002-postgres"
DB_NAME="pr002"
DB_USER="pr002"
KEEP_DAYS=7
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DUMP_FILE="${BACKUP_DIR}/pr002_${TIMESTAMP}.dump"
ENC_FILE="${DUMP_FILE}.age"

# Source .env for POSTGRES_PASSWORD and AGE_RECIPIENT if not already set
ENV_FILE="/home/pr002/pr002/.env"
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  set -o allexport; source "$ENV_FILE"; set +o allexport
fi

: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD must be set}"
: "${AGE_RECIPIENT:?AGE_RECIPIENT (age public key) must be set}"

# ── Backup ────────────────────────────────────────────────────────────────────
mkdir -p "$BACKUP_DIR"
echo "[$(date -Iseconds)] Starting backup → ${ENC_FILE}"

# pg_dump in custom format (compressed, supports selective restore)
docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$CONTAINER" \
  pg_dump -U "$DB_USER" -d "$DB_NAME" -Fc \
  > "$DUMP_FILE"

# Encrypt with age (recipient's public key — private key stays off-server)
age --recipient "$AGE_RECIPIENT" --output "$ENC_FILE" "$DUMP_FILE"
rm -f "$DUMP_FILE"   # remove plaintext immediately

echo "[$(date -Iseconds)] Backup complete: ${ENC_FILE} ($(du -sh "$ENC_FILE" | cut -f1))"

# ── Also backup media and recordings volumes (weekly, on Sunday) ──────────────
if [[ "$(date +%u)" == "7" ]]; then
  MEDIA_TAR="${BACKUP_DIR}/pr002_media_${TIMESTAMP}.tar.gz.age"
  echo "[$(date -Iseconds)] Weekly volume backup → ${MEDIA_TAR}"
  docker run --rm \
    -v pr002_media:/data/media:ro \
    -v pr002_recordings:/data/recordings:ro \
    alpine tar czf - /data/media /data/recordings \
    | age --recipient "$AGE_RECIPIENT" --output "$MEDIA_TAR"
  echo "[$(date -Iseconds)] Volume backup complete: ${MEDIA_TAR}"
fi

# ── Prune old backups ─────────────────────────────────────────────────────────
find "$BACKUP_DIR" -name "pr002_*.age" -mtime "+${KEEP_DAYS}" -delete
echo "[$(date -Iseconds)] Pruned backups older than ${KEEP_DAYS} days"
