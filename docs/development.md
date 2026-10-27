# Development workflow FoodAI

Phase 0 фиксирует layout и правила разработки. Спецификация ниже — source of truth даже после появления кода: реализация идёт по [roadmap.md](roadmap.md) и не должна расходиться с этими правилами без обновления docs.

## Целевая структура repository

```text
/
├── docs/
│   ├── architecture.md
│   ├── api.md
│   ├── database.md
│   ├── roadmap.md
│   ├── ai.md
│   ├── image-generation.md
│   ├── storage.md
│   └── development.md
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   ├── auth/
│   │   ├── profiles/
│   │   ├── nutrition/
│   │   ├── recipes/
│   │   ├── meal_plans/
│   │   ├── shopping/
│   │   ├── chat/
│   │   ├── entitlements/
│   │   ├── images/
│   │   │   ├── client.py
│   │   │   ├── generator.py
│   │   │   ├── prompts.py
│   │   │   ├── storage.py
│   │   │   ├── schemas.py
│   │   │   └── service.py
│   │   ├── integrations/openai/
│   │   │   ├── client.py
│   │   │   ├── text.py
│   │   │   └── images.py
│   │   ├── workers/
│   │   └── core/
│   ├── alembic/
│   └── tests/
├── android/
├── scripts/
├── .env.example
└── compose.yaml
```

Это specification, а не требование создавать пустые папки заранее. `backend/app/integrations/openai/` — единственное место для OpenAI SDK. `backend/app/images/` — отдельный image domain с обязательными файлами, указанными в [image-generation.md](image-generation.md).

## Environment configuration

`.env` — локальный файл разработчика, в `.gitignore`; он не передаётся Android, не коммитится и не вставляется в логи. `.env.example` коммитится только с пустыми secrets и безопасными sample defaults:

```dotenv
APP_ENV=development
LOG_LEVEL=INFO
API_PREFIX=/api/v1
DATABASE_URL=postgresql+asyncpg://foodai:CHANGE_ME@postgres:5432/foodai
REDIS_URL=redis://redis:6379/0
JWT_SECRET=CHANGE_ME
JWT_ACCESS_TTL_SECONDS=900
JWT_REFRESH_TTL_DAYS=30
PASSWORD_HASHER=argon2id

OPENAI_API_KEY=
OPENAI_TEXT_MODEL=
OPENAI_TEXT_TIMEOUT_SECONDS=30
OPENAI_TEXT_MAX_ATTEMPTS=2
OPENAI_IMAGE_MODEL=gpt-image-2
OPENAI_IMAGE_SIZE=
OPENAI_IMAGE_QUALITY=
OPENAI_IMAGE_FORMAT=webp
OPENAI_IMAGE_TIMEOUT_SECONDS=60
IMAGE_MAX_RETRIES=3
IMAGE_MAX_CONCURRENT_JOBS=

S3_PROVIDER=minio
S3_ENDPOINT=http://minio:9000
S3_REGION=us-east-1
S3_BUCKET=foodai-images
S3_ACCESS_KEY=
S3_SECRET_KEY=
S3_USE_SSL=false
MEDIA_PUBLIC_BASE_URL=http://localhost:8080/media
S3_PRESIGNED_URL_TTL_SECONDS=300
MINIO_ROOT_USER=
MINIO_ROOT_PASSWORD=

NUTRITION_MIN_DAILY_CALORIES_FEMALE=1200
NUTRITION_MIN_DAILY_CALORIES_MALE=1500
NUTRITION_MAX_WEEKLY_WEIGHT_CHANGE_KG=
NUTRITION_ACTIVITY_FACTORS_JSON=
AI_CACHE_TTL_SECONDS=86400
AI_RATE_LIMIT_FREE_PER_DAY=
AI_RATE_LIMIT_PREMIUM_PER_DAY=
```

