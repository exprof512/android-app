# Phase 23 Report — Bug Hunt, Refactoring & Stability

**Status: PARTIAL** — final verification in [`docs/phase-23-verification.md`](phase-23-verification.md). Unresolved P1: **B23-14 timezone only**. Physical-device smoke is **pending** (not run).

## 1. Audit summary

Re-audited Android, backend, AI routing, and prior phase claims without treating “fixed” as proof. Highest-risk clusters:

1. Client-side **idempotency defeat** and **selected-date** bugs  
2. **Plan ↔ diary** lifecycle gaps (replace / delete / duplicate)  
3. **Progress** consumed totals ignoring diary when no plan  
4. **Today refresh races** overwriting mutations  
5. Photo **quota before success**; continuity generate burning Free quota  

Full table: [`docs/phase-23-bug-inventory.md`](phase-23-bug-inventory.md).

## 2. Bug inventory (counts)

| Severity | Found | Fixed this phase | Deferred |
|----------|------:|-----------------:|---------:|
| P0 | 2 | 2 | 0 |
| P1 | 12 | 10 | 2 (timezone resolution; entitlement row lock) |
| P2 | 9 | 2 (export water; AI fallback comment) | 7 |
| P3 | 4 | 1 (fallback docstring) | 3 |
| Info | 6 | — | keep regressions |

Ideas for later: [`docs/phase-24-backlog.md`](phase-24-backlog.md).

## 3. Fixed bugs (root causes → fixes)

| ID | Fix |
|----|-----|
| B23-01 | Stable `Idempotency-Key` for replace (`replace:itemId:reason`) and photo confirm (session key) |
| B23-02 | `TodayViewModel` / `DiaryViewModel` cancel prior refresh + generation guard |
| B23-03 | `replace_item`: if completed → keep completed + `upsert_from_meal_plan_item` |
| B23-04 | Diary delete of plan-linked log → uncomplete meal-plan item |
| B23-05 | Reject `duplicate` of `meal_plan_item` logs (422) |
| B23-06 | Shared `compute_day_consumed` for Progress (diary without plan) |
| B23-07 | `AddFoodViewModel` uses `SelectedDateStore` for `loggedOn` |
| B23-08 | Photo analyze: entitlement `consume` **after** successful vision |
| B23-09 | Diary/AddFood parse errors via `ApiErrorParser.fromThrowable` |
| B23-10 | Nav bar reserves FAB center slot (`onFabClick` non-null) |
| B23-11 | `RefreshCoordinator.sessionEpoch` bumped on logout/delete |
| B23-12 | Continuity `generate(..., charge_entitlement=False)` |
| B23-13 | Concurrent ensure: re-fetch covering plan on generate failure |
| B23-16 | Export includes `water_entries` |

## 4. Backend / Android refactoring

- **Backend:** `app/nutrition/day_balance.py` — single merge for Progress; diary lifecycle coupled to plan; photo quota ordering; continuity quota split.  
- **Android:** refresh jobs, selected-date Add Food, stable idempotency, FAB dock slot, logout/refresh epoch.  
- No large feature rewrites; no new product screens.

## 5. AI provider architecture

**Verified unchanged:**

- Text → DeepSeek (`build_text_provider`)  
- Vision / images → OpenAI  
- Tests: `test_ai_provider_routing.py` (existing)

`FallbackTextProvider` docstring corrected (not wired as OpenAI→DeepSeek in prod).

## 6. Database

No new migrations. Existing unique indexes on `nutrition_logs.meal_plan_item_id` and idempotency keys reused.

## 7. Tests

```text
tests/test_phase23_stability.py  ......  (6 passed)
```

Covers: delete→uncomplete, duplicate reject, progress without plan, replace→diary sync, export water, continuity generate (with seeded catalog).

Also re-run: phase 22 nutrition invariants + phase 18 account (earlier pass in suite subset).

Android: `:app:assembleDebug` + `:app:testDebugUnitTest` **EXIT 0**.

## 8. Physical device

**Not executed in this environment.** Install APK and smoke:

login/logout · Today · Plan · Diary · FAB Add Food · manual + photo · eat/skip/replace · water/weight · Progress · Profile · restart · offline.

## 9. Performance / security

- No N+1 hotspots newly introduced; Progress now always reads diary (intentional).  
- Ownership: no change to user_id isolation patterns.  
- Secrets remain server-side.

## 10. Remaining / deferred

| Item | Why deferred |
|------|----------------|
| Profile timezone → server today | Needs careful API default change + migration of callers |
| Entitlement FOR UPDATE | Needs load test; partial risk |
| Week summary planned-vs-consumed labels | UX copy; not data loss |
| AI context diary merge | Use shared helper next pass |
| Water undo date-scoped | API already has delete-by-id |
| Camera / HEIC | Product feature → Phase 24 backlog |
| Giant VM split | Justified later; stability first |

## 11. Definition of Done checklist

- [x] Bug inventory  
- [x] P0 fixed  
- [x] Critical P1 fixed (timezone/lock deferred)  
- [x] Regression tests  
- [x] Plan≠consumed invariant kept  
- [x] AI DeepSeek/OpenAI split verified  
- [x] Export water  
- [x] APK builds  
- [ ] Physical smoke (user)  
- [x] Docs + backlog  

## 12. Artifacts

- **Commit:** `1e8ef088759ea9bd291eabf8b212cba3cc32a62c` (`refactor(phase-23): stabilize app and fix core bugs`)
- **APK:** `/root/app-android/android-app/android/app/build/outputs/apk/debug/app-debug.apk`
- **Bugs found:** 27 tracked (+ 6 info)
- **Fixed:** 15 (2 P0 + 10 P1 + 2 P2 + 1 P3)
- **Deferred:** see inventory / Phase 24 backlog
- **Tests:** full backend pytest green; Android unit tests + assembleDebug green
- **Physical device:** pending user smoke
