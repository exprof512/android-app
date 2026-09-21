# REST API FoodAI

Base URL: `/api/v1`. Формат — JSON UTF-8; даты — ISO 8601 UTC; идентификаторы — UUID. API является единственным контрактом Android с backend: Android не обращается к OpenAI, Redis, PostgreSQL или MinIO.

## Общие правила

Защищённые endpoints требуют:

```http
Authorization: Bearer <access_jwt>
```

Успешный ответ использует соответствующий HTTP status и JSON body. Единый ответ ошибки:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Проверьте значения профиля.",
    "details": [{"field": "height_cm", "reason": "must_be_positive"}],
    "request_id": "c766b6ac-76b6-4b42-88a4-92f98d1eb1a7"
  }
}
```

Коды: `400` malformed request, `401` invalid/expired token, `403` ownership or entitlement denied, `404` absent resource, `409` conflicting/in-progress action, `422` domain/schema validation, `429` quota/rate limit, `503` temporarily unavailable dependency. Не возвращать provider-specific или secret details.

Все принадлежащие пользователю UUID проверяются по `user_id` до чтения/изменения. Для создающих AI endpoints поддерживается `Idempotency-Key`; повтор с тем же key возвращает исходный результат, а не расходует новую quota.

## Auth и current user

| Method / path | Auth | Назначение |
|---|---|---|
| `POST /auth/register` | нет | создать пользователя и начальный пустой profile |
| `POST /auth/login` | нет | выдать token pair |
| `POST /auth/refresh` | refresh token | rotation token pair |
| `POST /auth/logout` | access JWT | отозвать указанный refresh token/сессию |
| `GET /users/me` | access JWT | получить безопасное user/tier summary |

`POST /auth/register`:

```json
{
  "email": "anna@example.com",
  "password": "correct horse battery staple",
  "locale": "ru-RU",
  "accepted_terms_at": "2026-09-18T17:00:00Z"
}
```

`201` login/registration и `POST /auth/refresh`:

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {"id": "b664c3c6-b9d5-4e2b-aac7-20f7bb8e1453", "email": "anna@example.com", "tier": "free"}
}
```

Пароль никогда не возвращается и не логируется. Refresh token передаётся только в body; его исходное значение не сохраняется в PostgreSQL.

Phase 2 фиксирует поведение этих endpoints:

| Endpoint | Success | Request body |
|---|---|---|
| `POST /auth/register` | `201` token pair | `email`, `password` (8–128 символов), optional `locale` (default `ru-RU`) и `accepted_terms_at` |
| `POST /auth/login` | `200` token pair | `email`, `password` |
| `POST /auth/refresh` | `200` token pair | `refresh_token` |
| `POST /auth/logout` | `204` без body | `refresh_token`; требует access JWT владельца |
| `GET /users/me` | `200` user summary | — |

Email нормализуется в lowercase и уникален без учёта регистра. Access JWT живёт `JWT_ACCESS_TTL_SECONDS` секунд (`expires_in`); от refresh token в `refresh_tokens` хранится только SHA-256 hash.

Refresh token одноразовый: `POST /auth/refresh` отзывает предъявленный token, выдаёт новый в той же token family и связывает записи через `replaced_by_id`. Повторное предъявление уже отозванного token считается утечкой: вся family отзывается, и все её token'ы перестают работать. `POST /auth/logout` отзывает только указанную сессию и идемпотентен для уже отозванного token.

Коды ошибок auth: `401 invalid_credentials` (неверный email или пароль — ответ одинаков, чтобы не раскрывать существование аккаунта), `401 invalid_token` (отсутствующий, истёкший, подделанный, не того типа или отозванный token; ответ содержит `WWW-Authenticate: Bearer`), `403 account_disabled`, `403 ownership_denied` (token принадлежит другому user), `409 email_already_registered`, `422 validation_error`.

`tier` в Phase 2 всегда `free`: реальный tier вычисляет `EntitlementsService` по `subscriptions` в Phase 14. Пустой `user_profiles` создаётся вместе с profile schema в Phase 3, поэтому Phase 2 регистрирует только `users` и сессию.

## Профиль и расчёт цели

