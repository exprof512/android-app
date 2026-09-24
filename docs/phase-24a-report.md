# Phase 24A — Today UX and navigation

Status: **code complete, physical smoke pending**.

This phase is an Android product UX pass. Backend nutrition formulas, entitlements, AI quota, plan generation, diary persistence, photo API, and authentication were not rewritten.

## Problems found

The previous shell put a large green “+” in the center of the bottom bar. That button opened Add Food, which already lives inside Diary, and it competed with the FoodAI card on Today. Tab labels (including «Дневник») wrapped on narrow widths. Today stacked a tutorial banner, an AI card, nutrition, hints, the next meal, the meal list, water, weight, and the same add-food action.

## Navigation

Bottom bar destinations, equal width, one line, Material icons:

| Slot | Label | Route |
| --- | --- | --- |
| 1 | Сегодня | Home |
| 2 | План | Plan |
| center | AI | sheet, not a route |
| 4 | Прогресс | Progress |
| 5 | Профиль | Profile |

«Дневник» is not a tab. Diary stays a route opened from Today («Дневник» / empty-state action). The center control is a 52dp green circle with `AutoAwesome`, label «AI», inside the bar (not a Scaffold FAB). System navigation insets are applied on the bar. Labels use `maxLines = 1` and do not wrap.

## Central AI

`AiHubSheet` is a bottom sheet. It does not answer locally. Rows call existing flows:

- Что съесть? → `TodayViewModel.requestWhatToEat()`
- Адаптировать день → `requestAdaptDay()`
- Заменить блюдо → existing replace-reason dialog for the next planned meal
- Что купить? → shopping list
- Спросить FoodAI → existing AI chat

Today-scoped actions are delivered with `pendingAiAction` after navigating Home, because the Today view model is scoped to that destination. Preview and confirm sheets on Today are unchanged.

## Today

Order: lighter date header («Сегодня · твой план питания»), dismissible tip (`FoodAITipBanner`, already remembered), nutrition card, next meal (Съел / Пропустить / Заменить), meal list, Diary / Plan / Shopping, water, steps / weight / progress.

Nutrition copy distinguishes consumed calories from planned food that is not eaten yet («Вне плана» and «В плане ещё … — не съедено»). The old «Дневник +N» line is gone. Add Food is not on Today.

## Diary and Add Food

Diary is its own screen: date selector, calorie and macro totals, breakfast / lunch / dinner / snack (empty sections say «Нет записей»), and «Добавить еду». The existing sheet still offers photo, search, recent foods, quick calories, and meal type. Photo recognition still uses the current backend.

## Plan, Progress, Profile

Plan header states that a planned meal is not consumed until «Съел». Progress keeps the same calculations and uses a shorter consumed-vs-goal line. Profile keeps the existing sections and the shared color, type, and card tokens.

## Design tokens

Existing `FoodAIColors`, `FoodAITypography`, `FoodAIDimens`, `FoodAIShapes`, and shared components are the system. `FoodAISpacing` is an alias of `FoodAIDimens`. No new component library.

## Tests

- Android: `:app:testDebugUnitTest` and `:app:assembleDebug` succeeded after the navigation change. `MainNavContractTest` checks the four tab labels (no «Дневник», no «+», single line). There is no Compose UI-test harness, so flows 1–12 in the prompt were not automated as instrumented tests.
- Backend: `python -m pytest -q` exit 0 (246 tests). No backend behavior change in this phase.

## APK

`/root/app-android/android-app/android/app/build/outputs/apk/debug/app-debug.apk`

Install this build on a physical phone. Debug API base URL must be a host the phone can reach (public IP/hostname or LAN), not `10.0.2.2`.

## Physical smoke

**Pending.** This environment has no phone. Do not treat this phase as device-verified.

Checklist for the phone:

1. Open Today and confirm the bar reads Сегодня, План, AI, Прогресс, Профиль on the narrowest device, with no wrapped labels and no “+”.
2. Tap AI, open one action, close the sheet.
3. Open Plan, then Diary from Today, add food (photo and search), return to Today, check totals.
4. Open Progress and Profile.
5. Recreate the activity and confirm the selected tab.
6. Confirm the bar does not sit under the system navigation or cover Today content.

## Known issues

- Physical smoke is not done.
- Profile timezone is still unused for the server “today” (Phase 23, B23-14). Not changed here.
- Replace from the AI sheet no-ops when the selected day has no remaining planned meal.
- Layout at 360 / 375 / 390 / 412 dp was checked by construction (equal weights, single-line labels, 52dp center, inset padding), not by a device or emulator.
- No screenshots.
