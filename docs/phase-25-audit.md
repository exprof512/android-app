# Phase 25 — Full Technical Audit

**Date:** 2026-09-24  
**Mode:** audit only. No architecture rewrite, no API/DB/UX changes, no new features.  
**Code:** `main` at `ea50cbe` (Phase 24A navigation + Phase 23 verification docs).

## Executive Summary

The product loop works and the Phase 23 invariants still hold: planned food is not consumed until «Съел», Progress uses `compute_day_consumed`, replace and photo-confirm have stable idempotency keys, continuity does not charge the free meal-plan quota, text AI is DeepSeek, vision and recipe images are OpenAI.

This pass did not find a P0 (data loss, auth bypass, or a nutrition formula that double-counts on a single screen). It did find issues that can show the wrong plan or stale screens, and a real cost hole on food photos.

Confirmed in the running database (aggregates only, no user rows):

- **3 pairs** of overlapping `ready` meal plans for the same user and dates. Today’s plan picker orders by `created_at`; Progress and AI context order by `updated_at`. Those screens can attach to different plans.
- **16** `recipe_images` rows stuck in `pending` for more than one hour. `ai_image_usage` has no `failed` rows (107 ready, 16 pending, 2 reused).
- **0** `food_photo_analysis` rows with status `failed`. Two `ok` rows. Nginx shows one authenticated phone `POST /api/v1/nutrition/photo/analyze` on 2026-09-24 12:13:56 UTC that returned **200** (264 bytes). There is no server log of «Не удалось распознать фото» in the current containers. The string is a catch-all for any vision exception, not a diagnosed provider failure.

Do not re-open Phase 23 fixes (B23-01…B23-13, B23-15, B23-16, B23-24, B23-26) or the Phase 24A navigation change. B23-14 (timezone) and the deferred P2/P3 items in `docs/phase-23-verification.md` are still open and are listed again only as carry-forward.

## Project Architecture

Android (Kotlin, Compose, MVVM, Hilt, Retrofit, OkHttp, Kotlinx Serialization, Coil) talks only to FastAPI through Nginx. PostgreSQL is the source of truth. Redis is cache, rate limit, and Arq. MinIO stores recipe image bytes. The client keeps in-memory snapshots (`MealPlanRepository`, `ProfileRepository`) and a process-wide `AppStateBus`. There is no Room cache of plans or diary logs despite `docs/architecture.md` mentioning Room for UI cache.

`docs/architecture.md` is stale on AI routing: it still says product text uses OpenAI Responses. Production DI uses DeepSeek for text (`build_text_provider`) and OpenAI only for vision and image generation. `docs/ai-provider-routing.md` matches the code.

Main user flow and where state lives:

| Step | Backend owner | Android owner | Refresh |
| --- | --- | --- | --- |
| Onboarding / profile / goal | `ProfileService`, `NutritionEngine` | `ProfileRepository`, onboarding draft prefs | `ProfileChanged` |
| Weekly plan | `MealPlanService.generate` / `find_covering` | `WeekViewModel` + `MealPlanRepository.weekPlan` | `PlanChanged` |
| Today | `GET /meal-plans/today` `day_progress` | `TodayViewModel` | bus + generation guard |
| Eat / skip / replace | `complete_item` / `skip_item` / `replace_item` | `MealPlanRepository` | bus; cache refresh uses `LocalDate.now()` |
| Diary | `NutritionLog` rows | `DiaryViewModel` sums `GET /nutrition/logs` | `NutritionLogChanged` + generation guard |
| Progress | `compute_day_consumed` | `ProgressViewModel` | bus, no generation guard |
| Next day / next week | `ensure_current_day_plan`, `_maybe_prepare_next_week` | Today open | continuity does not charge generate quota |
| AI | recommendations, chat, photo | `AiHubSheet` → Today or chat | several apply paths skip the bus |

## Android Audit

State is split across Hilt ViewModels and singleton repositories. `SelectedDateStore` and `AppStateBus` are in-memory only (`MutableStateFlow` / `MutableSharedFlow`, extra buffer 64, `tryEmit`). Process death resets the selected date to today and drops `pendingAiAction` (`remember` in `MainShell`, not saveable).

Phase 23 refresh-generation guards exist on Today and Diary only. Week and Progress can finish an older request after a newer one.

### P25-AND-001

ID: P25-AND-001  
Severity: P1  
Area: Android sync / AI

File: `android/app/src/main/java/com/foodai/app/feature/chat/ChatScreen.kt`  
Line: 282–304 (`confirmAiRecommendation`), 307–335 (`confirmAdaptDay`), 345+ (`confirmVariant`)

Problem: Chat applies AI actions (`create_nutrition_log`, `replace_meal_item`) and never emits `NutritionLogChanged` or `PlanChanged`.

Why it happens: `ChatViewModel` has no `AppStateBus`.

Root cause: AI apply was added beside the repository mutation path that does emit events.

Impact: After confirming food or an adapted day in chat, Diary, Today, Progress, and the week plan stay on the previous snapshot until something else refreshes them.

Reproduction: Confirm a chat recommendation that creates a nutrition log, then open Diary without pulling another mutation.

Current behavior: Chat shows «Добавлено»; other screens do not reload.

Expected behavior: The same bus events as `TodayViewModel.addFood` / `MealPlanRepository.replaceItem`.

