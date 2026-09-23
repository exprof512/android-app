# State management (Phase 18–19)

PostgreSQL is the authoritative source. Android repositories hold in-memory snapshots and emit typed `DomainEvent`s via `AppStateBus` so screens stay consistent without ad-hoc `refresh()` coupling.

## Domains

| State | Backend | Android repository | Cache | Invalidation | Dependent screens |
|---|---|---|---|---|---|
| Auth session | JWT + `refresh_tokens` | `AuthRepository` / `TokenStore` | Encrypted prefs | logout/delete | Boot, shell |
| Profile + goal | `GET/PUT /profile` | `ProfileRepository` (`StateFlow`) | memory | `ProfileChanged`, `WeightChanged` | Today, Week, Progress, Profile |
| Weight | `POST /weight-entries`, mirrored on profile | `ProgressRepository` | none local | emits `WeightChanged` | Progress, Profile, Today |
| Plan (week) | `GET /meal-plans/week` (+ `week_summary`) | `MealPlanRepository.weekPlan` | memory (+ last-success) | `PlanChanged` | Week, Shopping |
| Plan (today) | `GET /meal-plans/today` (+ `day_progress`) | `MealPlanRepository.todayPlan` | memory (+ last-success) | `PlanChanged` | Today |
| Selected date | — | `SelectedDateStore` | memory | `SelectedDateChanged` | Today, Week |
| Nutrition logs | `/nutrition/logs` (also upserted on complete) | NutritionApi via Today VM | none | `NutritionLogChanged` | Today, Progress |
| Water | `/water` | `WaterRepository` | memory + prefs mirror | `WaterChanged` | Today |
| Shopping | shopping APIs (+ stale/cost/category) | `ShoppingRepository` + VM | memory | `ShoppingChanged`, `PlanChanged` | Shopping |
| Theme / units | — | `ThemePreferences`, `UnitPreferences` | SharedPreferences | immediate | whole app |
| Entitlements | `/entitlements/me` | badge fetch | none | — | Profile/Premium |

## Events

```text
PlanChanged → Today, Week, Shopping refresh
WeightChanged → Profile cache invalidate, Today/Progress refresh
ProfileChanged → Today/Week refresh
NutritionLogChanged → Today (and Progress if open)
ShoppingChanged → Shopping refresh
SelectedDateChanged → Today loads that day; Week highlights day
WaterChanged → Today water section refresh
```

## Targets vs consumption

- **USER TARGET** — active `goals.*` from profile / plan `daily_targets`.
- **PLAN SNAPSHOT** — `meal_plans.*_target_*` frozen at generation.
- **ACTUAL CONSUMPTION** — completed `meal_plan_items` ∪ `nutrition_logs` for the day (server `day_progress`).

Android must prefer `day_progress.remaining_*` from the backend; do not recompute when present.

## Mutations

Generate / replace / complete / skip / rebuild shopping / add water / add weight / edit profile / add food all go through repositories that emit events. ViewModels subscribe to `AppStateBus` instead of calling sibling ViewModels.