Production injects secrets from a secret manager/orchestrator, with distinct credentials per environment. `MINIO_ROOT_*` используются только bootstrap MinIO; backend/worker используют отдельные least-privilege `S3_*` keys. Rotate `OPENAI_API_KEY`, `JWT_SECRET`, database password and S3 keys independently. `JWT_SECRET=CHANGE_ME` or default database/S3 passwords are startup failures outside a disposable local test environment.

`NUTRITION_MAX_WEEKLY_WEIGHT_CHANGE_KG` пустым означает `1.0` кг в неделю. `NUTRITION_ACTIVITY_FACTORS_JSON` пустым означает `{"sedentary": 1.2, "light": 1.375, "moderate": 1.55, "high": 1.725, "very_high": 1.9}`; переданный JSON накладывается на эти значения, а неизвестный activity level, неположительный или нечисловой factor и битый JSON — startup failure.

Since Phase 2 the backend refuses to start with an empty `JWT_SECRET` in any environment, and rejects a sample value or a secret shorter than 32 characters (RFC 7518 HMAC-SHA256 minimum) whenever `APP_ENV` is not `development`/`test`. Startup errors name the setting only, never its value.

## Local services

`compose.yaml` содержит эти services (плюс one-shot `migrate`, который применяет Alembic до старта backend/worker):

| Service | Role | Persistent data | Healthcheck intent |
|---|---|---|---|
| `postgres` | authoritative relational database | named `postgres_data` volume | `pg_isready` |
| `redis` | cache, rate limit and Arq queue | optional configured persistence | `redis-cli ping` |
| `backend` | FastAPI HTTP API | no local state | `GET /health` |
| `worker` | Arq text/image jobs | no local state | worker startup/dependency readiness |
| `nginx` | public reverse proxy/media delivery | config only | backend upstream reachable |
| `minio` | S3-compatible private image bucket | named `minio_data` volume | MinIO readiness endpoint |
| `migrate` | one-shot `alembic upgrade head` перед backend/worker | none | контейнер завершается с кодом 0 |

MinIO образ тянется с `quay.io/minio/minio`: Docker Hub отвечает `401 UNAUTHORIZED` на анонимный pull `minio/minio`, поэтому `docker compose up` с Hub-образом падает до старта стека.

Nginx разрешает адрес backend через Docker DNS на каждый request, поэтому пересборка backend (`docker compose up -d --build backend`) не требует перезапуска nginx и не приводит к `502`.

### Публичный HTTPS без домена (sslip.io + Let's Encrypt)

`sslip.io` — публичный wildcard DNS: имя `193-32-179-108.sslip.io` резолвится в `193.32.179.108`, поэтому отдельный домен не нужен. Nginx публикует 80/443, HTTP отдаёт ACME-challenge и редиректит на HTTPS, а 8080 остаётся только на localhost для healthcheck.

```bash
certbot certonly --webroot -w ./certbot/www -d 193-32-179-108.sslip.io
docker compose restart nginx
```

Продление: `certbot renew` (webroot) и reload nginx. Для постоянного продукта нужен собственный домен и обычный TLS-контур; Cloudflare Quick Tunnel для российских клиентов не подходит — он блокируется без VPN.

### Локальный запуск на macOS

Все образы стека (`postgres:17-alpine`, `redis:7-alpine`, `nginx:1.27-alpine`, `python:3.12-slim`, `quay.io/minio/minio`) публикуются для `linux/arm64`, поэтому на Apple Silicon они запускаются нативно, без Rosetta и без `--platform`.

```bash
cp .env.example .env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # значение для JWT_SECRET
# заполнить JWT_SECRET, POSTGRES_PASSWORD, MINIO_ROOT_*, S3_*, REDIS_PASSWORD в .env
docker compose up -d --wait
docker compose exec backend alembic upgrade head
curl http://localhost:8080/health
```

Нужен работающий Docker Desktop (или другой Docker с поддержкой Compose v2). Порт публикует только nginx; при конфликте `8080` он меняется через `NGINX_PORT` в `.env`.