Recommended fix: Emit `NutritionLogChanged` and, for plan replaces, `PlanChanged` after a successful apply. Do this in one place, not a second copy in the chat screen.

Risk of fix: Low. Extra refreshes only.

Tests required: ViewModel or repository test that a successful chat apply emits the domain event.

### P25-AND-002

ID: P25-AND-002  
Severity: P1  
Area: Android sync / Today AI

File: `android/app/src/main/java/com/foodai/app/feature/plan/PlanViewModels.kt`  
Line: 486–511

Problem: `TodayViewModel.confirmAiRecommendation()` calls `refresh()` on Today and does not emit `NutritionLogChanged`. `addFood` at lines 315–316 does emit it.

Why it happens: The AI confirm path refreshes only its own ViewModel.

Root cause: Same split as P25-AND-001.

Impact: Diary and Progress stay stale after «Что съесть?» is confirmed on Today. Today itself updates because `refresh()` loads logs and `day_progress`.

Reproduction: Confirm a Today AI recommendation, open Diary.

Current behavior: Today info message and local refresh. Diary totals unchanged until another event.

Expected behavior: `bus.emit(NutritionLogChanged(selectedDate))`.

Recommended fix: Emit the event after a successful apply, then refresh.

Risk of fix: Low.

Tests required: Confirm path emits `NutritionLogChanged` for the selected date.

### P25-AND-003

ID: P25-AND-003  
Severity: P1  
Area: Android plan cache / selected date

File: `android/app/src/main/java/com/foodai/app/core/mealplan/MealPlanRepository.kt`  
Line: 142, 148–152, 156–159

Problem: After replace, complete, and skip, the repository refreshes the singleton cache with `LocalDate.now()`, not `SelectedDateStore`.

Why it happens: The repository does not know the date the user is looking at.

Root cause: `refreshToday` / `refreshAll` default to the device clock.

Impact: Completing or replacing a meal on a non-today date updates the server, then reloads **today** into `todayPlan`. Today’s screen usually refreshes itself with the selected date afterwards, so the visible screen can recover, but any reader of the singleton snapshot (shopping, chat `mealPlans.today()`, a later bus refresh) can see the wrong day until that refresh lands.

Reproduction: Select yesterday on Today, mark a meal eaten, inspect `MealPlanRepository.todayPlan` before Today’s own refresh returns.

Current behavior: Cache anchor is the device date.

Expected behavior: Refresh the date of the mutated item.

Recommended fix: Pass the item’s `planned_date` into `refreshToday`.

Risk of fix: Low if every caller passes the date. Medium if some callers forget and fall back to now.

Tests required: Complete an item whose date is not today; assert the refreshed snapshot date.

### P25-AND-004

ID: P25-AND-004  
Severity: P2  
Area: Android concurrency

File: `android/app/src/main/java/com/foodai/app/feature/progress/ProgressViewModel.kt` lines 57–77; `PlanViewModels.kt` `WeekViewModel.refresh` around 633–695

Problem: Progress and Week refresh coroutines are not cancelled and have no generation counter. Today and Diary do.

Why it happens: Phase 23 added guards only where the races were reproduced.

Impact: A slow summary for “week” can overwrite a faster “month” response, or an older week payload can replace a newer one after `PlanChanged`.

Reproduction: Toggle Progress period quickly, or fire two `PlanChanged` events while a week request is in flight. Not reproduced on a device in this pass.

Current behavior: Last coroutine to finish wins, not the last request started.

Expected behavior: Ignore stale generations, as Diary does.

Recommended fix: Copy the Diary `refreshGeneration` pattern.

Risk of fix: Low.

Tests required: Two overlapping refreshes; only the later generation is shown.

### P25-AND-005

ID: P25-AND-005  
Severity: P2  
Area: Android performance

File: `PlanViewModels.kt` Today `refresh` (profile + water + plan + `listLogs` on every bus event); `PlanScreens.kt` unused `DiaryLogRow` (~551–575); `DiaryScreen.kt` `onSaved` plus bus refresh

Problem: Today fetches nutrition logs on every refresh and does not render them. Diary save refreshes twice (bus and explicit `refresh()`).

Why it happens: Diary became its own screen in Phase 24A; the Today fetch was left in place.

Impact: Extra `GET /nutrition/logs` and `GET /profile` on startup and after every eat/water/plan event.

Recommended fix: Stop loading logs inside Today unless a widget needs them. Let Diary rely on the bus **or** the explicit refresh, not both.

Risk of fix: Medium if some Today number still depends on the local log list. Check `fromDiary` comes from `day_progress` (it does) before deleting the fetch.

Tests required: Today refresh test asserts the nutrition list endpoint is not called.

Other Android notes (not new bugs):

- Eat / skip / replace from the plan repository **do** emit `PlanChanged` and, for complete, `NutritionLogChanged`. Those three screens stay aligned when the user uses the meal buttons. `complete_item` is not a toggle: the client sends `completed=true`, and the server upserts one diary row.
- `pendingAiAction` is cleared when the effect starts, not when the AI call finishes, and it is not saveable. Process death drops an in-flight hub action. P3.
- Diary is pushed with `navigate` and no `launchSingleTop`, and it has no up button. Repeat opens can stack. P3.
- `clearMessages()` on Today is never called from the UI, so an error line stays until the next mutation. P3.
- Profile water label does not subscribe to `WaterChanged`. P3.
- `confirmAdaptDay` applies replacements one by one. A failure in the middle leaves a partial day and still may not emit `PlanChanged` (chat). Today does `refresh()` only if the whole loop succeeds. P2, same family as P25-AND-001.

