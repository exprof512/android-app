# PHASE 18 AUDIT — Core Consistency

**Date:** 2026-09-23  
**Base commits:** `1c094bf` (Phase 17), `db294bc` (UX prerequisite)  
**Scope:** read-only analysis of `docs/`, `backend/`, `android/` before implementation.

---

## 1. Current data sources

| Domain fact | Backend authoritative | Android today | Notes |
|---|---|---|---|
| Auth session | `refresh_tokens` + JWT | `TokenStore` (EncryptedSharedPreferences) | OK |
| Display name / avatar | **none** (local-only) | `UserProfileStore` SharedPreferences | Documented as device-local |
| Profile biometrics / goal | `user_profiles` + `goals` via `GET/PUT /profile` | `ProfileRepository.getProfile()` one-shot per screen | No shared StateFlow |
| Weight (latest) | `weight_entries` + mirrored `user_profiles.current_weight_kg` on add | Progress: `GET /progress/summary`; Today/ProfileDetails: `profile.current_weight_kg` | Same DB field if Progress updated, but screens load independently → stale UI |
| Calorie **goal target** | `goals.calorie_target_kcal` | Today uses `profile.goal` then `plan.dailyTargets`; Progress uses `summary.calorieTargetKcal` then today balance | Intentional: goal vs plan snapshot can diverge after regen |
| Calorie **plan snapshot** | `meal_plans.calorie_target_*` | Mixed with goal on Today | Not labeled in UI → feels like “inconsistency” |
| Consumed macros (Today) | Completed `meal_plan_items` (+ `nutrition_logs` on Progress) | Today: **completed plan items only** (ignores diary logs in ring) | Diary section separate; Progress unions logs |
| Active meal plan | `meal_plans` covering date | `MealPlanRepository.today/week` one-shot; **separate** `TodayViewModel` / `WeekViewModel` StateFlows | No cross-screen invalidation |
| Shopping list | `shopping_lists` | `ShoppingViewModel` local state; regenerate writes list into state | Should work after rebuild if response OK |
| Entitlements | `usage_limits` | Display badge only | 429 often opaque |
| Theme / units | **none** | `foodai_settings` prefs | **Fake relative to UI** (prefs saved, Theme/units unused) |
| Notifications | **none** | `foodai_notifications` prefs | Explicitly “pushes later”; local-only OK if labeled |
| Promotions/discounts | **none** | Onboarding checkbox copy only | Fake promise |
| Water / steps | **none** | `DailyMetricsStore` local | OK as device metrics |

**Room:** not used. Caches = SharedPreferences + in-memory ViewModel StateFlows only.

---

## 2. Duplication / multi-truth

1. **Plan state:** `TodayViewModel` and `WeekViewModel` each hold independent `MealPlanDto?`. Mutation on one screen does not notify the other.
2. **Weight:** Progress updates via `POST weight` → updates profile in DB, but Today/Profile keep old `ProfileResponse` until their own refresh.
3. **Calories target:** Today prefers active goal; Progress may show goal or daily balance target; plan snapshot unused/unlabeled → user sees different “target” numbers.
4. **Consumed calories:** Today = completed meals only; Progress daily balance = completed meals ∪ nutrition_logs → rings disagree after diary snack.
5. **Generate entrypoints:** `ProfileRepository.generateFirstPlan` and `MealPlanRepository.generate` both call `POST /meal-plans/generate` with `LocalDate.now()` — duplicate paths, no shared result bus.

---

## 3. Screens vs APIs

| Screen | Primary APIs | Gap |
|---|---|---|
| Today | `GET /meal-plans/today`, `GET /profile`, local metrics, `nutrition/logs` | Manual refresh icon; no log macros in ring |
| Week | `GET /meal-plans/week?start_date=today` | UI filters meals to **selectedDate only** (day strip exists, but no week overview cards); stale after Today generate |
| Shopping | `week` + `shopping current/generate` | Rebuild updates VM state — if UI still empty, check response mapping / empty items |
| Progress | `/progress/summary`, weight POST | Does not push Profile/Today |
| Profile hub | local name/avatar + nav | Backend profile often passed from parent once |
| Settings | local prefs | Theme/metric toggles do not drive `FoodAiTheme` / formatters |
| Account | sessions/export/delete/verify | Export never save/share; delete may 422 |
| Onboarding | `PUT /profile`, `POST /meal-plans/generate` | `force=true` regenerate burns Free quota (3/day) → 429 |

