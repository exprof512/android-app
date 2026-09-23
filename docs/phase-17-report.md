# PHASE 17 REPORT — Productization & Beta Foundation

**Date:** 2026-09-23  
**Commit message:** `feat(phase-17): productization and beta foundation`  
**Prerequisite (separate):** `db294bc` — `fix(android): profile edit, tip banners, shopping icons, pedometer`

## Delivered

### Backend
- Migrations `0011_account_lifecycle`, `0012_product_events`, `0013_nutrition_diary_policy`
- Soft email verify + forgot/reset (`MockEmailProvider`); sessions list/revoke; delete/export
- Consent versions + `TERMS_URL`/`PRIVACY_URL` (production validation)
- `POST /events` product analytics + Redis/memory rate limit
- Admin AI aggregates (`/admin/ai/*`) + `users.role` / `ADMIN_EMAILS`
- `nutrition_logs` CRUD; Progress/Today union with completed meals
- Replace: `replace_reason`, `Idempotency-Key`, richer constraint context
- `NUTRITION_POLICY_VERSION` snapshotted on goals/meal_plans
- `ingredients.source_version` (`seed-v1` for seed rows)

### Android
- Account screen: verification, sessions, export, delete (local clear only after 204)
- Auth: forgot / reset password
- `AnalyticsTracker` → best-effort `/events`
- Today: nutrition diary section + manual snack log
- Legal URLs from `/users/me`

### Docs
- Updated: roadmap, api, database, architecture, ai, development, release-checklist
- Added: `docs/privacy.md`, `docs/analytics.md`
- `.env.example` Phase 17 keys

## Validation

| Check | Result |
|---|---|
| `GET /health` | `{"status":"ok"}` |
| `alembic check` | known pre-existing reflection noise only (DESC indexes / JSON variants / subscriptions unique); Phase 17 unique/smallint drift cleared |
| `:app:testDebugUnitTest` | **SUCCESS** (`TEST_EXIT:0`) |
| `scripts/build_android.sh` | **SUCCESS** |
| Debug APK | `/root/app-android/android-app/android/app/build/outputs/apk/debug/app-debug.apk` |
| `API_BASE_URL` | `http://193.32.179.108:8080/api/v1/` |

### Alembic check note
`alembic check` still reports pre-existing autogenerate noise (DESC index expressions on usage/image/meal_plans tables, JSON type variants, subscriptions unique index reflection). Phase 17 schema/models are aligned; remaining drift is historical reflection mismatch, not unapplied Phase 17 migrations.

## Phone smoke (human — physical device only)

- [ ] Install debug APK
- [ ] Register / Login; Account verification banner
- [ ] Forgot / reset password
- [ ] Sessions list / revoke
- [ ] Export; Delete account confirm (session cleared only on success)
- [ ] Legal Terms / Privacy links
- [ ] Today diary + add snack
- [ ] Replace meal still works

## Out of scope (as planned)
Payments, FCM, social, camera, wearables, real SMTP, admin web UI, Firebase/Amplitude, Kubernetes.