## Backend Audit

Routers under `/api/v1`: auth, users, profile, recipes, meal-plans, images, shopping, progress, chat, ai, entitlements, nutrition, analytics, admin AI, water. Errors are mostly `ApiError` `{error: {code, message, request_id}}`. A few handlers still raise raw `HTTPException` (progress 422), so the message can be English `http_error` instead of the domain message.

Authorization on plan items, diary rows, chat conversations, and media downloads checks `user_id`. No new IDOR on those resources. Two weaker spots are below (recipe UUID used as an AI/diary input without the dish-card gate).

### P25-BE-001

ID: P25-BE-001  
Severity: P1  
Area: Plan selection

File: `backend/app/meal_plans/repository.py` line 49 (`order_by(MealPlan.created_at.desc())` in `find_covering`); `backend/app/nutrition/day_balance.py` line 54 (`order_by(MealPlan.updated_at.desc())`); `backend/app/ai/context.py` uses the same `updated_at` order. Overlap archive is only on `force=True`: `backend/app/meal_plans/service.py` lines 121–128 and 854–868. `MealPlan` has a unique hash, not a unique covered date (`backend/app/meal_plans/models.py`).

Problem: More than one `ready` plan can cover the same calendar day. Callers do not agree which one is active.

Why it happens: `generate(force=false)` returns an existing hash or inserts another ready plan. It does not archive other ready plans whose dates overlap. Continuity uses `force=false`.

Root cause: No single “active plan for date” rule in the database.

Impact: Today (`find_covering` / `created_at`) and Progress (`compute_day_consumed` / `updated_at`) can score different plans. Targets, completed meals, and remaining calories diverge. Confirmed in this environment: **3 overlapping ready pairs** (8 ready plans, 8 archived).

Reproduction: Two ready plans for one user with overlapping `start_date`/`end_date`. Open Today and Progress for a date inside both ranges.

Current behavior: Each query picks its own row.

Expected behavior: One ready plan covers a given user and date, and every reader uses that row.

Recommended fix: One helper, one `ORDER BY`. On generate, archive other ready plans that overlap the new window (including `force=false` when a new hash is inserted). Add a constraint only after existing overlaps are archived. Do not change the nutrition formula.

Risk of fix: Medium. Archiving the “wrong” plan hides meals the user already completed on that plan. The migration must pick the plan that owns completed items, not merely the newest timestamp.

Tests required: Two overlapping ready plans; Today, Progress, and AI context return the same `plan_id`. Generate does not leave a second ready overlap.

### P25-BE-002

ID: P25-BE-002  
Severity: P1  
Area: AI cost / photo

File: `backend/app/nutrition/photo.py` lines 139–160

Problem: OpenAI vision runs before the food-photo entitlement check. `consume` happens only after a successful response (Phase 23, intentional for failures). There is no pre-check, and `POST /nutrition/photo/analyze` has no idempotency key.

Why it happens: Quota was moved after the provider call so failures would not burn the user’s daily count. The provider call itself was left unguarded.

Root cause: User quota and provider cost are different limits, and only the user quota is enforced, and only after success.

Impact: Failed analyzes are unlimited against OpenAI. A user who is already at the daily limit still pays for a successful vision call; `consume` then raises and the client shows an error. A double tap after success analyzes twice and charges twice. Confirm is idempotent; analyze is not.

Reproduction: Exhaust `FEATURE_FOOD_PHOTO`, send another photo. Or send two analyze requests in parallel.

Current behavior: Vision is invoked, then quota is applied.

Expected behavior: Reject with `usage_limit_exceeded` before the provider call. Retry of the same photo returns the stored analysis.

Recommended fix: Check remaining quota first. Keep charging only on success. Store the analyze response under an idempotency key the same way confirm does.

Risk of fix: Low for the pre-check. Medium for idempotency if the key is unstable (the Android confirm key is already stable; analyze needs the same treatment).

Tests required: At the limit, vision provider is not called. Two analyze calls with one key produce one usage row.

### P25-BE-003

ID: P25-BE-003  
Severity: P2  
Area: Plan generation

File: `backend/app/meal_plans/service.py` lines 131–146; `backend/app/recipes/service.py` commit inside recipe create; `service.py` `_maybe_prepare_next_week` around 329–357

Problem: User-initiated generate consumes `FEATURE_MEAL_PLAN_GENERATE` before the provider returns. Each AI recipe commits on its own. Next-week preparation swallows every exception.

Why it happens: Quota-before-work was left in place for generate/replace (called out in B23-08). Continuity correctly passes `charge_entitlement=False`.

Impact: A failed generate still spends the free daily slot, including when the text cache hits after consume. A failed plan insert can leave orphan recipes. If next-week prep fails, the user reaches day 8 with no plan and no error on the Today response.

Recommended fix: Consume after a successful plan commit, or refund on failure. One transaction for the generate path. Put a warning on `MealPlanOut` when next-week prep fails instead of only a log line.

Risk of fix: Medium around entitlement refunds and transaction boundaries. Do not change continuity’s `charge_entitlement=False`.

Tests required: Provider failure does not increment the daily counter. Exception in `_maybe_prepare_next_week` is visible as a warning, and a later Today open still generates once.

### P25-BE-004

