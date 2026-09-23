# PHASE 18 REPORT

## Status
**PARTIAL**

Core consistency work landed (audit, delete/export contracts, SSOT bus, Today/Week/Shopping sync, theme modes, beta quotas). Physical phone smoke and some Definition-of-Done items remain open.

## Root Causes Found
See [phase-18-audit.md](phase-18-audit.md).

Highlights:
- Delete `422`: DELETE-with-body unreliable; fixed via `POST /users/me/delete`.
- Export “false success”: backend JSON was real; Android never saved/shared.
- Today ≠ Week: separate ViewModels, no invalidation after generate.
- Fake settings: theme/metric prefs unused; promotions promised store deals without data.

## Account
- Added `POST /users/me/delete` with `confirmation=DELETE`.
- Legacy `DELETE /users/me` accepts body or `X-Confirm-Delete`.
- Android switched to POST; clears session only after 2xx.
- Tests: `test_delete_current_user_success`, unauthenticated, invalid confirmation, header fallback.

## Export
- Backend validates `exported_at`; `Content-Disposition` attachment.
- Android validates payload + share Intent (`ACTION_SEND`).
- Test: `test_export_contains_user_owned_data` with profile seed; secrets excluded.

## State Synchronization
- `AppStateBus` + typed `DomainEvent`.
- `MealPlanRepository` / `ProfileRepository` / `ProgressRepository` emit events.
- `SelectedDateStore` shared across Today/Week.
- Documented in [state-management.md](state-management.md).

## Today
- Uses selected date; listens for Plan/Weight/Profile/Nutrition events.
- Empty copy: “План на этот день отсутствует.”
- Manual refresh retained as secondary.

## Week Plan
- Still uses covering week API (full window).
- Day chips with planned/missing status + week summary (avg kcal, completed, cost).
- Shares selected date with Today; refreshes on `PlanChanged`.

## Shopping
- Rebuild updates list in VM; listens for `PlanChanged` / `ShoppingChanged`.

## Onboarding / Rate Limits
- Free beta defaults raised: plan 10/day, replace 15/day, chat 40/day.
- Replace sends `Idempotency-Key`.
- Full 429 UX (remaining quota surface) still thin — PARTIAL.

## Settings
- Theme: System / Light / Dark via `ThemePreferences` → `FoodAiTheme`.
- Metric toggle persists; presentation helpers in `UnitPreferences` (wire-through to all screens incomplete → PARTIAL).
- Promotions onboarding copy made honest (no fake store deals).

## Theme
Implemented System/Light/Dark.

## Units
Canonical kg on backend; Android conversion helpers added; not every screen reformatted yet.

## Weight Goal
Engine max weekly change aligned to **2.0 kg** (matches DB `WEEKLY_CHANGE_KG_MAX`).

## Promotions
No promotion data source — UI no longer claims store discounts.

## Additional Features
Landed: selected-day sync, week summary, event-driven completion/replace refresh, remaining calories already on Today, improved empty copy.
Not fully done: Quick Add menu variants, pull-to-refresh polish, last-updated labels everywhere, favorites polish, local notification scheduler.

## Backend Changes
- `POST /users/me/delete`, DELETE header fallback, export headers/validation.
- Entitlement Free defaults raised.
- Nutrition max weekly default 2.0 kg.

## Database Changes
None (no new migration in Phase 18 so far).

## Android Changes
- Sync bus, SelectedDateStore, repository SSOT.
- Account delete/export UX.
- Theme preferences, settings UI, week summary, shopping/progress listeners.

## Tests
```text
docker compose run --rm --no-deps -v "$PWD/backend:/app" backend \
  bash -lc "pip install -e '.[dev]' -q && python -m pytest tests/test_phase18_account.py tests/test_phase17_productization.py -q"
# RESULT: 12 passed

./scripts/build_android.sh
# RESULT: BUILD SUCCESSFUL
# APK: android/app/build/outputs/apk/debug/app-debug.apk
```

Full suite / Android unit tests / alembic check / ownership matrix: **not fully re-run in this cut** — treat as follow-up before marking COMPLETE.

## APK
`/root/app-android/android-app/android/app/build/outputs/apk/debug/app-debug.apk`  
`API_BASE_URL=http://193.32.179.108:8080/api/v1/`

## Physical Device
**FAIL / NOT RUN** — phone smoke checklist from the Phase 18 prompt awaits human install.

## Known Limitations
- Imperial formatting not applied on every screen yet.
- Diary macros still not fully merged into Today calorie ring.
- No FCM; notification prefs remain local-only (explicit copy).
- Alembic historical reflection noise from Phase 17 may still appear on `alembic check`.

## Commit
Pending at report write time — see git log for `refactor(phase-18): core consistency and weekly planning`.
