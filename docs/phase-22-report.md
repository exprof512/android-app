# Phase 22 Report — UX/UI 2.0 + Smart Plan Continuity

**Status: PARTIAL** — core backend/Android fixes landed; physical-device smoke must be run by the user on a phone.

## UX / navigation

| Before | After |
|---|---|
| Сегодня · План · Прогресс · Профиль | Сегодня · План · **Дневник** · Прогресс · Профиль |
| FAB → Chat | FAB → **Add Food** sheet |
| Diary jammed into Today | Dedicated `DiaryScreen` + date switching |
| Large outline CTAs on Today | Compact text actions; add via FAB |

## Plan continuity

- `MealPlanService.ensure_current_day_plan()` — idempotent generate when `GET /meal-plans/today` has no covering plan.
- `_maybe_prepare_next_week()` when `days_remaining <= 1`.
- Week endpoint also ensures a plan exists.

## Diversity

- Catalog fallback rotates **7 distinct** breakfast/lunch/dinner/snack templates by day offset (`fallback_plans.py`).
- `MealPlanEngine.validate_plan` rejects `same_meal_repetition` / `daily_variety` / `same_recipe_repetition` → repair via catalog fallback.

## Image recognition — root cause

**Confirmed:** `nginx/nginx.conf` had `client_max_body_size 1m`. Real phone JPEGs (often 2–8 MB) got **HTTP 413 from nginx** before FastAPI/OpenAI. Android showed generic «Не удалось распознать фото».

**Reproduction:** `curl` 1.5 MB JPEG → 413 HTML from nginx; after `client_max_body_size 8m` → request reaches API (401 without auth).

**Fixes:**
1. Nginx limit → **8m**
2. Android `downscaleForUpload` (~900 KB JPEG) before multipart
3. Clearer 413 / `image_too_large` UI message

## Tests

- `tests/test_phase22_plan_continuity.py` — auto today + fallback diversity
- Existing `tests/test_phase22_nutrition_invariants.py`

## Physical device smoke

**Not executed in this environment.** Install APK and verify checklist in the phase prompt (especially photo + new day plan).

## Known limitations

- Next-week generation is synchronous on Today/Week fetch (not Arq job yet) — may add latency near week end.
- Settings theme/units audit not fully completed this pass.
- Progress chart polish deferred.
- Full UI instrumentation suite not added.

## Commit

`feat(phase-22): ux ui and smart plan continuity`