ID: P25-BE-004  
Severity: P2  
Area: Authorization (low sensitivity)

File: `backend/app/nutrition/diary.py` recipe source create; `backend/app/nutrition/api.py` template apply (~532–540); `backend/app/ai/recommendations.py` substitution/variant (~345, ~423)

Problem: Logging or adapting a recipe by UUID does not go through the dish-card access check. Recipes are a shared catalog, not private user documents.

Why it happens: Catalog recipes are globally readable by search already.

Impact: Any authenticated user can attach a ready catalog recipe to their diary or spend AI quota on its id. This is not access to another user’s diary or plan.

Recommended fix: Reuse the same visibility rule as dish card if some recipes are meant to be private. If the catalog is public, document that and still rate-limit AI operations on arbitrary ids.

Risk of fix: Low if the catalog is public. Higher if private recipes exist and are currently only hidden in the UI.

Tests required: A recipe that fails dish-card access cannot be logged via template apply.

## Database Audit

Models, FKs, and the unique indexes added in earlier phases are in place: `nutrition_logs.meal_plan_item_id` unique, meal-plan generation hash unique, refresh-token hash, shopping item uniqueness. User delete cascades plans and logs. `goals` is `ON DELETE RESTRICT` from plans, so a goal cannot be removed while plans point at it.

Gaps:

- No exclusion constraint for one ready plan per user per day (P25-BE-001). Live data already has 3 overlapping ready pairs.
- `nutrition_logs.meal_plan_item_id` is `ON DELETE SET NULL`. Deleting a plan keeps the diary rows, which is reasonable for history, but those rows remain in diary sums after the plan is gone. P3.
- `AiTextUsage.user_id` is nullable `SET NULL` after account delete. Usage history survives without the user. P3, privacy-relevant if exports or admin views are widened later.
- Entitlement consume still has no `SELECT … FOR UPDATE` (B23-23, deferred). Parallel consume can overshoot a limit. P2 carry-forward.
- 16 recipe images have been `pending` for over an hour while the worker container is healthy. No failed image-usage rows. Likely jobs were never queued or were lost on restart. P2.

ID: P25-DB-001  
Severity: P2  
Area: Images

File: `recipe_images.generation_status`; worker `backend/app/images/generator.py`

Problem: 16 images older than one hour are still `pending`.

Why it happens: Not fully traced in this pass. `ai_image_usage` shows ready/pending/reused and zero `failed`, so this is not a recorded provider failure.

Impact: Plan and recipe screens keep placeholders for those dishes.

Recommended fix: A sweep that re-enqueues `pending` rows older than N minutes, with a retry cap. Do not regenerate `ready` images.

Risk of fix: Medium if the sweep double-charges OpenAI. Fingerprint reuse must stay on.

Tests required: A pending row older than the threshold is enqueued once.

## API Audit

| Area | Method / path | Auth | Idempotency | Notes |
| --- | --- | --- | --- | --- |
| Auth | register, login, refresh, logout | public / bearer | refresh rotation | Phase 23 session epoch on the client |
| Profile / goals | `/profile` | bearer | last write wins | timezone stored, unused (B23-14) |
| Plan | `POST /meal-plans/generate` | bearer | hash reuse when `force=false` | no client idempotency key; quota before success |
| Plan | `GET /meal-plans/today`, `/week` | bearer | read | may call continuity generate |
| Plan | complete / skip / replace | bearer | replace key only | complete/skip are upserts |
| Diary | `/nutrition/logs` | bearer | create has no key | list is unbounded (P3) |
| Diary | `/nutrition/diary/day` | bearer | read | sums logs; Android does not call it |
| Photo | `POST /nutrition/photo/analyze` | bearer | none | P25-BE-002 |
| Photo | `POST /nutrition/photo/confirm` | bearer | `Idempotency-Key` | quota not charged again |
| Progress | `/progress/summary` | bearer | read | `compute_day_consumed` per day, up to 90 queries (P2) |
| AI | recommendations, adapt, chat | bearer | execute key; suggest/adapt keys vary | quota before provider |
| Images | recipe image, media | bearer | fingerprint reuse | IDOR check on download |
| Shopping | list from plan | bearer | rebuild | follows week plan |
| Entitlements | `/entitlements/me` | bearer | consume | no row lock |

N+1: meal-plan `_to_out` loads a primary image per item (`meal_plans/service.py` ~948–960). AI context loads each recipe in a loop (`ai/context.py` ~237). Progress walks days and calls `compute_day_consumed` each time (`progress/service.py` ~144–181). These are P2 latency issues, not wrong numbers.

## Nutrition Engine Audit

### Source of truth

| Question | Authoritative code | What it counts |
| --- | --- | --- |
| Calorie target | `NutritionEngine` at goal time, copied onto `meal_plans.*_target_*` | Frozen plan snapshot. Progress falls back to `Goal` if no plan. |
| Consumed kcal, protein, fat, carbs for Today | `MealPlanService._build_day_progress` | Completed slots (`status == completed` or `is_completed`) plus diary logs whose `meal_plan_item_id` is not one of those slots |
| Same numbers for Progress | `nutrition/day_balance.py` `compute_day_consumed` | Same merge, duplicated rather than called |
| Diary screen | Android `DiaryViewModel` sums `GET /nutrition/logs` | Every log row, including the row created when a plan meal is eaten |
| Diary API `day_totals` / `history` | `nutrition/diary.py` 296–371 | Same sum of logs. Not used by the Android diary screen |
| Remaining on Today | `day_progress.remaining_*` | Target minus consumed. Android must not recompute when this is present (`docs/state-management.md`) |
| Planned but not eaten | `planned_remaining_kcal` | Uneaten slots only |
| AI “consumed today” | `ai/context.py` `_consumed_remaining` | Completed plan items only. Diary extras ignored. **B23-17, still deferred** |
| Replace context remaining | `meal_plans/service.py` ~445 | Completed plan items only, not diary. Same gap |
| Week strip | `_build_week_summary` | **Planned** kcal, not consumed. **B23-18, still deferred** |