Backend-тесты запускаются без Docker и без secrets:

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/python -m pytest
```

Phase 1 supplies the runtime files as `compose.yaml` and `nginx/nginx.conf`. After copying `.env.example` to an untracked `.env` and filling its empty secrets, start the stack with `docker compose up --build`; `docker compose up -d --wait` is the non-interactive readiness check. Nginx is the sole published service at `http://localhost:8080` by default and proxies `GET /health` to the internal backend port `8000`; backend, Redis, PostgreSQL and MinIO ports remain internal. Do not treat a provider OpenAI call as health check. `/health` checks service readiness needed to serve API but does not spend AI quota.

## Test policy

pytest is required for backend. Tests must be deterministic, isolated and have no network dependency on OpenAI:

| Area | Required coverage |
|---|---|
| Auth | Argon2id hashes, JWT validation/expiry, refresh rotation/revocation, ownership |
| Nutrition | BMR/TDEE, floors, macro targets, ingredient sums, plan constraints |
| Recipe/plan | schema validation, canonicalization, allergies/exclusions, persistence, idempotency |
| AI text | structured output parse/repair, unknown ingredients, cache, quota and safe chat |
| Images | statuses, async enqueue, provider timeout, dedup, retry/primary logic, rate limits |
| Storage | upload keys, safe delivery URLs, cleanup and restore invariants |
| Entitlements | Free/Premium permissions and usage limits |
| API | error envelope, permission boundaries and rate-limit `429` |

`MockTextProvider`, `MockImageProvider` и `MockStorageProvider` are mandatory unit-test doubles. Unit tests **MUST NOT** call OpenAI Responses API or Image Generation API, even if a developer possesses a key. Local MinIO may be an opt-in integration-test dependency, but no production bucket may be accessed. CI runs a no-secrets configuration and fails if a test attempts external image generation.

## Logging and observability

Use structured JSON logs. Every HTTP request carries or receives `X-Request-ID`; all child worker events carry correlation/job id. Permitted fields:

```json
{
  "request_id": "uuid",
  "user_id": "uuid-or-null",
  "recipe_id": "uuid-or-null",
  "endpoint": "/api/v1/meal-plans/generate",
  "method": "POST",
  "status_code": 201,
  "duration_ms": 143,
  "ai_duration_ms": 850,
  "image_duration_ms": 0,
  "error_code": null
}
```

Never log password, password hash, access/refresh JWT, `OPENAI_API_KEY`, database URL with password, MinIO/S3 credentials, plaintext signed URL, full profile, full food restrictions or raw prompt/provider payload. `JsonFormatter` redacts sensitive keys and scrubs JWT-like / credential URL substrings from free-form messages. Error responses return `request_id`, but internal trace details remain server-side. Usage/cost audit belongs in `ai_text_usage`/`ai_image_usage`, not in sensitive logs.

Security headers on every HTTP response: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, `Cross-Origin-Resource-Policy`; API paths also get `Cache-Control: no-store`. Nginx mirrors the baseline headers at the edge.

## Healthchecks

| Check | What it proves |
|---|---|
| Compose `healthcheck` on postgres/redis/minio/backend/worker/nginx | container-level readiness |
| `GET /health` | Postgres + Redis reachable within 2s → `200 {"status":"ok"}` |
| `GET /health/deps` | per-dependency `ok`/`unavailable`/`skipped` (storage); 503 if postgres/redis fail |
| `scripts/healthcheck_all.sh` | all Compose services healthy + public health endpoints |
| `scripts/cache_smoke.sh` | Redis via deps + AI text cache fingerprint stability |

OpenAI / DeepSeek are **not** healthcheck dependencies.

## Database, migrations и backups

Alembic migration accompanies every schema change; do not use `create_all` as production migration. A migration must be tested against an empty DB and a prior schema snapshot. In local Compose apply them with `docker compose exec backend alembic upgrade head`; `alembic check` must report no drift between models and the applied schema.

Local backup/restore drill (Phase 15):

