#!/usr/bin/env bash
# infra/backup/restore_test.sh
# Veylo PR 002 — Backup restore test
# Owner: Member 4
#
# Restores the latest encrypted backup into a scratch database and runs
# a sanity count query. Run manually before the demo and after any schema change.
#
# Requirements: docker, age (with AGE_IDENTITY env var pointing to the private key file)

set -euo pipefail

BACKUP_DIR="/home/pr002/backups"
CONTAINER="pr002-postgres"
DB_USER="pr002"
SCRATCH_DB="pr002_restore_test"

ENV_FILE="/home/pr002/pr002/.env"
if [[ -f "$ENV_FILE" ]]; then
  set -o allexport; source "$ENV_FILE"; set +o allexport
fi

: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD must be set}"
: "${AGE_IDENTITY:?AGE_IDENTITY (path to age private key file) must be set}"

# Find latest backup
LATEST=$(find "$BACKUP_DIR" -name "pr002_*.dump.age" | sort | tail -1)
if [[ -z "$LATEST" ]]; then
  echo "ERROR: No backup file found in $BACKUP_DIR"
  exit 1
fi
echo "[$(date -Iseconds)] Restoring from: $LATEST"

# Decrypt to temp file
TEMP_DUMP=$(mktemp /tmp/pr002_restore_XXXXXX.dump)
trap 'rm -f "$TEMP_DUMP"' EXIT

age --decrypt --identity "$AGE_IDENTITY" --output "$TEMP_DUMP" "$LATEST"
echo "[$(date -Iseconds)] Decrypted successfully ($(du -sh "$TEMP_DUMP" | cut -f1))"

# Create scratch DB
docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$CONTAINER" \
  psql -U "$DB_USER" -c "DROP DATABASE IF EXISTS ${SCRATCH_DB};" postgres
docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$CONTAINER" \
  psql -U "$DB_USER" -c "CREATE DATABASE ${SCRATCH_DB};" postgres

# Restore
cat "$TEMP_DUMP" | docker exec -i -e PGPASSWORD="$POSTGRES_PASSWORD" "$CONTAINER" \
  pg_restore -U "$DB_USER" -d "$SCRATCH_DB" --no-owner --no-privileges -Fc

# Sanity checks
echo "[$(date -Iseconds)] Running sanity queries..."
docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$CONTAINER" \
  psql -U "$DB_USER" -d "$SCRATCH_DB" -c "
    SELECT 'campaigns' AS tbl, COUNT(*) FROM campaigns
    UNION ALL
    SELECT 'contacts', COUNT(*) FROM contacts
    UNION ALL
    SELECT 'campaign_contacts', COUNT(*) FROM campaign_contacts
    UNION ALL
    SELECT 'calls', COUNT(*) FROM calls;
  "

# Drop scratch DB
docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$CONTAINER" \
  psql -U "$DB_USER" -c "DROP DATABASE ${SCRATCH_DB};" postgres

echo "[$(date -Iseconds)] Restore test PASSED. Scratch DB dropped."