---

## 4. ViewModels with private state copies

- `TodayViewModel` — plan, profile, metrics, logs
- `WeekViewModel` — plan, profile, selectedDate, weekDates
- `ShoppingViewModel` — list, mealPlanId
- `ProgressViewModel` — summary
- `SessionViewModel` — account snapshot
- `OnboardingViewModel` — draft
- `AccountViewModel` — account + sessions
- `ProfileViewModel` — local display only

None subscribe to a shared repository StateFlow for plan/profile/weight.

---

## 5. Stale cache / refresh policy

- No TTL; “cache” = last ViewModel value until `refresh()`.
- Bottom-nav keeps ViewModels alive → After Today “Создать план”, Week can stay on `missingPlan` ErrorPane until manual refresh or process death.
- `MealPlanRepository` is `@Singleton` but **stateless** (no flow) — misses chance for SSOT.

---

## 6. HTTP 200/422 mishandling

### Delete account → 422 (critical)

- Backend: `DELETE /users/me` **requires** JSON body `DeleteAccountRequest.confirmation == "DELETE"` (`users.py`, `schemas.py`).
- Android: `@HTTP(DELETE, hasBody=true)` + `DeleteAccountRequest("DELETE")`.
- Likely failure modes to confirm in tests:
  1. Empty/missing body (client/proxy) → FastAPI **422** validation.
  2. Pydantic `ValueError` on confirmation → 422.
- UI tracks `account_deleted` **before** call succeeds; session cleared only after 2xx in repository (good), but error path may look “failed delete” with confusing messaging.
- **Fix direction (no Android-only workaround):** prefer `POST /users/me/delete` with body, or DELETE with header `X-Confirm-Delete: DELETE`, keep one contract + regression tests.

### Export → “false 200” (critical)

- Backend `export_user_data` builds a **real** JSON payload (account, profile, goals, prefs, pantry, weights, logs, plans, items, shopping, chat, favorites) — secrets excluded.
- Android: `exportData().toString()` → toast with character count; **no file write / share Intent**. User perceives “nothing exported”.
- Empty success risk: brand-new account still returns non-empty envelope (`exported_at`, empty arrays). Treat missing `exported_at` / parse failure as error; require share/save for UX success.

### Other

- Shopping regenerate assigns `list` from API — if backend returns 200 with empty items for valid plan, UI looks “unchanged”.
- Analytics / some `runCatching` paths swallow errors (non-product-critical).

---

## 7. UI claims without backend

| UI control | Backend? | Persist? | Behavior? |
|---|---|---|---|
| Системная тема | No | Prefs yes | **No** — `FoodAiTheme(darkTheme=false)` always light; `prefer_system_theme` unused |
| Метрическая система | No | Prefs yes | **No** — all UI hardcodes кг/см/л |
| Учитывать акции и скидки (onboarding) | No field/API | Draft only? | **No** — copy promises promotions |
| Уведомления meals/water/tips | No | Prefs yes | Prefs only; copy admits pushes later |
| Подсказки | Local tip dismiss | Yes | **Yes** (local) |

---

## 8. Backend exists, UI underuses

| Capability | Backend | Android gap |
|---|---|---|
| Full week plan items | `GET /meal-plans/week` returns full window | UI shows one selected day only (no week summary / 7-day meal grid) |
| Nutrition logs CRUD | `/nutrition/logs` | Today lists + snack only; not in calorie ring |
| Favorites | `POST/DELETE /recipes/{id}/favorite` | Wired in repository; recipe UX may be incomplete |
| Replace `Idempotency-Key` | Header supported | Android replace **does not send** key |
| Generate week (days=7) | `POST /meal-plans/generate` | Works, but no per-day status model (`planned/missing/generating/failed`) |
| Policy max weekly weight change | Engine + Settings; schema max **2.0** kg (`limits.WEEKLY_CHANGE_KG_MAX`); engine default safe **1.0** | Onboarding may hit `exceeds_safe_weekly_change` at 1.0 while DB allows up to 2.0 — confusing |
| Admin AI / events | Phase 17 | Not user-facing (OK) |
| Sessions list/revoke | Phase 17 | Account screen present |