```bash
./scripts/backup.sh                 # → backups/<timestamp>/postgres.sql.gz + minio/
./scripts/restore_drill.sh          # isolated DB restore + integrity checks; drops drill DB
```

PostgreSQL uses logical `pg_dump`; MinIO is mirrored with `mc` into `backups/` (gitignored). Restore drill never overwrites the live database. Production should use encrypted dump/PITR and separate object-storage replication; `.env` secrets stay in secret-manager, never in dumps or git.

## Android build policy

Android (`android/`) — Kotlin/Compose, Hilt, Retrofit/OkHttp, Kotlinx Serialization. В BuildConfig попадает только `API_BASE_URL` (debug default `http://10.0.2.2:8080/api/v1/` для эмулятора; для телефона передайте `FOODAI_API_BASE_URL=https://<host>/api/v1/`). Override: `FOODAI_API_BASE_URL=... ./scripts/build_android.sh`. OpenAI, database, Redis, MinIO keys и JWT secret на устройство не попадают. Access/refresh хранятся в EncryptedSharedPreferences (Android Keystore master key); refresh выполняется single-flight через `TokenAuthenticator`. Онбординг Phase 9: 7 resumable screens + local draft + `calculate-target` preview + first plan generate.

```text
scripts/build_android.sh
scripts/install_android.sh
```

`build_android.sh` запускает `:app:assembleDebug` и печатает абсолютный путь к APK (`android/app/build/outputs/apk/debug/app-debug.apk`). `install_android.sh` проверяет `adb`, устройство и APK; без `adb` печатает инструкцию и выходит с ошибкой. Unit-тесты: `cd android && ./gradlew :app:testDebugUnitTest`. Каждый implementation phase после Android foundation обязан собрать APK.

## Production config review (Phase 16 + 17)

Before production: `APP_ENV=production`, non-placeholder `JWT_SECRET`, real `TERMS_URL`/`PRIVACY_URL`, strong DB/Redis/S3 secrets, TLS at the edge, and `ADMIN_EMAILS` limited to operators. See [privacy.md](privacy.md) and [analytics.md](analytics.md).

Перед публичным деплоем:

| Item | Development | Production |
|---|---|---|
| `APP_ENV` | `development` | `production` (rejects weak `JWT_SECRET`) |
| TLS | optional HTTP to public IP for phone debug | required on Nginx/CDN edge |
| `MEDIA_PUBLIC_BASE_URL` | `http://host:8080/media` | HTTPS CDN/domain |
| Secrets | local `.env` (gitignored) | secret manager; rotate JWT/MinIO/AI keys |
| OpenAI/DeepSeek | optional fallbacks | keys required for live AI; catalog fallback remains |
| Backups | `scripts/backup.sh` + restore drill | encrypted dump/PITR + object replication |
| Observability | JSON logs + request ids | ship logs to aggregator; alert on `/health` 503 |

Release gate document: [release-checklist.md](release-checklist.md). Smoke: `scripts/release_check.sh`. Phase reports: [phase-18-report.md](phase-18-report.md), [phase-19-report.md](phase-19-report.md).

## Phase gate и git workflow

1. Работать только в scope текущей фазы из [roadmap.md](roadmap.md).
2. Обновить documents/API/schema contract до или вместе с изменением.
3. Запустить compile, migrations и target tests; после появления Android — debug APK build.
4. Исправить все новые failures в scope фазы. Не переходить к следующей фазе, если current build broken.
5. Проверить `git diff`, отсутствие secrets/generated credentials и актуальность `.env.example`.
6. Создать отдельный descriptive git commit и report текущего status.

Phase 0 считается завершённой, когда все восемь docs согласованы и подтверждены человеком. Повторный Phase 0 review (re-validation) не откатывает уже реализованные фазы 1–4; после confirmation следующий шаг — Phase 5 по roadmap репозитория (см. маппинг в [roadmap.md](roadmap.md)). Cross-links: [architecture.md](architecture.md), [api.md](api.md), [database.md](database.md), [ai.md](ai.md), [storage.md](storage.md).
