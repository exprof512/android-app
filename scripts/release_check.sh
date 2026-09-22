#!/usr/bin/env bash
# Phase 16 release-candidate smoke: health + APK presence.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PORT="${NGINX_PORT:-8080}"

echo "== Compose health =="
docker compose -f compose.yaml ps --format '{{.Name}} {{.Health}}'

echo "== HTTP =="
curl -fsS "http://127.0.0.1:${PORT}/health" | grep -q '"status":"ok"'
curl -fsS "http://127.0.0.1:${PORT}/health/deps" | grep -q '"postgres":"ok"'
echo "ok: health endpoints"

echo "== Android debug APK =="
APK="$ROOT/android/app/build/outputs/apk/debug/app-debug.apk"
if [[ ! -f "$APK" ]]; then
  echo "APK missing — run ./scripts/build_android.sh" >&2
  exit 1
fi
echo "$APK"

echo "== Production config reminders =="
echo "- Set APP_ENV=production and a strong JWT_SECRET before public deploy"
echo "- Serve API/media over TLS; keep secrets out of git and the APK"
echo "- Complete phone smoke items in docs/release-checklist.md"

echo "RELEASE CHECK SMOKE PASSED"
