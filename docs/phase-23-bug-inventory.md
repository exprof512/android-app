# Phase 23 — Bug Inventory

Audit date: 2026-09-24. Prior phase “fixed/tested” claims were re-checked against code; physical smoke still required for COMPLETE.

Severity: **P0** data loss/security/critical · **P1** major broken · **P2** important UX/logic · **P3** minor.

| ID | Area | Problem | Reproduction | Root Cause | Severity | Fix |
|----|------|---------|--------------|------------|----------|-----|
| B23-01 | Android / Idempotency | Double-tap replace/photo confirm sends a **new** `Idempotency-Key` each call → server cannot dedupe; quota burned twice | Tap «Заменить» twice quickly; or retry confirm photo | `UUID.randomUUID()` at call site in `MealPlanRepository` / `AddFoodViewModel` | P0 | Stable key per UI action (itemId+reason / photo session); reuse on retry |
| B23-02 | Android / State | Parallel `refresh()` races: in-flight GET Today/Diary finishes after mutation and overwrites UI with stale data | Eat meal while previous Today load in flight; or rapid bus events | `viewModelScope.launch` without cancel/generation guard | P0 | Cancel prior `refreshJob` or generation token before apply |
| B23-03 | Plan / Diary | Replace completed meal: `day_progress` uses **new** slot macros; diary keeps **old** `nutrition_logs` row | Complete breakfast → Replace → compare Today vs Diary | `replace_item` sets macros/`status=replaced`, never upserts diary | P1 | If `is_completed`, `upsert_from_meal_plan_item` after replace |
| B23-04 | Diary / Today | Delete plan-linked diary log leaves slot `completed` → Today still counts meal, Diary drops | Eat meal → Diary delete that entry → Today totals | Diary `delete` not coupled to plan completion | P1 | On delete of `meal_plan_item` log, uncomplete plan item (or forbid delete) |
| B23-05 | Diary / Totals | Duplicate of plan-linked log clears `meal_plan_item_id` → **double** consumed (plan + clone) | Eat → Diary «Дублировать» → Today | Dedup only by `meal_plan_item_id ∈ completed` | P1 | Reject duplicate of `source=meal_plan_item` (or require explicit “ate again”) |
| B23-06 | Progress | No covering plan → Progress shows consumed 0 while Diary has entries | Delete/archive plan or day without plan + add food → Progress | `_daily_balance` early-return without reading `nutrition_logs` | P1 | Always merge diary; share helper with `_build_day_progress` |
| B23-07 | Android / Diary | Add Food always `LocalDate.now()` → wrong day when Diary on another date | Diary yesterday → FAB add food → entry on today | `AddFoodViewModel` ignores `SelectedDateStore` | P1 | Inject selected date into all `loggedOn` / photo confirm |
| B23-08 | Entitlements / AI | Photo (and plan/replace) `consume` **before** provider success → failed vision burns Free quota | Analyze invalid/timeout photo | Pay-before-call without refund | P1 | Consume after success (photo first); document plan/replace |
| B23-09 | Android / Errors | Diary/AddFood catch only `ApiException`; Retrofit throws `HttpException` → stuck loading / silent fail | Force 4xx/5xx on nutrition APIs | No `ApiErrorParser.fromThrowable` in those VMs | P1 | Parse all throwables to typed UI errors |
| B23-10 | Android / FAB | Center Scaffold FAB with 5 equal tabs overlaps **Дневник** | Open app bottom bar | `onFabClick=null` removes center slot | P1 | Reserve FAB slot (`onFabClick` non-null) or `FabPosition.End` |
| B23-11 | Auth | Logout vs in-flight refresh can `saveSession` after `clear()` | Logout while 401 refresh running | No session epoch shared with `RefreshCoordinator` | P1 | Session generation / clear under same mutex |
| B23-12 | Continuity | `_maybe_prepare_next_week` spends Free plan-generate quota on Today open | Near week end open Today | Continuity generate always `entitlements.consume` | P1 | Continuity path without Free quota (or separate budget) |
| B23-13 | Continuity | Parallel `ensure_current_day_plan` can double-generate / clash hash | Two concurrent GET `/today` with no plan | No per-user generate lock | P1 | Advisory lock / upsert-on-conflict |
| B23-14 | Timezone | `profile.timezone` unused; server `date.today()` vs device near midnight | Cross midnight UTC vs local | No ZoneInfo resolution | P1 | Resolve today from profile TZ; Android always pass `date=` |
| B23-15 | Auth Android | Failed refresh clears tokens on **any** Exception; Main stays without logout UX | Airplane mode during 401 refresh | Broad catch + no SessionExpired navigation | P2 | Clear only on auth failure; emit session expired |
| B23-16 | Export | Export omits `water_entries` | Export account with water logs | `export_user_data` never queries water | P2 | Include water (and document other gaps) |
| B23-17 | AI context | AI “remaining” ignores diary food | Suggest food after manual snack | `_consumed_remaining` plan-only | P2 | Reuse shared day consumed helper |
| B23-18 | Week UI | Week summary kcal = **planned** sum, reads like eaten | Open Week chips | `_build_week_summary` sums all slots | P2 | Expose planned vs consumed; label UI |
| B23-19 | Water | Undo deletes last entry **any** day | Undo while viewing past day | `deleteLast` global by `created_at` | P2 | Date-scoped undo or delete by id |
| B23-20 | Water prefs | `DailyMetricsStore` water keyed by device today only | Add water for past date | Prefs ignore `recorded_on` | P2 | Key prefs by date |
| B23-21 | Photo | Unmatched foods / default 100g / HEIC / gallery-only | Unmatched confirm; HEIC gallery | Confirm filters null ingredient; ALLOWED_MIME | P2 | Manual path; fail closed >limit; backlog camera/HEIC |
| B23-22 | AI usage | Text repair retries → multiple `ai_text_usage` rows | Force invalid then ok | Per-attempt `_record_usage` | P2 | Rollup or attempt column for dashboards |
| B23-23 | Entitlements | `consume` without row lock → parallel overspend | Parallel photo/replace | No `FOR UPDATE` | P2 | Lock window row |
| B23-24 | Progress | `except Exception: pass` around diary merge | Rare import/DB error | Silent undercount | P3 | Remove bare catch |
| B23-25 | Macros | Rounding / scale helpers diverge (HALF_UP vs truncate) | Edge grams | Multiple helpers | P3 | Shared scale helpers |
| B23-26 | AI docs | `FallbackTextProvider` comment says OpenAI→DeepSeek but prod DI is DeepSeek-only | Read fallback.py | Stale comment | P3 | Fix comment |
| B23-27 | Architecture | Giant Today/PlanScreens/Chat VMs; unused diaryDay API | Code size | Organic growth | P3 | Split gradually; prefer diaryDay |
| — | Plan≠Actual | Planned slots do **not** auto-count as consumed | Phase 22 tests | By design | Info | Keep regressions |
| — | Auth refresh | Android single-flight refresh exists | Code | Mitigated | Info | Keep |
| — | Account delete | DELETE confirmation / 422 path works | `test_phase18_account` | Prior fix holds | Info | Keep regression |
| — | AI routing | DeepSeek=text, OpenAI=vision+images | `dependencies` + routing tests | Correct | Info | Preserve |
| — | Photo body | nginx 8m + Android downscale | nginx.conf / AddFood | Phase 22 fix | Info | Keep |

## Shared root causes

1. **Triplicated consumed merge** (Today / Progress / AI) already drifted.  
2. **Plan item ↔ diary** lifecycle incomplete on replace/delete/duplicate.  
3. **Client defeats** server idempotency and date selection.  
4. **Quota before success** for AI/vision.  
5. **No cancelable refresh** on Android ViewModels.

## Fix order (this phase)

1. P0: B23-01, B23-02  
2. P1 data: B23-03…B23-07, B23-08 (photo), B23-09, B23-10  
3. P1 continuity/auth: B23-11, B23-12 (B23-13/14 partial or deferred if time)  
4. Shared `compute_day_consumed` for Progress + Today  
5. Regression tests + docs + APK  