Eat path: `complete_item` sets the slot completed and upserts **one** diary row with the slot macros. Today counts the slot and skips that log. Diary counts the log. The two numbers match when the log macros equal the slot macros. Phase 23 replace updates that log. This is **not** a 2× bug. A 2× total would require a screen to add the slot and the linked log. Neither Today, Progress, nor Diary does that.

They diverge when:

- the linked log’s macros differ from the slot (should not happen after the Phase 23 upsert);
- two ready plans overlap and the screens pick different plans (P25-BE-001);
- AI context ignores diary food (B23-17).

`_build_day_progress` still reimplements the merge instead of calling `compute_day_consumed`. That is drift risk (P2), not a current numeric split.

Rounding: Progress quantizes macros to 0.1; Today uses 0.01 (B23-25). Plan validation uses `float` servings; stored items use `Decimal`. P3.

Units: backend is metric only (kcal, g, kg, ml). No imperial conversion on the server.

Timezone: `date.today()` and UTC entitlement windows ignore `profile.timezone` (B23-14). Android usually sends `date=`, so the bug shows up when a caller omits the date near local midnight. Entitlement reset is UTC, not the user’s midnight. P1 carry-forward. Do not change it inside a drive-by; it changes “today” for plans, water, diary, and quotas together.

## Plan Engine Audit

Generation builds `days` (normally 7) times meals per day, validates with `MealPlanEngine` (diversity can hard-fail; calorie mismatch is a warning; budget is context for the model, not an engine check). Catalog fallback runs if the text provider fails, after the quota consume on user-initiated generate.

New day: `ensure_current_day_plan` returns `find_covering` when a ready plan covers the date. Otherwise one `generate(force=false)`. The hash unique index blocks a second stored plan. A concurrent first load can still call the text provider twice; only one plan is stored (known Phase 23 limitation).

End of week: `_maybe_prepare_next_week` looks for a covering plan on the next start date and generates with `charge_entitlement=False`. Failures are logged and swallowed (P25-BE-003). There is no separate “week completed” state; the next window is just another plan.

Empty “no menu” on a new day happens if covering lookup misses (overlap/status) or both generate and fallback fail. It is not the steady state when a plan already covers the date.

## Diary Audit

Add food (photo, search, recent, quick calories, meal type) lives in `AddFoodSheet`, opened from Diary. `loggedOn` is `SelectedDateStore` (B23-07). Photo confirm uses a stable key (B23-01). Delete of a plan-linked log sets the slot back to planned (B23-04). A second log for the same plan item returns 422 (B23-05).

Diary has no local cache. Offline, the list is an error pane. Today can still show the last plan snapshot.

Quick calories and unmatched photo foods can be saved without an allergy check. Recipe and plan generation do check restrictions. Photo confirm trusts client `ingredient_id` and catalog macros (AI is not the macro source of truth) but does not reject an allergen. P2: warn or reject on confirm when the ingredient matches `food_restrictions`. Manual entry is intentionally free-text.

There is no edit endpoint in the diary UI beyond delete and duplicate. Duplicate clears `meal_plan_item_id`, so the copy counts as extra food. That is intended.

## AI Audit

| Operation | Provider | Model (config) | Entitlement | Cache | Retry / charge |
| --- | --- | --- | --- | --- | --- |
| Meal plan proposal | DeepSeek | `DEEPSEEK_TEXT_MODEL` | `meal_plan_generate` if `charge_entitlement` | hash reuse before consume; text cache after | repair attempts each write usage (B23-22); user quota consumed before success |
| Continuity / next week | DeepSeek | same | not charged | hash | same provider cost, no user quota |
| Replace meal | DeepSeek | same | `meal_plan_replace` | idempotency before consume; `use_cache=False` | quota before success |
| Chat | DeepSeek | same | `chat_message` | off | quota before success; fallback answer still counts |
| What to eat | DeepSeek | same | `ai_recommendation` | text cache on | quota before success |
| Adapt day | DeepSeek | same | `ai_recommendation` | off | quota even when no meals remain |
| Substitution / variant | DeepSeek | same | `ai_recommendation` | per call | any catalog recipe id |
| Photo analyze | OpenAI vision | `gpt-4.1-mini` (this environment) | `food_photo_analysis` after success | none | no vision retry; failures do not charge the user; they do call OpenAI |
| Photo confirm | none | — | none | idempotency | — |
| Recipe image | OpenAI Images | image model | none for lazy enqueue; `image_regenerate` for manual | fingerprint | platform cost; 16 jobs stuck pending |

`build_text_provider` does not return `OpenAIResponsesProvider`. `FallbackTextProvider` is not in production DI. Vision and images are OpenAI. If `OPENAI_API_KEY` is empty outside tests, `build_vision_provider` returns a mock (P2 in production misconfig). This environment has both keys set (`app_env=development`); the mock path is not active here.

