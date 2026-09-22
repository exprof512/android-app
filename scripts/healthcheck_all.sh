#!/usr/bin/env bash
# Verify Compose service healthchecks and public /health endpoints.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

COMPOSE=(docker compose -f compose.yaml)
PORT="${NGINX_PORT:-8080}"

echo "== docker compose ps =="
"${COMPOSE[@]}" ps

echo "== waiting for healthy containers =="
for svc in postgres redis minio backend worker nginx; do
  ok=0
  for _ in $(seq 1 36); do
    status="$("${COMPOSE[@]}" ps --format '{{.Service}} {{.Health}}' | awk -v s="$svc" '$1==s {print $2}')"
    if [[ "$status" == "healthy" ]]; then
      ok=1
      break
    fi
    sleep 2
  done
  if [[ "$ok" -ne 1 ]]; then
    echo "FAIL: service $svc is not healthy (status=${status:-unknown})" >&2
    exit 1
  fi
  echo "ok: $svc"
done

echo "== HTTP health =="
curl -fsS "http://127.0.0.1:${PORT}/health" | grep -q '"status":"ok"'
echo "ok: /health"

deps="$(curl -fsS "http://127.0.0.1:${PORT}/health/deps")"
echo "$deps" | grep -q '"postgres":"ok"'
echo "$deps" | grep -q '"redis":"ok"'
echo "ok: /health/deps ($deps)"

echo "ALL HEALTHCHECKS PASSED"
