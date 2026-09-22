#!/usr/bin/env bash
# Logical Postgres dump + MinIO bucket mirror into ./backups/<timestamp>/.
# Secrets are read from .env / Compose; nothing is printed.
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
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$ROOT/backups/$STAMP"
mkdir -p "$OUT/minio"

echo "Writing Postgres dump to backups/${STAMP}/postgres.sql.gz"
"${COMPOSE[@]}" exec -T postgres \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --format=plain \
  | gzip -c > "$OUT/postgres.sql.gz"

NETWORK="$("${COMPOSE[@]}" ps -q backend | xargs -I{} docker inspect -f '{{range $k,$v := .NetworkSettings.Networks}}{{$k}}{{end}}' {})"
if [[ -z "$NETWORK" ]]; then
  echo "Could not resolve Compose network" >&2
  exit 1
fi

echo "Mirroring MinIO bucket ${S3_BUCKET:-foodai-images} (no credentials logged)"
# Prefer quay.io — Docker Hub often denies anonymous minio/mc pulls.
MC_IMAGE="${FOODAI_MC_IMAGE:-quay.io/minio/mc:RELEASE.2025-08-13T08-35-41Z}"
MC_USER="${S3_ACCESS_KEY:-$MINIO_ROOT_USER}"
MC_PASS="${S3_SECRET_KEY:-$MINIO_ROOT_PASSWORD}"
docker run --rm \
  --network "$NETWORK" \
  -e MC_USER \
  -e MC_PASS \
  -e S3_BUCKET="${S3_BUCKET:-foodai-images}" \
  -v "$OUT/minio:/backup" \
  --entrypoint /bin/sh \
  "$MC_IMAGE" \
  -c 'mc alias set local http://minio:9000 "$MC_USER" "$MC_PASS" >/dev/null && mc mirror --quiet "local/$S3_BUCKET" /backup'

# Consistency marker: schema revision + ready image object counts (keys only).
"${COMPOSE[@]}" exec -T postgres \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -Atc \
  "SELECT 'alembic=' || version_num FROM alembic_version; SELECT 'ready_images=' || count(*) FROM recipe_images WHERE generation_status='ready';" \
  > "$OUT/consistency.txt"

echo "$OUT"