Text results go through schema validation and `MealPlanEngine` / `RecipeEngine`. Photo macros come from `nutrition_for_grams` after name match, not from the model. The vision prompt tells the model not to emit macros.

AI context is not the nutrition source of truth for stored totals, but it **is** what the model sees. It omits diary intake (B23-17), so “what to eat” can ignore food the user already logged.

Empty DeepSeek key uses a mock text provider in non-test environments. Same fail-open pattern as vision. P2 for a production deploy with a missing key.

## Vision/Image Audit

Pipeline:

1. Diary → `AddFoodViewModel.analyzePhoto` reads the gallery URI, downscales above ~900 KB to JPEG ≤1600 px.
2. `POST /api/v1/nutrition/photo/analyze` multipart field `file`.
3. Nginx `client_max_body_size 8m`. Backend rejects MIME other than JPEG/PNG/WebP, payload &lt; 64 bytes, and payload &gt; 5 MB, then PIL-downscales the long edge.
4. `OpenAIVisionProvider.analyze_food` sends a base64 data URL. Timeout 60s. One attempt. Invalid JSON becomes `TextAIUnavailable`.
5. Names are matched to the ingredient catalog. Unmatched or confidence &lt; 0.5 sets `needs_manual_review` and still returns **200**.
6. Confirm writes diary rows from catalog macros.

User-facing «Не удалось распознать фото» is only the `else` branch in `AddFoodViewModel.analyzePhoto` (line 273) when the server message is blank, and the server message itself from `photo.py` lines 151–153 when **any** exception escapes vision (timeout, HTTP error, bad JSON). Size and MIME have their own Russian strings. A low-confidence success does **not** use this string; it opens the review step.

### What the logs show

| Evidence | Result |
| --- | --- |
| `ai_text_usage` where `operation = food_photo_analysis` | 2 rows, both `ok`, no error code |
| Nginx `POST /api/v1/nutrition/photo/analyze` | 401 from curl (11:49 UTC); **200** from okhttp (12:13:52–12:13:56 UTC, 264-byte body). No 4xx/5xx from the phone in the retained nginx log |
| Backend container logs | Current process only has health checks. The 12:13 request was before this container start, so the application log line is gone |
| Keys | OpenAI and DeepSeek keys are set. Vision model `gpt-4.1-mini`, max 5_242_880 bytes, timeout 60s |

Root cause of a specific «Не удалось распознать фото» session: **not established**. Nothing in the retained logs failed. The code path that shows that sentence is “vision raised”. The phone request we can see succeeded at HTTP level. A 264-byte 200 is a small JSON body (few or no matched foods) and would open review, not the failure string.

If the failure is still seen on a phone, capture `request_id` and the `error.code` (`ai_generation_unavailable`, timeout, `image_too_large`, `unsupported_image_type`). HEIC from the camera is still unsupported (B23-21); gallery JPEG/PNG/WebP is the supported path. The in-app picker is the gallery, not a camera capture.

## Auth & Security Audit

JWT access plus rotating refresh hashes, logout revokes the server token, and the Android `sessionEpoch` stops a refresh from restoring a logged-out session (B23-11). Account deletion requires `confirmation=DELETE` and then the old token fails (Phase 18/23 tests). Export includes water entries (B23-16).

No `.env` is committed. `.env.example` has empty keys. Logging redacts bearer tokens and key-like fields (`backend/app/core/logging.py`). AI context tests assert email and API keys are not sent to the model.

IDOR: plan item, diary log, chat conversation, and media download check ownership. Recipe search is the shared catalog.

Rate limit fails open when Redis errors (`backend/app/core/rate_limit.py`). P2 for auth endpoints if Redis is down.

Photo confirm does not check allergies (see Diary). That is a product safety gap, not an IDOR.

Secrets were not printed in this audit. Key presence was checked as a boolean only.

## Performance Audit

Android: `PlanScreens.kt` is about 1,150 lines and `ChatScreen.kt` holds the chat ViewModel. Today refresh refetches profile and logs on every event (P25-AND-005). Coil loads a thumbnail per meal row; the disk cache limits repeat network use. No measured startup trace in this pass.

Backend: per-day progress queries, per-item image lookups, and per-item recipe loads in AI context. Plan generate is synchronous on the request, including continuity on Today open (catalog fallback limits the worst case; a cold generate is still a long request). Next-week prep on the request path is the backlog item “move to Arq”; not done.

Images: 16 pending rows older than an hour (P25-DB-001).

## Error Handling

Backend domain errors use a stable `code` plus a Russian `message` for nutrition and plans. Validation fallback and unhandled 500s are English (`Request validation failed.`, `internal_error`). Android `ApiErrorParser` maps network, 401, 413, 429, and the envelope `message`. It does not read `Retry-After`. `SessionViewModel` uses `error.message` instead of the parser, so session failures can be English or a raw exception string. P3.

Today can show `actionError` with no dismiss. Chat `open_shopping_list` sets an info string and does not navigate. P3.

Quota failures and AI failures are different codes. The client often shows one red line. That is acceptable if the message is the server `message`. It is not acceptable when the message is blank and the photo screen substitutes «Не удалось распознать фото» for every other failure (parser bug risk if `toUiMessage()` is empty on a network error). Worth checking on device: airplane mode during photo should say the network string, not the vision string. Code uses `toUiMessage().ifBlank { vision string }`, so a non-blank network message wins. Good.

