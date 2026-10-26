# FoodAI

Android + AI продукт FoodAI. Спецификация утверждена в Phase 0; backend реализуется по [фазам 0–16](docs/roadmap.md).

- [Архитектура](docs/architecture.md)
- [REST API](docs/api.md)
- [Модель данных](docs/database.md)
- [AI](docs/ai.md) и [генерация изображений](docs/image-generation.md)
- [Хранилище](docs/storage.md)
- [Разработка и roadmap](docs/development.md), [фазы 0–16](docs/roadmap.md)
- [Release checklist](docs/release-checklist.md)

## Статус

| Phase (roadmap репозитория) | Состояние |
|---|---|
| 0 — Product specification | готово (re-validated против master prompt; ждёт confirmation) |
| 1 — Backend foundation | готово: FastAPI, config, Alembic, `/health`, Compose/Nginx/MinIO/worker runtime |
| 2 — Auth and session | готово: `users`/`refresh_tokens`, Argon2id, JWT access/refresh rotation, `/auth/*`, `/users/me`, ownership guard |
| 3 — Profile and Nutrition Engine | готово: анкета, цели, предпочтения/ограничения/pantry, `GET`/`PUT /profile`, `POST /profile/calculate-target`, BMR/TDEE/macros с safety floors |
| 4 — Recipe domain | готово: каталог ингредиентов, `RecipeEngine` (валидация, канонизация, единицы → граммы, fingerprint/dedup), пересчёт БЖУ и стоимости, `GET /recipes/{id}` и favorites |
| 5 — Text AI | готово: `integrations/openai`, `TextAIService`, Structured Outputs, cache, `ai_text_usage`, `MockTextProvider` tests |
| 6 — Meal planning | готово: generate/today/week/replace/complete, MealPlanEngine constraints, idempotent reuse |
| 7 — Image pipeline | готово: StorageProvider/MinIO, RecipeImage, Arq worker, Mock/OpenAI providers, media URLs |
| 8 — Android foundation | готово: Kotlin/Compose shell, Hilt, Retrofit, EncryptedSharedPreferences, login/register, bottom nav |
| 9 — Android onboarding/profile | готово: 7 экранов, draft, calculate-target preview, first-plan loading, Profile tab |
| 10 — Android plan and recipe | готово: Today/Plan, dish card, Coil image states, replace/complete/favorite |
| 11 — Shopping | готово: generate/current/complete, pantry exclusion, Android Shopping tab |
| 12 — Progress | готово: weight entries, summary, daily balance, Android Progress tab |
| 13 — Contextual chat | готово: conversations/messages, safety refusal, Ask AI from recipe |
| 14 — Entitlements abstraction | готово: subscriptions/usage_limits, Free/Premium limits, PaymentProvider stub, Android Free badge |
| 15 — Hardening and observability | готово: log redaction, security headers, /health/deps, backup+restore drill scripts, cache smoke |
| 16 — MVP release candidate | готово (RC): pytest green, `0.1.0-rc1`, [release-checklist.md](docs/release-checklist.md); phone smoke ожидает подтверждения |

Маппинг master-prompt фаз → roadmap: [docs/roadmap.md](docs/roadmap.md).

## Локальный запуск

```bash
cp .env.example .env   # заполнить secrets: JWT_SECRET, POSTGRES_PASSWORD, MINIO_ROOT_*, S3_*, REDIS_PASSWORD
docker compose up -d --wait   # сервис migrate применит миграции автоматически
curl http://localhost:8080/health
```

Тесты backend: `pytest` в `backend/` — без OpenAI/Docker/secrets.  
Android debug APK: `./scripts/build_android.sh` (нужны JDK 17 и `ANDROID_HOME`).