| Method / path | Назначение |
|---|---|
| `GET /profile` | анкета, предпочтения, restrictions и active goal |
| `PUT /profile` | атомарно обновить editable profile/food preferences/restrictions |
| `POST /profile/calculate-target` | preview, рассчитанный только `NutritionEngine` |

Пример `PUT /profile`:

```json
{
  "sex": "female",
  "age_years": 31,
  "height_cm": 168,
  "current_weight_kg": 72.4,
  "target_weight_kg": 64,
  "activity_level": "moderate",
  "goal_type": "lose_weight",
  "desired_weekly_change_kg": 0.4,
  "meals_per_day": 4,
  "daily_calorie_mode": "deficit",
  "daily_calorie_value": 400,
  "grocery_budget_weekly": 6500,
  "currency": "RUB",
  "max_cook_time_minutes": 35,
  "household_size": 2,
  "liked_foods": ["гречка", "лосось"],
  "disliked_foods": ["сельдерей"],
  "excluded_foods": ["свинина"],
  "allergies": ["арахис"],
  "available_products": [{"name": "яйца", "quantity": 10, "unit": "piece"}]
}
```

`POST /profile/calculate-target` принимает те же антропометрические/goal поля (без сохранения) и возвращает:

```json
{
  "bmr_kcal": 1424,
  "tdee_kcal": 2207,
  "recommended_calorie_target_kcal": 1807,
  "applied_safety_floor_kcal": 1200,
  "macro_targets_g": {"protein": 115, "fat": 60, "carbohydrate": 195},
  "warnings": ["Расчёты приблизительны и не заменяют врача или диетолога."]
}
```

Backend отклоняет экстремальный target вместо того, чтобы передавать его AI.

## Meal plans и plan items

| Method / path | Назначение |
|---|---|
| `POST /meal-plans/generate` | создать персональный plan и рецепты; image jobs только ставятся в очередь |
| `GET /meal-plans/today?date=YYYY-MM-DD` | active plan на дату |
| `GET /meal-plans/week?start_date=YYYY-MM-DD` | семь дней active plan |
| `POST /meal-plans/{meal_plan_id}/regenerate` | заменить scope плана после entitlement/quota check |
| `POST /meal-plan-items/{item_id}/replace` | подобрать допустимую замену одному meal slot |
| `POST /meal-plan-items/{item_id}/complete` | отметить приготовление/съедение |

`POST /meal-plans/generate`:

```json
{
  "start_date": "2026-09-21",
  "days": 7,
  "regenerate_scope": "all",
  "notes": "Быстрые ужины в будни"
}
```

`201` возвращает сохранённый `MealPlan`; HTTP request не ждёт изображения:

```json
{
  "id": "2c36f0a7-8bbd-4887-b8f8-b5601410ddfb",
  "start_date": "2026-09-21",
  "end_date": "2026-09-27",
  "status": "ready",
  "daily_targets": {"calories_kcal": 1807, "protein_g": 115, "fat_g": 60, "carbohydrate_g": 195},
  "items": [{
    "id": "3fb40a5f-4d6d-48fd-aedd-fca3e18f62d2",
    "date": "2026-09-21",
    "meal_type": "breakfast",
    "recipe": {"id": "a86cebd6-e8c3-463d-92ea-a6fced7b9dcb", "name": "Овсянка с ягодами", "calories_kcal": 412, "image": {"status": "pending", "thumbnail_url": null}}
  }],
  "warnings": []
}
```

`regenerate_scope` — `all`, `day` или `item`; запрос с `day` содержит `date`, с `item` используется endpoint replace. Все результаты после replacement снова проходят `NutritionEngine`.

## Recipes и изображения

| Method / path | Назначение |
|---|---|
| `GET /recipes/{recipe_id}` | полная dish card, доступная текущему user по plan/ownership |
| `POST /recipes/{recipe_id}/favorite` | добавить favorite |
| `DELETE /recipes/{recipe_id}/favorite` | убрать favorite |
| `GET /recipes/{recipe_id}/image` | primary image status для быстрого UI polling/refetch |
| `GET /recipes/{recipe_id}/images` | все версии image history, latest primary first |
| `POST /recipes/{recipe_id}/image/regenerate` | создать новый image job после rate/quota check |
| `POST /images/{image_id}/retry` | повторить failed image job, если разрешено |