---

## 9. Today / Week plan sync (user report)

**Backend:** `today` and `week` both use `find_covering(on_date)`; week returns **full** `start_date..end_date` items (not collapsed). Generation with `days=7` persists a week.

**Root cause of “Today has plan, Week says create”:** Android ViewModel isolation + no invalidation after generate/replace — not primarily a missing week API.

**Root cause of “Week shows only current day”:** UI design filters `items` by `selectedDate`; date chips exist but no multi-day summary. If `weekDates` empty / plan missing, ErrorPane looks like “no plan”.

---

## 10. Onboarding regeneration / 429

- Endpoint: `POST /meal-plans/generate` with `force=true` via `regeneratePlan` / questionnaire rebuild.
- Free quota: `ENTITLEMENT_FREE_MEAL_PLAN_PER_DAY=3` (`FEATURE_MEAL_PLAN_GENERATE`).
- Each forced regen **consumes** one slot; retries without Idempotency-Key can burn quota.
- Screen reopen should **GET** plan, not regenerate — `ensurePlan` correctly GETs first, but rebuild paths use `force=true`.
- **Proposed beta defaults (apply in implementation after review):**
  - meal_plan_generate Free: **10 / day**
  - meal_replace Free: **15 / day**
  - chat Free: **40 / day**
  - Keep Premium unlimited / high ceiling
  - Add Idempotency-Key on generate/replace from Android
  - Surface remaining quota + Retry-After on 429

---

## 11. Settings matrix (PART 21 preview)

| Setting | UI | Backend | Persist | Behavior | Tests |
|---|---|---|---|---|---|
| Tips banners | Y | N | Y | Y | N |
| Metric units | Y | N | Y | **N** | N |
| System theme | Y | N | Y | **N** | N |
| Notifications (3) | Y | N | Y | Pref only | N |
| Promotions checkbox | Y (onboarding) | N | Draft? | **N** | N |
| Language/region | Static text | N | N | Fake display | N |
| Edit questionnaire | Y | Y | Y | Y | Partial |
| Account/legal | Y | Y | — | Partial | Partial |

---

## 12. Implementation priority (locked for Phase 18)

1. **P0** Account delete contract + tests; export content + share/save + tests  
2. **P0** Shared repositories + typed invalidation (`PlanChanged`, `WeightChanged`, …)  
3. **P0** Today ↔ Week ↔ Shopping sync after mutations; week 7-day presentation + day status  
4. **P1** Onboarding 429 analysis: idempotency + beta quotas + UI reason  
5. **P1** Profile/Today/Progress target labeling (goal vs plan vs consumed)  
6. **P1** Theme System/Light/Dark; Metric/Imperial presentation; weight-rate policy alignment  
7. **P1** Promotions: remove or honest “estimate-only” (no fake store discounts)  
8. **P2** Features A–H (selected day, week summary, completion sync, quick add, remaining, empty states, PTR, last updated)  
9. **P2** Notifications foundation (prefs + local abstraction, no FCM required)  
10. Docs: `state-management.md`, `phase-18-report.md`; tests; APK; phone smoke  

---

## 13. Explicit non-goals (unchanged)

Payments, social, camera, wearables, real SMTP, K8s, visual redesign, microservices rewrite.

---

## 14. Audit conclusion

Phase 17 productization APIs largely exist, but the **client state model is fragmented**. User-facing failures (delete 422, “export did nothing”, Today/Week disagreement, fake settings, 429 on regen) are primarily **contract + SSOT + invalidation + honest settings** problems, not missing week persistence on the server.

**Next step:** implement in the order above; do not patch individual screens with ad-hoc `refresh()` without shared repository events.
