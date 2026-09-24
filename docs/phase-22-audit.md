# Phase 22 Audit — UI/UX + Nutrition Consistency

## Current architecture (relevant)

| Layer | Role |
|---|---|
| `meal_plan_items` | Planned day slots; `status` planned/completed/skipped/replaced |
| `nutrition_logs` | Actual diary entries (manual, recipe, photo_ai, meal_plan_item, …) |
| `MealPlanService._build_day_progress` | Authoritative Today totals |
| `GET /meal-plans/today` → `day_progress` | Android Today consumes this |
| `AppStateBus` | Invalidation after mutations |

## Planned vs consumed (as designed in code)

`day_progress.consumed_*` =
1. Sum of **completed** `meal_plan_items` for the date
2. **Plus** all `nutrition_logs` for the date whose `meal_plan_item_id` is not already counted via (1)

**Planned / skipped items are NOT included** in backend aggregation. Verified in `_build_day_progress`.

## Root cause of screenshot bug (2448 kcal / 1 of 3 meals)

User `exprof512@gmail.com` on 2026-09-24:

| Source | kcal |
|---|---|
| Completed breakfast (plan) | 374 |
| Extra diary logs (recipe/manual, not shown on meal timeline) | ~2074 |
| **day_progress total** | **~2448** |

Lunch/dinner **planned** slots were never counted. The UI showed only 3 plan cards, so the user inferred “only breakfast was eaten → totals must be ~374”. Hidden diary entries from AI suggestions / manual / recipe logging explain the macros (protein ~170 g).

**Primary product bug:** Today does not surface diary entries, so authoritative totals look “wrong” relative to the meal timeline.

**Secondary UX bugs:** remaining shows “0” when over target; recipe titles include `(YYYY-MM-DD)` from catalog fallback; Add Food chip layout clips “Фото”.

## Meal state machine (existing)

`planned` | `completed` | `skipped` | `replaced` (+ `is_completed` bool). No new status system needed.

## State sync

`NutritionLogChanged` / `PlanChanged` refresh Today. Logs are fetched into `TodayUiState.nutritionLogs` but **not rendered**.

## Proposed fixes (Phase 22)

1. Show diary section on Today; label totals as “Съедено” with breakdown.
2. `day_progress`: add `over_target_kcal`, `planned_remaining_kcal`; fix over-target copy.
3. Strip date suffixes from user-facing recipe names (display + stop generating).
4. Soften design system (less green borders); compact meals; fix Add Food chips.
5. Regression tests: planned never counted; diary-only entries counted; eat/skip/delete transitions.