## Offline

| Data | Offline |
| --- | --- |
| Meal plan | Last successful snapshot in `MealPlanRepository`; Today shows an offline banner |
| Diary logs | No cache. Error pane |
| Progress | No cache |
| Water | Preferences mirror can update on `ApiException` and drift from the server (B23-19 / B23-20 still deferred) |
| Profile | Memory cache |
| AI, photo, generate | Require the backend |

This is not offline-first. Mutations need the network. Reads of the current plan can survive one failed refresh.

## Navigation

Bottom bar after Phase 24A: Сегодня, План, AI, Прогресс, Профиль. Diary is not a tab. AI opens `AiHubSheet`. Add Food opens only from Diary.

| From | Back / state |
| --- | --- |
| Today → Diary | Bottom bar stays. System back pops Diary. No in-screen up control. `launchSingleTop` is not set |
| AI hub → Today action | `pendingAiAction` then Home. Lost on process death |
| AI hub → chat / shopping | Those routes hide the bottom bar. Shopping has its own back |
| Recipe | Bottom bar hidden. Item id is a query param |
| Add Food sheet | `remember`, not saveable. Process death closes it and drops the draft |
| Selected date | Shared in memory across Today, Plan, Diary, Add Food. Process death resets to today |

No duplicate Add Food in the bar. Today still has unused `addFood` / `deleteFood` on the ViewModel (dead after Phase 24A). P3 cleanup, not a user-facing duplicate.

## UI Architecture

Design tokens exist (`FoodAIColors`, `FoodAITypography`, `FoodAIDimens`, `FoodAIShapes`). Screens still mix raw `.dp` (~150 call sites) with tokens. Shared components: buttons, nav bar, recipe card, empty state, tip banner. Not worth a new library.

Later unification, not this phase:

- One meal row used by Today and Plan.
- One macro summary used by Today, Diary, and Progress.
- One error line with dismiss.
- Split `PlanScreens.kt` and move chat’s ViewModel out of the screen file.

Touch targets on the custom nav bar are the full slot (~72 dp tall). Labels are single-line. Contrast was not measured on a device.

## Localization

No `stringResource` usage under `android/app/src/main`. Copy is hardcoded Russian across onboarding, Today, Diary, chat, and profile. There is no English catalog and no plural rules. Units (ккал, г, кг, мл, ₽) are inline. Dates use `Locale("ru")` and `java.time`, which is correct for Russian month names and wrong for a future English UI.

This is P2 technical debt, not a functional bug, as long as the product language is Russian only.

## Test Coverage

Backend pytest covers auth, nutrition merge, plan continuity, photo quota-after-success, entitlements, AI routing, account delete, and export. It does **not** cover two overlapping ready plans, photo analyze-before-quota, or chat/Today bus events (those are Android).

Android unit tests cover auth token storage, `ApiErrorParser`, a few DTO fixtures, onboarding draft, display names, and the four nav labels. They do **not** cover ViewModels, eat/replace/delete, diary totals, photo analyze, AI apply, or `sessionEpoch` behavior beyond repository logout.

No Compose UI tests. No device smoke in this phase.

## Code Quality

No `TODO` / `FIXME` / `HACK` in the Android main tree. One `Log.d` in `AnalyticsTracker`. Dead leftovers: Today `addFood` / `deleteFood` wiring, `DiaryLogRow` in `PlanScreens.kt`. `docs/architecture.md` still describes OpenAI as the text provider.

Temporary choices that should stay visible:

- In-memory `SelectedDateStore` and `AppStateBus.tryEmit`.
- Quota consumed before text AI success (generate, replace, chat, recommendations).
- Mock providers when API keys are empty outside tests.
- Next-week errors swallowed.
- Profile timezone unused.

## Technical Debt

Carry-forward from Phase 23, not re-diagnosed here: B23-14 timezone (P1), B23-17 AI ignores diary (P2), B23-18 week chips are planned kcal (P2), B23-19 water undo not date-scoped (P2), B23-20 water prefs keyed by device today (P2), B23-21 default 100 g and no HEIC/camera (P2), B23-22 usage row per repair attempt (P2), B23-23 entitlement row lock (P2), B23-25 rounding (P3), B23-27 large ViewModels (P3).

Phase 24 backlog items (billing, camera, Arq next-week, gamification) are out of scope until the P1 sync and plan-selection issues are closed.

## Confirmed Bugs

| ID | Sev | One line |
| --- | --- | --- |
| P25-BE-001 | P1 | Overlapping ready plans; Today and Progress can pick different ones. 3 pairs in this database |
| P25-AND-001 | P1 | Chat AI apply does not invalidate Diary, Today, Plan, or Progress |
| P25-AND-002 | P1 | Today AI “add food” refreshes Today only |
| P25-AND-003 | P1 | Plan cache refresh after eat/replace/skip uses `LocalDate.now()` |
| P25-BE-002 | P1 | Vision runs before photo quota check; analyze is not idempotent |
| B23-14 | P1 | `profile.timezone` unused. Carry-forward |

P0: none.

## Potential Bugs

