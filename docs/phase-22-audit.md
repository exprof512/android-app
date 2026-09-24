# Phase 22 Audit — UX/UI 2.0 + Smart Plan Continuity

> Extends prior nutrition-consistency audit. Focus: navigation, diary split, plan continuity, week diversity, photo recognition.

## Navigation (current)

| Tab | Route | Screen |
|---|---|---|
| Сегодня | `Routes.Home` | `TodayRoute` / `PlanScreens.kt` |
| План | `Routes.Plan` | `WeekRoute` |
| Прогресс | `Routes.Progress` | `ProgressRoute` |
| Профиль | `Routes.Profile` | Profile home in `MainShell` |

No Diary tab. No center FAB. Shopping is a nested route from Today/Plan.

State: `TodayViewModel` / `WeekViewModel` + `AppStateBus` + `SelectedDateStore`. Backend is SSOT for nutrition; Room only for offline UI cache where present.

## Today / Week data flow

```
GET /meal-plans/today?date=
  → MealPlanService.today()
  → find_covering(user, date)
  → if None: MealPlanNotFound (404)
  → else: items for date + day_progress
```

**Confirmed gap:** No auto-generation when today is outside the active plan window. Android shows error / “create plan” CTA. New calendar day after `end_date` → empty Today.

```
GET /meal-plans/week
POST /meal-plans/generate
POST /meal-plans/{id}/regenerate
```

Generation uses AI proposal → validate → persist; on AI failure uses `build_catalog_meal_plan_proposal` (4 fixed templates cycled by meal_type **identically every day**).

## Duplicate menu root cause (backend)

`backend/app/ai/fallback_plans.py`: one breakfast/lunch/dinner/snack template reused for every day. When DeepSeek quota fails or validation falls back, all 7 days look the same.

AI path may also under-diversify; engine `validate_plan` checks macros/cook time/allergies — **not** cross-day recipe uniqueness.

## Photo recognition pipeline

```
AddFoodViewModel.analyzePhoto
  → multipart POST /nutrition/photo/analyze
  → nginx (client_max_body_size **1m**)
  → PhotoAnalysisService.analyze
  → OpenAIVisionProvider
  → catalog match → PhotoAnalyzeOut
```

UI error «Не удалось распознать фото» from:
1. Generic catch in `AddFoodViewModel` (non-ApiException / poorly mapped HTTP)
2. `TextAIUnavailable` message from vision exception wrap

### Confirmed P0: nginx body limit

`nginx/nginx.conf` → `client_max_body_size 1m;`

Phone camera JPEGs are typically 2–8 MB. Backend allows ~5 MB (`openai_vision_max_image_bytes`). Nginx rejects large uploads **before** the app (413 HTML), Android maps to generic failure.

Secondary risks: missing OpenAI key, MIME quirks, provider timeout, quota on `FEATURE_FOOD_PHOTO`.

## Diary vs plan (product)

| Concept | Storage | Today (prior Phase 22) |
|---|---|---|
| Planned meals | `meal_plan_items` | Timeline |
| Consumed | `nutrition_logs` + completed items | Totals + «Дневник вне плана» block |

**Product decision this phase:** move all actual consumption UI to **Diary** screen; Today only shows plan + progress + quick actions.

## Problems classified

| Issue | Layer | Severity |
|---|---|---|
| Photo fails on real camera shots | Edge nginx + Android upload size | P0 |
| Identical week menu on fallback | Backend fallback templates | P0 |
| Empty Today on new day past plan end | Backend missing ensure | P0 |
| Manual “Пересобрать” for next week | Backend continuity gap | P1 |
| No Diary tab; diary jammed into Today | Android IA | P1 |
| No FAB for add food | Android IA | P1 |
| Week day chips clipped | Android UX | P2 |
| Green outline button clutter | Android design | P2 |
| Settings may include non-working toggles | Android | P2 |

## Proposed fixes (this phase)

1. Raise nginx limit to ≥6m; client-side image downscale before upload; clearer 413 mapping.
2. Expand rotating catalog fallback + diversity validation (`same_recipe_repetition` etc.).
3. `ensure_current_day_plan` on today (idempotent generate covering today).
4. Auto-schedule next week when `days_remaining <= 1` (async-friendly, idempotent).
5. Nav: Сегодня · План · Дневник · Прогресс · Профиль + FAB.
6. Compact Today; dedicated `DiaryScreen`.
7. Week day selector + compact summary polish.
8. Tests + APK; physical smoke required for COMPLETE.
