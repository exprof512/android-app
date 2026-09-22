#!/usr/bin/env bash
# Smoke: AI text cache fingerprint stability + Redis ping via backend health.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PORT="${NGINX_PORT:-8080}"

curl -fsS "http://127.0.0.1:${PORT}/health/deps" | grep -q '"redis":"ok"'
echo "ok: redis reachable via /health/deps"

docker compose -f compose.yaml exec -T backend python - <<'PY'
from app.ai.cache import MemoryCacheStore, TextAICache
import asyncio

async def main() -> None:
    cache = TextAICache(MemoryCacheStore(), ttl_seconds=60, schema_version=1)
    payload = {"locale": "ru-RU", "days": [{"date": "2026-09-22"}]}
    a = cache.fingerprint(operation="generate_meal_plan_proposal", model="m", payload=payload)
    b = cache.fingerprint(operation="generate_meal_plan_proposal", model="m", payload=payload)
    assert a == b, "fingerprint must be stable"
    await cache.set(a, {"ok": True})
    hit = await cache.get(a)
    assert hit == {"ok": True}
    print("ok: text AI cache fingerprint + hit")

asyncio.run(main())
PY

echo "CACHE SMOKE PASSED"
