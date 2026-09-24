# Phase 22 Report — UI/UX + Data Consistency

**Status: PARTIAL** — code and automated tests landed; physical-device smoke not executed in this session.

**Commit message:** `refactor(phase-22): ui ux and data consistency`

## UI audit

| Issue | Severity | Fix |
|---|---|---|
| Today totals looked “wrong” vs 1/3 meals | P0 (product) | Diary section + breakdown; not aggregation bug |
| Remaining showed 0 when over target | P1 | `over_target_kcal` + copy |
| Recipe titles with `(YYYY-MM-DD)` | P2 | Strip on API display + stop generating + Android helper |
| Add Food “Фото” narrow vertical chip | P2 | Full-width photo CTA + FlowRow meal chips |
| Excessive green/outlined cards | P2 | Surface elevation; meal accent bar |
| AI block dominated Today | P2 | Compact FoodAI row |
| Water “Отменить” always visible | P3 | Shown only when `total > 0` |

## Critical bugs / root causes

**Screenshot 2448 kcal / 1 of 3 meals:** Backend `day_progress` correctly excluded planned slots. Consumed included completed breakfast **plus** untied `nutrition_logs` (AI/manual/recipe) that Today did not render. UX made totals appear inconsistent with the meal timeline.

## Nutrition aggregation rules (authoritative)

```
consumed = Σ completed meal_plan_items (date)
         + Σ nutrition_logs (date) not already counted via completed item link
```

Planned / skipped / replaced originals do **not** enter consumed.

API fields added to `DayProgressOut`:

- `over_target_kcal`
- `planned_remaining_kcal`
- `from_plan_kcal`
- `from_diary_kcal`

## Planned vs actual

| State | Consumed? |
|---|---|
| PLANNED | No |
| EATEN / completed | Yes |
| SKIPPED | No |
| REPLACED | Only if new item completed / diary entry exists |
| Diary-only log | Yes (shown under «Дневник (вне плана)») |

## State synchronization

Unchanged bus events; Today now **renders** `nutritionLogs` and supports delete. Mutations still emit `NutritionLogChanged` / `PlanChanged`.

## Design system

See `docs/ui-design-system.md`.

## Screens touched

- Today (progress, meals, diary, water, AI)
- Add Food sheet
- AI recommendation cards (shorter “why”)
- FoodAICard (no default border stroke)

## Tests

- `backend/tests/test_phase22_nutrition_invariants.py`
- Android: `DisplayNamesTest`, extended `Phase19ModelsTest`

## Physical device

**Not run** — cannot claim smoke PASS.

## Remaining / out of scope

- Full Profile/FAB/shopping visual pass beyond soft card elevation
- Compose UI instrumentation tests on device
- Historical recipe rows in DB still store dated names (display stripped)
- Production hardening (Phase later)

## AI providers

Unchanged: DeepSeek text; OpenAI vision/images (Phase 21).