| ID | Sev | Note |
| --- | --- | --- |
| P25-AND-004 | P2 | Week and Progress refreshes can apply out of order. Not reproduced on a device |
| P25-BE-003 | P2 | Generate quota burned on failure; next-week errors swallowed; recipe commits are not one transaction |
| P25-DB-001 | P2 | 16 recipe images pending for over an hour. Cause not traced past the row status |
| P25-BE-004 | P2 | Catalog recipe id accepted by diary template apply and AI variant without the dish-card gate |
| Bus `tryEmit` | P2 | Buffer is 64. A burst could drop an event. Not observed |
| Vision mock | P2 | Empty OpenAI key in a non-test process serves mock vision. Not active in this environment |
| Photo allergies | P2 | Confirm does not check `food_restrictions` |
| Partial adapt | P2 | `confirmAdaptDay` can replace some slots and then fail |

## Architecture Risks

- Two consumption implementations (`compute_day_consumed` and `_build_day_progress`) will drift the first time only one is edited.
- Two plan pickers (`created_at` vs `updated_at`) already can. This is the highest structural risk.
- Cross-screen truth depends on every mutation remembering `AppStateBus`. Chat and Today AI confirm already forgot.
- AI text quota is a user counter, not a provider budget. Retries, cache hits after consume, and failed generates still cost money or a daily slot.
- `docs/architecture.md` will keep sending future work toward OpenAI for text unless it is corrected. Documentation only.

## Recommended Refactoring

Do this as Phase 25B, in this order, without new product features:

1. One active plan per user-day: shared selector, archive overlaps, test with the 3 existing pairs. Do not add the SQL constraint until the data is clean.
2. One mutation helper that writes the server change and emits `PlanChanged` / `NutritionLogChanged` / `ShoppingChanged`. Use it from meal buttons, Today AI, and chat.
3. Refresh plan caches with the mutated date, not `LocalDate.now()`.
4. Photo: quota check before vision; idempotency on analyze; keep charge-after-success.
5. Point `_build_day_progress` and AI `_consumed_remaining` at `compute_day_consumed` (closes the B23-17 half without a new formula).
6. Generation guards on Week and Progress.
7. Re-enqueue stale `pending` images once, with the existing fingerprint guard.
8. Timezone (`B23-14`) as its own change with a single `user_local_date`, not mixed into 1–7.

Explicitly not in 25B: billing, new AI modes, new screens, Room offline-first, string extraction of all Russian copy, splitting every large file.

## Priority Matrix

| Priority | IDs |
| --- | --- |
| P0 | — |
| P1 | P25-BE-001, P25-AND-001, P25-AND-002, P25-AND-003, P25-BE-002, B23-14 |
| P2 | P25-AND-004, P25-AND-005, P25-BE-003, P25-BE-004, P25-DB-001, B23-17, B23-18, B23-19, B23-20, B23-21, B23-22, B23-23, photo allergies, partial adapt, rate-limit fail-open |
| P3 | B23-25, B23-27, dead Today food APIs, diary back stack, saveable AI intent, English 500/validation strings, architecture.md text-provider paragraph, localization |

## Phase 25B Proposal

**Phase 25B — plan identity and screen sync.** No new features.

Scope:

- Fix P25-BE-001, P25-AND-001, P25-AND-002, P25-AND-003, P25-BE-002.
- Add regression tests for overlapping plans and for bus events after AI apply.
- Leave timezone, billing, and UI redesign out.

Done when Today, Diary, and Progress show the same consumed totals after eat, diary add, chat apply, and Today AI apply, including on a non-today selected date, and a second ready plan cannot cover the same day.

## Tests

| Suite | Result |
| --- | --- |
| Backend `python -m pytest -q --tb=line` | **PASS.** Exit 0. 246 tests, 0 failed, 0 skipped (72+72+72+30). No warnings in the pytest summary |
| Android `:app:testDebugUnitTest` | **PASS.** `BUILD SUCCESSFUL`. Task `UP-TO-DATE` (same sources as the Phase 24A green run) |
| Android `:app:assembleDebug` | **PASS.** `UP-TO-DATE` |

No code was changed in this phase, so the Android tasks correctly stayed up to date.

## Build

APK path after `assembleDebug`:

`/root/app-android/android-app/android/app/build/outputs/apk/debug/app-debug.apk`

## Physical smoke

NOT RUN — requires user device.

Suggested checks tied to this audit, not a general tour:

1. Eat a planned meal and compare Today, Diary, and Progress on that date.
2. Confirm «Что съесть?» on Today, then open Diary without restarting.
3. Confirm a chat suggestion that adds food, then open Today and Diary.
4. Open a past day, mark a meal eaten, leave and come back.
5. Photo from the gallery. If it fails, note the on-screen text and the time so `request_id` can be matched.
6. Dishes with a permanent placeholder: those are the pending image rows.

## Observed behavior left unchanged

| Topic | Observed | Possible intent | Recommendation |
| --- | --- | --- | --- |
| Diary totals vs Today | Diary sums logs; Today counts slots and skips the linked log | Same number when macros match | Keep. Do not “fix” a 2× that is not there. Add a test that they are equal after eat |
| Continuity quota | Auto day/week generate does not increment `meal_plan_generate` | Free users are not charged for opening the app | Keep |
| Photo quota | User quota increments only after vision success | Failures should not burn the daily photo count | Keep the charge-after-success rule; add a pre-check so OpenAI is not called when the user is already at the limit |
| Week chips | Planned kcal | Phase 23 deferred on purpose | Change only with a label, not a silent swap to consumed |
| Weight-loss pace / premium limits | Unchanged | Product policy | Do not retune in 25B |
