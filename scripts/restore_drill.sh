#!/usr/bin/env bash
# Restore the latest (or given) backup into an isolated Postgres DB and verify.
# Does NOT overwrite the live foodai database.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "Missing .env" >&2
  exit 1
fi
# shellcheck disable=SC1091
set -a
source .env
set +a

COMPOSE=(docker compose -f compose.yaml)
BACKUP_DIR="${1:-}"
if [[ -z "$BACKUP_DIR" ]]; then
  BACKUP_DIR="$(ls -1dt "$ROOT"/backups/* 2>/dev/null | head -1 || true)"
fi
if [[ -z "$BACKUP_DIR" || ! -f "$BACKUP_DIR/postgres.sql.gz" ]]; then
  echo "Usage: $0 [backups/<timestamp>]" >&2
  echo "No backup found. Run scripts/backup.sh first." >&2
  exit 1
fi

DRILL_DB="${POSTGRES_DB}_restore_drill"
DUMP="$BACKUP_DIR/postgres.sql.gz"

echo "Restore drill from $BACKUP_DIR into database $DRILL_DB"

"${COMPOSE[@]}" exec -T postgres \
  psql -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1 <<SQL
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${DRILL_DB}' AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS ${DRILL_DB};
CREATE DATABASE ${DRILL_DB} OWNER ${POSTGRES_USER};
SQL

gunzip -c "$DUMP" | "${COMPOSE[@]}" exec -T postgres \
  psql -U "$POSTGRES_USER" -d "$DRILL_DB" -v ON_ERROR_STOP=1 >/dev/null

echo "== schema / integrity checks =="
version="$("${COMPOSE[@]}" exec -T postgres \
  psql -U "$POSTGRES_USER" -d "$DRILL_DB" -Atc "SELECT version_num FROM alembic_version")"
echo "alembic_version=$version"
[[ -n "$version" ]]

tables="$("${COMPOSE[@]}" exec -T postgres \
  psql -U "$POSTGRES_USER" -d "$DRILL_DB" -Atc \
  "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")"
echo "public_tables=$tables"
[[ "$tables" -ge 10 ]]

# Ready images must have storage keys (bytes live in MinIO backup mirror).
missing="$("${COMPOSE[@]}" exec -T postgres \
  psql -U "$POSTGRES_USER" -d "$DRILL_DB" -Atc \
  "SELECT count(*) FROM recipe_images WHERE generation_status='ready' AND (storage_key IS NULL OR storage_key='')")"
echo "ready_images_missing_keys=$missing"
[[ "$missing" -eq 0 ]]

if [[ -d "$BACKUP_DIR/minio" ]]; then
  objects="$(find "$BACKUP_DIR/minio" -type f | wc -l | tr -d ' ')"
  echo "minio_mirrored_files=$objects"
fi

echo "Cleaning up drill database $DRILL_DB"
"${COMPOSE[@]}" exec -T postgres \
  psql -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1 \
  -c "DROP DATABASE IF EXISTS ${DRILL_DB};" >/dev/null

echo "RESTORE DRILL PASSED"
