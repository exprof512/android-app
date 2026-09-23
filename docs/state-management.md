# State management (Phase 18)

PostgreSQL is the authoritative source. Android repositories hold in-memory snapshots and emit typed `DomainEvent`s via `AppStateBus` so screens stay consistent without ad-hoc `refresh()` coupling.

## Domains

| State | Backend | Android repository | Cache | Invalidation | Dependent screens |
|---|---|---|---|---|---|
| Auth session | JWT + `refresh_tokens` | `AuthRepository` / `TokenStore` | Encrypted prefs | logout/delete | Boot, shell |
| Profile + goal | `GET/PUT /profile` | `ProfileRepository` (`StateFlow`) | memory | `ProfileChanged`, `WeightChanged` | Today, Week, Progress, Profile |
| Weight | `POST /weight-entries`, mirrored on profile | `ProgressRepository` | none local | emits `WeightChanged` | Progress, Profile, Today |
| Plan (week) | `GET /meal-plans/week` | `MealPlanRepository.weekPlan` | memory | `PlanChanged` | Week, Shopping |
| Plan (today) | `GET /meal-plans/today` | `MealPlanRepository.todayPlan` | memory | `PlanChanged` | Today |
| Selected date | — | `SelectedDateStore` | memory | `SelectedDateChanged` | Today, Week |
| Nutrition logs | `/nutrition/logs` | NutritionApi via Today VM | none | `NutritionLogChanged` | Today, Progress |
| Shopping | shopping APIs | `ShoppingRepository` + VM | memory | `ShoppingChanged`, `PlanChanged` | Shopping |
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
```

## Targets vs consumption

- **USER TARGET** — active `goals.*` from profile.
- **PLAN SNAPSHOT** — `meal_plans.*_target_*` frozen at generation.
- **ACTUAL CONSUMPTION** — completed `meal_plan_items` ∪ `nutrition_logs` for the day.

UI must not silently mix these without labeling.

## Mutations

Generate / replace / complete / rebuild shopping / add weight / edit profile all go through repositories that emit events. ViewModels subscribe to `AppStateBus` instead of calling sibling ViewModels.