Полная карточка содержит `name`, nutrition от backend, `ingredients` с `grams`, estimated `cost`, `cook_time_minutes`, ordered `steps` и `image`. Не принимать nutrition, имя или image URL от Android как authoritative update.

Контракт image endpoint:

```json
{
  "id": "049ed0db-3f13-4b1e-a54b-39036c09bf40",
  "recipe_id": "a86cebd6-e8c3-463d-92ea-a6fced7b9dcb",
  "status": "ready",
  "url": "https://api.foodai.example/media/recipes/a86.../original.webp",
  "thumbnail_url": "https://api.foodai.example/media/recipes/a86.../thumbnail.webp",
  "width": 1536,
  "height": 1024,
  "format": "webp",
  "updated_at": "2026-09-18T17:03:20Z"
}
```

Допустимые `status`: `pending`, `processing`, `ready`, `failed`. Для `failed` `url` и `thumbnail_url` — `null`; response может содержать нейтральный `retry_allowed`, но не внутренний provider error. UI: placeholder/shimmer → «Готовим фото блюда...» → image; failure: «Изображение пока недоступно.»

`POST /recipes/{recipe_id}/image/regenerate` лимитируется на user и recipe (начальная policy: максимум 2 accepted requests/recipe/24h и учитывает tier); ответ `202` содержит pending image contract. `POST /images/{id}/retry` допускается только для `failed`, c server-side maximum retry count и теми же entitlement/rate limit правилами. Duplicate concurrent jobs возвращают `409 image_generation_in_progress`.

URL всегда принадлежит FoodAI CDN/Nginx/backend; raw MinIO endpoint и storage credentials никогда не возвращаются.

## Shopping

| Method / path | Назначение |
|---|---|
| `POST /shopping-lists/generate` | построить список из meal plan/date range и pantry |
| `GET /shopping-lists/current?meal_plan_id=` | current list пользователя |
| `GET /shopping-lists/{list_id}` | список с items |
| `POST /shopping-list-items/{item_id}/complete` | отметить куплено/не куплено |

`POST /shopping-lists/generate` принимает `meal_plan_id`, optional `from_date`/`to_date`, `exclude_available_products=true`. Server агрегирует одинаковые normalized ingredients и единицы; не вызывает AI.

## Progress

| Method / path | Назначение |
|---|---|
| `POST /weight-entries` | сохранить факт веса |
| `GET /weight-entries?from=&to=` | timeline weight |
| `GET /progress/summary` | goal progress, balance и trend без medical claim |
| `POST /nutrition-logs` | записать подтверждённый nutrition факт, если feature доступен |
| `GET /nutrition-logs?date=` | дневной nutrition log |

`POST /weight-entries`:

```json
{"measured_at": "2026-09-18T07:30:00Z", "weight_kg": 72.1, "note": "утром"}
```

## AI chat

| Method / path | Назначение |
|---|---|
| `POST /ai/chat/conversations` | создать/получить current conversation |
| `GET /ai/chat/conversations/{conversation_id}` | paginated history |
| `POST /ai/chat/conversations/{conversation_id}/messages` | отправить запрос к contextual AI |

Пример:

```json
{"content": "Чем заменить курицу на ужин без молочных продуктов?"}
```

Ответ содержит assistant message, optional structured `suggested_actions` (например `replace_meal_item`) и warnings. Он не исполняет mutation автоматически: Android запрашивает отдельный authenticated endpoint. Chat requests покрыты free/premium quota и сохраняют `ai_text_usage`.

## Health

`GET /health` не требует auth и возвращает ровно `200 {"status":"ok"}` только когда API готово обслуживать request. В Phase 1 endpoint также используется Docker/Nginx healthcheck и доступен через public Nginx path `http://localhost:8080/health` в local Compose; provider OpenAI не вызывается healthcheck-ом.

Полный data contract: [database.md](database.md). Потоки и security: [architecture.md](architecture.md). Image semantics: [image-generation.md](image-generation.md).
