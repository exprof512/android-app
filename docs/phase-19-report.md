# PHASE 19 REPORT

## Status
**PARTIAL**

Daily-loop backend + Android landed and compile/tests for the new surface are green. Physical phone smoke is **NOT RUN** in this environment (install APK on device to close).

## Daily Loop
Today is the hub: date, authoritative `day_progress`, next meal, meal timeline, quick actions (complete / skip / replace / add food / plan / shopping), water, weight check-in, suggestions, estimated daily cost.

## Today
- Uses `GET /meal-plans/today` → `day_progress` (consumed/target/remaining kcal + macros).
- Next meal from `next_meal_item_id` / `next_meal_type`.
- Distinct loading / empty / error / offline-cache states.
- Android no longer invents remaining macros when `day_progress` is present.

## Week Plan
- `week_summary.days[]` with per-day status, kcal, protein, completion, cost.
- Shared `SelectedDateStore` with Today.
- Missing day CTA without silent generation on GET.

## Nutrition
- Authoritative day totals: completed items ∪ nutrition_logs.
- Complete meal upserts `nutrition_logs` (`source=meal_plan_item`) idempotently.
- Skip does not create consumption.

## Meal Completion
- `POST /meal-plan-items/{id}/complete` + nutrition log upsert/delete.
- UI flips only after 2xx; emits `PlanChanged` / `NutritionLogChanged`.

## Replacement
- Reason chips include dislike / expensive / long / no ingredients / more protein / less calories / other.
- Idempotency-Key retained; shopping marked stale after replace.

## Shopping
- Estimated total + currency; item `category`; `stale` + rebuild CTA; clear-completed.
- Pantry exclude via existing generate flag.

## Water
- New `water_entries` + `GET/POST /water`, `DELETE /water/last`.
- Today +250/+500 + undo; `WaterChanged` bus event.

## Weight
- Inline Today check-in via existing `/weight-entries`.
- Progress / Profile refresh via `WeightChanged`.

## Progress
- `GET /progress/summary?period=7|30|90` with sparse `series`.
- Android period selector wired.

## Notifications
- Local AlarmManager scheduler; master + meal/water/weight/weekly prefs; POST_NOTIFICATIONS.
- No FCM.

## Favorites
- `GET /recipes/favorites`; toggle remains POST/DELETE; Profile entry.

## Search
- `GET /recipes/search` (ILIKE + filters); Profile entry UI.

## Offline
- In-memory last-success cache on Today with «Нет соединения» + retry.
- Mutations still require server confirmation.

## Analytics
- Phase 19 event names allowlisted server-side; wired from Today/Week/Shopping/Recipe/Settings (bounded props only).

## Backend
- Migration `0014_phase19_daily_loop` (water + shopping stale/fingerprint columns).
- meal_plans day_progress/week_summary; skip; complete↔log; shopping cost/category/stale; water module; progress series; favorites list + search.

## Database
- `water_entries`
- `shopping_lists.stale`, `shopping_lists.plan_fingerprint`

## Android
- Today redesign, Week/Shopping/Progress updates, notifications package, water repository, favorites/search screens, onboarding «Обновить мой план?» dialog.

## Tests
```text
docker compose run --rm --no-deps -v "$PWD/backend:/app" backend \
  bash -lc "pip install -e '.[dev]' -q && python -m pytest tests/test_phase19_daily_loop.py -q"
# RESULT: 6 passed

cd android && ./gradlew :app:testDebugUnitTest --tests 'com.foodai.app.core.network.Phase19ModelsTest'
# RESULT: BUILD SUCCESSFUL / tests passed

./scripts/build_android.sh
# RESULT: BUILD SUCCESSFUL
```

## APK
`/root/app-android/android-app/android/app/build/outputs/apk/debug/app-debug.apk`  
`API_BASE_URL=http://193.32.179.108:8080/api/v1/`

## Physical Device
**NOT RUN** — install the APK above and run the Phase 19 smoke checklist before marking PASS.

## Known Limitations
- Notification icon uses launcher drawable (soft appearance).
- Exact-alarm permission UX not polished (inexact repeating alarms).
- Steps remain device-local only.
- Offline is memory snapshot only (no Room disk cache).
- Imperial units still not applied on every screen (Phase 18 leftover).

## Commit
`b8a54a8` — `feat(phase-19): beta UX and daily loop`
