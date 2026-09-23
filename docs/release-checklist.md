# FoodAI MVP release checklist (Phase 16 + Phase 17)

Использовать перед объявлением MVP release candidate / beta. Отмечать только после проверки на **физическом телефоне** (эмулятор не используется).

## Backend / infra

- [x] `docker compose ps` — все сервисы `healthy` (postgres, redis, minio, backend, worker, nginx)
- [x] `GET /health` → `{"status":"ok"}` и `X-Request-ID`
- [x] `GET /health/deps` → postgres/redis/storage без секретов
- [x] Alembic head применён (`0013_nutrition_diary_policy`)
- [x] Full backend pytest suite green (incl. `test_phase17_productization`)
- [x] Postgres restore drill (isolated DB) passed
- [x] Structured logs не содержат password/JWT/API keys (audit + redaction tests)
- [x] Security headers на API/Nginx
- [ ] Production `.env`: `APP_ENV=production`, сильный `JWT_SECRET` (≥32), не placeholder
- [ ] Production `TERMS_URL` / `PRIVACY_URL` — реальные URL (не example.com)
- [ ] Production `MEDIA_PUBLIC_BASE_URL` и TLS на публичном edge
- [ ] OpenAI/DeepSeek keys только в secret store / Compose env, не в git/APK
- [ ] `ADMIN_EMAILS` bootstrap только для trusted operators

## Android

- [x] Debug APK собирается (`scripts/build_android.sh`)
- [x] `API_BASE_URL` указывает на публичный host (не `10.0.2.2`)
- [x] Secrets не в BuildConfig (только `API_BASE_URL`)
- [x] Tokens в EncryptedSharedPreferences
- [ ] Установка на физический телефон и smoke:
  - [ ] Register / Login
  - [ ] Онбординг 1–7 + disclaimer
  - [ ] Генерация плана (Today/Plan)
  - [ ] Recipe card + Ask AI
  - [ ] Shopping complete toggle
  - [ ] Progress weight entry
  - [ ] Profile Free badge / edit profile / logout
  - [ ] Account: verification state, sessions, export, delete confirm
  - [ ] Forgot / reset password
  - [ ] Today nutrition diary (manual snack log)
  - [ ] Legal links (Terms / Privacy)

## Product MVP scope (roadmap)

1. Регистрация и сессия
2. Онбординг 1–7 + first plan
3. Nutrition Engine + disclaimer
4. Недельный plan, Today, replace/complete
5. Recipe cards (БЖУ/стоимость/шаги/изображения)
6. Async AI images с placeholder/failure
7. Shopping list
8. Progress + contextual chat
9. Free/Premium limits без реальной оплаты
10. Повторяемый debug APK build

## Localization / a11y (MVP bar)

- UI copy преимущественно на русском; bottom nav labels как в макете (Home/Plan/…)
- Ключевые иконки навигации имеют `contentDescription`
- RTL: `supportsRtl=true` в манифесте; полный RTL-pass — follow-up
- Контраст primary Forest на белом — соответствует макету

## Sign-off

| Role | Status |
|---|---|
| Engineering | Phase 16 RC prepared |
| Product / human | **ожидает подтверждения** после phone smoke |

APK path после сборки: `android/app/build/outputs/apk/debug/app-debug.apk` (абсолютный путь печатает `scripts/build_android.sh`).
