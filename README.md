# FoodAI

Android + AI продукт FoodAI. Спецификация утверждена в Phase 0; backend реализуется по [фазам 0–16](docs/roadmap.md).

- [Архитектура](docs/architecture.md)
- [REST API](docs/api.md)
- [Модель данных](docs/database.md)
- [AI](docs/ai.md) и [генерация изображений](docs/image-generation.md)
- [Хранилище](docs/storage.md)
- [Разработка и roadmap](docs/development.md), [фазы 0–16](docs/roadmap.md)

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
| 10 — Android plan and recipe | не начато ← **следующий шаг** |
| 11–16 | не начаты |

Маппинг master-prompt фаз → roadmap: [docs/roadmap.md](docs/roadmap.md).

## Локальный запуск

```bash
cp .env.example .env   # заполнить пустые secrets
docker compose up -d --wait
docker compose exec backend alembic upgrade head
curl http://localhost:8080/health
```

Тесты backend: `pytest` в `backend/` — без OpenAI/Docker/secrets.  
Android debug APK: `./scripts/build_android.sh` (нужны JDK 17 и `ANDROID_HOME`).
