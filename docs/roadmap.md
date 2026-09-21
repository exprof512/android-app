# Roadmap FoodAI: фазы 0–16

## Неподвижные правила поставки

- Phase 0 — только спецификация: никакого backend/Android кода, Compose, Docker Compose, API implementation или реальных AI/image вызовов **в рамках самой Phase 0**.
- **Новая implementation-фаза начинается только после явного human confirmation результата Phase 0 / текущего status.**
- После каждой фазы, начиная с Phase 1: обновить затронутые docs, выполнить compile и релевантные tests, исправить ошибки, сделать отдельный git commit, зафиксировать status. Если Android уже существует — собрать debug APK; переход к следующей фазе запрещён, пока текущая не собирается.
- Никакие ключи, пароли, JWT secrets или MinIO credentials не попадают в git/Android.

## Соответствие master-prompt и roadmap репозитория

Master DEVELOPMENT PROMPT нумерует фазы иначе (Docker → Auth → … → Image → Android). В этом репозитории каноническая нумерация — таблица ниже. Маппинг:

| Master prompt | Roadmap репозитория | Статус на момент Phase 0 re-validation |
|---|---|---|
| 0 Spec | **0** Product specification | готово |
| 1 Docker + health | часть **1** Backend foundation | готово (`compose.yaml`, Nginx, MinIO, `/health`) |
| 2 Backend foundation | **1** Backend foundation | готово |
| 3 Auth + Android login | **2** Auth (+ Android позже в **8**) | backend готово; Android отсутствует |
| 4 Profile + onboarding UI | **3** Profile/Nutrition (+ Android **9**) | backend готово |
| 5 Nutrition engine | **3** Profile and Nutrition Engine | готово |
| 6 OpenAI text | **5** Text AI integration | не начато |
| 7 Recipes + Android recipe | **4** Recipe domain (+ Android **10**) | backend готово |
| 8 Image generation | **7** Image pipeline and storage | не начато |
| 9 Daily meal plan | **6** Meal planning (+ Android **10**) | не начато |
| 10 Weekly + shopping | **6**/**11** | не начато |
| 11 Progress | **12** | не начато |
| 12 AI chat | **13** | не начато |
| 13 Monetization | **14** | не начато |
| 14 Security | **15** Hardening | не начато |
| 15 UX polish | **10–15** Android/UX | не начато |
| 16 Release candidate | **16** MVP RC | не начато |

После подтверждения Phase 0 **не** пересоздаём Docker/Auth/Profile: следующий implementation-шаг — **Phase 5 Text AI** по roadmap репозитория.

| Phase | Цель и scope | Exit criteria |
|---|---|---|
| **0 — Product specification** | Зафиксировать архитектуру, REST contract, data model, AI/image/storage policy, development workflow и план MVP. | Все восемь Phase 0 документов согласованы cross-links; **ожидание human confirmation перед Phase 1**. |
| **1 — Backend foundation** | Создать минимальный FastAPI project, config, Alembic foundation, dependency wiring, `/health`, базовый Docker/runtime layout без product features. | Backend compile/import; `/health` test; migration smoke test; docs актуальны. |
| **2 — Auth and session** | `users`, Argon2id, JWT access/refresh rotation, register/login/logout/`users/me`, ownership middleware. | Auth/JWT/refresh/revocation pytest green; no secret leaks; API contract verified. |
| **3 — Profile and Nutrition Engine** | Onboarding data persistence, goals, preferences/restrictions/pantry, BMR/TDEE/calorie/macro calculator и safety guardrails. | Nutrition unit tests и edge cases green; profile API tests; disclaimer surfaced in contract. |
| **4 — Recipe domain** | Ingredients catalog, structured recipe validation, canonicalization, nutrient/cost recalculation, recipe and favorite read APIs. | Recipe/ingredient/macro validation tests green; AI data cannot overwrite Nutrition Engine values. |
| **5 — Text AI integration** | Единственный OpenAI integration layer, Responses API structured outputs, TextAIService retry/repair, text usage/caching. | Provider mocked tests green; malformed AI output handled; no real API in automated tests. |
| **6 — Meal planning** | Генерация, daily constraints, persisted week/today, replace/complete и idempotency. | Meal-plan validation/integration tests green; reopening plan has no AI call; rate/quota tests green. |
| **7 — Image pipeline and storage** | `StorageProvider`, MinIO adapter, Arq worker, image providers, recipe-image metadata/status, dedup, Nginx-safe delivery. | Image/storage/dedup/retry tests use `MockImageProvider`; failure leaves recipe usable; no bytes in Postgres. |
| **8 — Android foundation** | Kotlin app shell, Compose navigation, DI/network/auth secure token storage, design tokens and error/loading primitives. | Android debug compile; unit tests; login/session manual smoke flow. |
| **9 — Android onboarding/profile** | Семь onboarding screens с product-copy из architecture, target preview, preferences/restrictions/pantry and first-plan loading handoff. | Debug APK; UI/navigation tests; API error/disclaimer states verified. |
| **10 — Android plan and recipe** | Home Today, Plan, recipe dish card, Coil thumbnail/full image states, replace/complete/favorite. | Debug APK; UI tests for pending/processing/ready/failed image states; plan data matches API. |
| **11 — Shopping** | Генерация, merged ingredients, pantry exclusion, completion и Shopping navigation. | Backend + Android tests; debug APK flow from plan to checked list. |
| **12 — Progress** | Weight entry, progress summary, daily nutrition balance and Progress screen. | Tests for timeline/ownership; debug APK flow; no medical/guaranteed claims. |
| **13 — Contextual chat** | Conversation/message API, bounded profile/plan context, safety handling, Chat UI entry from recipe. | Mocked AI tests; quota tests; debug APK chat/error states. |
| **14 — Entitlements abstraction** | Free/Premium limits, `require_premium()`, usage UX and `PaymentProvider` interface only. | Permission/rate/usage tests; Android paywall states; no real payment provider required. |
| **15 — Hardening and observability** | Structured logs, request IDs, security review, healthchecks, backups/restore drill, performance/cache checks. | Sensitive-log audit; all service healthchecks; tested Postgres/MinIO restore procedure. |
| **16 — MVP release candidate** | End-to-end regression, accessibility/localization review, production config review, APK build/install evidence. | Full backend suite green; Android debug/release-candidate build succeeds; APK path reported; release checklist accepted. |

## MVP на Phase 16

1. Регистрация, безопасная сессия и профиль питания.
2. Онбординг 1–7: «Твоя цель», «Расскажи о себе», «Как ты питаешься?», «Что ты любишь?», «Какой бюджет?», «Сколько времени готовишь?», «Что есть дома?» + loading «Создаём твой первый план...».
3. Серверный BMR/TDEE/target/macro calculation с safety floors и disclaimer.
4. Сохранённый личный недельный plan, Today, replacement и completion.
5. Полные recipe cards: ингредиенты/граммы, recalculated БЖУ/calories, стоимость, время и шаги.
6. Асинхронные AI-food images с placeholder/failure/retry и cached Coil delivery.
7. Список покупок с aggregation/merge и отмечанием покупок.
8. Weight progress и contextual AI chat.
9. Free/Premium entitlement и usage limits без реальной платёжной интеграции.
10. Повторяемый debug APK build и, при наличии `adb`, install workflow.

## Обязательная проверка фазы

До закрытия любой implementation phase owner подтверждает:

```text
[ ] scope фазы реализован без функционала следующей
[ ] backend compile/import и релевантный pytest green
[ ] migrations/schema проверены, если изменялись
[ ] Android debug APK собран, если Android существует
[ ] docs и .env.example синхронизированы
[ ] secrets/PII не попали в logs или git
[ ] отдельный commit создан; текущий status записан
```

Будущие команды сборки документированы, но не создаются в Phase 0: `scripts/build_android.sh` должен печатать путь к debug APK; `scripts/install_android.sh` должен использовать `adb` только если он доступен. Детали окружения: [development.md](development.md). Архитектурные gates: [architecture.md](architecture.md).
