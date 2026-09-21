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
| 6 — Meal planning | не начато ← **следующий шаг** |
| 7–16 | не начаты |

Android-модуля (`android/`) пока нет. Маппинг master-prompt фаз → roadmap: [docs/roadmap.md](docs/roadmap.md).

## Локальный запуск

```bash
cp .env.example .env   # заполнить пустые secrets
docker compose up -d --wait
docker compose exec backend alembic upgrade head
curl http://localhost:8080/health
```

Тесты: `pytest` в `backend/` — без обращений к OpenAI, без Docker и без secrets. Все образы стека собраны и для `linux/arm64`, поэтому на Apple Silicon запускаются нативно; подробности — в [development.md](docs/development.md#локальный-запуск-на-macos).
