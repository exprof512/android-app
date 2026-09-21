# FoodAI

Android + AI продукт FoodAI. Спецификация утверждена в Phase 0; backend реализуется по [фазам 0–16](docs/roadmap.md).

- [Архитектура](docs/architecture.md)
- [REST API](docs/api.md)
- [Модель данных](docs/database.md)
- [AI](docs/ai.md) и [генерация изображений](docs/image-generation.md)
- [Хранилище](docs/storage.md)
- [Разработка и roadmap](docs/development.md), [фазы 0–16](docs/roadmap.md)

## Статус

| Phase | Состояние |
|---|---|
| 0 — Product specification | готово |
| 1 — Backend foundation | готово: FastAPI, config, Alembic, `/health`, Compose/Nginx runtime |
| 2 — Auth and session | готово: `users`/`refresh_tokens`, Argon2id, JWT access/refresh rotation, `/auth/*`, `/users/me`, ownership guard |
| 3 — Profile and Nutrition Engine | готово: анкета, цели, предпочтения/ограничения/pantry, `GET`/`PUT /profile`, `POST /profile/calculate-target`, BMR/TDEE/macros с safety floors |
| 4–16 | не начаты |

## Локальный запуск

```bash
cp .env.example .env   # заполнить пустые secrets
docker compose up -d --wait
docker compose exec backend alembic upgrade head
curl http://localhost:8080/health
```

Тесты: `pytest` в `backend/` — без обращений к OpenAI, без Docker и без secrets.
