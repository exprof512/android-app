# Phase 23 — Final verification

**Status: PARTIAL.** Code audit + full test rerun on 2026-09-24. Physical-device smoke was **not** run and is **pending**.

## Unresolved P0

None.

## Unresolved P1

| ID | Status | Why it stays open |
|----|--------|-------------------|
| B23-14 | DEFERRED | `profile.timezone` is stored and unused. Server defaults still use process `date.today()`. Android often sends `date=`, so the mismatch shows up near midnight when a caller omits the date. Not a new feature; left because changing every default “today” is a behavior change across meal plans, water, diary, and progress. |

## Classification of the 27 inventory bugs

| ID | Sev | Class | Note |
|----|-----|--------|------|
| B23-01 | P0 | FIXED | Replace key `replace:{itemId}:{reason}`; photo confirm key stable for the ViewModel lifetime |
| B23-02 | P0 | FIXED | Today and Diary cancel the previous refresh and ignore stale generations |
| B23-03 | P1 | FIXED | Completed replace upserts the diary row to the new macros |
| B23-04 | P1 | FIXED | Deleting a plan-linked log sets the slot back to `planned` |
| B23-05 | P1 | FIXED | Duplicate of a plan-linked log returns 422 |
| B23-06 | P1 | FIXED | Progress uses `compute_day_consumed` (diary counts with no plan) |
| B23-07 | P1 | FIXED | Add Food `loggedOn` is `SelectedDateStore` |
| B23-08 | P1 | FIXED | Photo quota is consumed only after vision succeeds. User-initiated plan generate / replace still call `consume` before the provider; a delivered catalog fallback is still a successful plan |
| B23-09 | P1 | FIXED | Diary and Add Food use `ApiErrorParser.fromThrowable` |
| B23-10 | P1 | FIXED | `onFabClick` reserves the center nav slot under the Scaffold FAB |
| B23-11 | P1 | FIXED | Logout and delete bump `sessionEpoch` so refresh cannot restore the session |
| B23-12 | P1 | FIXED | Continuity passes `charge_entitlement=False` |
| B23-13 | P1 | FIXED | Repeat `GET /today` hits `find_covering` or the same generation hash and does not insert another plan (`uq_meal_plans_user_generation_request_hash`). A concurrent pair can still both call the text provider once before the loser hits the unique index |
| B23-14 | P1 | DEFERRED | Timezone |
| B23-15 | P2 | FIXED | Refresh clears tokens only on HTTP 401/403. No in-app “session expired” navigation (residual, not the original wipe-on-IO bug) |
| B23-16 | P2 | FIXED | Export includes `water_entries` |
| B23-17 | P2 | DEFERRED | AI remaining still ignores diary |
| B23-18 | P2 | DEFERRED | Week chips still sum planned kcal |
| B23-19 | P2 | DEFERRED | Water undo is global last entry |
| B23-20 | P2 | DEFERRED | Water prefs keyed by device today |
| B23-21 | P2 | DEFERRED | Default 100 g, unmatched foods, no HEIC/camera |
| B23-22 | P2 | DEFERRED | Text repair writes one usage row per attempt |
| B23-23 | P2 | DEFERRED | Entitlement consume has no row lock (this is P2, not P1) |
| B23-24 | P3 | FIXED | Progress no longer swallows diary merge errors; it uses `compute_day_consumed` |
| B23-25 | P3 | DEFERRED | Rounding helpers still differ |
| B23-26 | P3 | FIXED | `FallbackTextProvider` docstring matches DeepSeek-only DI |
| B23-27 | P3 | DEFERRED | Large ViewModels; diary day API unused |

Info rows (plan≠consumed, single-flight refresh, account delete, AI routing, nginx 8m) were re-checked and still hold. Not counted in the 27.

## Checklist

| Check | Result |
|-------|--------|
| Today calories | `day_progress` counts completed slots plus diary logs not tied to those slots. Planned slots are `planned_remaining_kcal` only |
| Diary totals | Diary sums `nutrition_logs` for the selected date |
| Progress totals | Same merge as Today via `compute_day_consumed`, including days with no plan |
| Plan vs consumed | Uneaten slots are excluded. Phase 22 invariant tests still in the suite |
| Eat | `complete_item` upserts one diary row |
| Replace | Completed slot stays completed and diary macros match the new slot |
| Delete diary entry | Plan-linked delete uncompletes the slot |
| Duplicate tap | Stable idempotency keys on replace and photo confirm |
| Selected date | Add Food uses `SelectedDateStore` |
| Photo recognition | Pipeline unchanged: gallery → downscale → OpenAI vision. Not re-run against a live provider in this pass |
| Photo quota | `FEATURE_FOOD_PHOTO` consume is after a successful vision response |
| Plan continuity | Missing covering plan → one `generate(..., force=False)` |
| Free quota vs continuity | `ensure_current_day_plan` and next-week prep pass `charge_entitlement=False`, so `FEATURE_MEAL_PLAN_GENERATE` is not incremented. A second call does not generate again |
| DeepSeek text | `build_text_provider` returns `DeepSeekChatProvider` or mock. OpenAI text is not in that chain |
| OpenAI images | Recipe images use `OpenAIImageProvider`. Food photos use `OpenAIVisionProvider` |
| Account deletion | `confirmation=DELETE`, then 401 on the old token. Covered by `test_phase18_account` |
| Export | Non-empty envelope plus `water_entries`. Covered by `test_phase23_stability` |

## `ensure_current_day_plan`

- If a ready plan covers the date, it returns that plan and does not call generate.
- Generate uses `force=False`, so the same user/goal/start/days hash is reused.
- The unique index on `(user_id, generation_request_hash)` blocks a second stored plan.
- Free meal-plan quota is not charged. That is intentional (B23-12), not an unbounded loop: each missing window is generated at most once.
- Text usage rows are still written by `TextAIService` when a new window is actually generated.

## Tests (this pass)

- Backend: `python -m pytest -q` exit 0 (full suite, 100%).
- Android: `:app:assembleDebug` and `:app:testDebugUnitTest` exit 0 (UP-TO-DATE; sources unchanged since the Phase 23 APK).

## APK

`/root/app-android/android-app/android/app/build/outputs/apk/debug/app-debug.apk`

## Physical smoke — pending

Not run. Do not treat this verification as a phone pass.

1. Login and logout.
2. Today: uneaten meals must not add calories; «Я съел» must match Diary and Progress.
3. Replace a eaten meal: old dish must not stay in the totals.
4. Delete that diary row: Today must drop those calories.
5. Open Diary on yesterday, add food: the row must land on yesterday.
6. Double-tap replace and photo confirm: one result, quota not doubled.
7. Photo from the gallery through confirm into Diary.
8. Open Today on a day with no plan: a plan appears, and the free generate counter does not drop for that automatic create.
9. Export file contains water. Delete account with `DELETE`; the old session must fail.
10. App restart and a short offline/online cycle on Today.

## Exact remaining issues

- P1: B23-14 timezone.
- P2: B23-17, B23-18, B23-19, B23-20, B23-21, B23-22, B23-23.
- P3: B23-25, B23-27.
- Known limitation: two parallel first-time Today loads can both call the text provider; only one plan is stored.
- Physical smoke: pending.
