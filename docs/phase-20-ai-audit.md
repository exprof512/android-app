# Phase 20 — AI audit (pre-implementation)

Status: **baseline for Phase 20**. Do not rewrite working TextAI/Image stacks without need.

## 1. Existing AI operations

| Operation | Entry | Consumer | Structured? |
|---|---|---|---|
| `generate_recipe_candidates` | [`TextAIService.generate_recipe_candidates`](../backend/app/ai/service.py) | Meal plan / catalog paths | Yes — `RecipeCandidatesResponse` |
| `generate_meal_plan_proposal` | `generate_meal_plan_proposal` | [`MealPlanService.generate`](../backend/app/meal_plans/service.py) | Yes — `MealPlanProposalResponse` |
| `replace_meal_item` | `replace_meal_item` | `MealPlanService.replace_item` | Yes — `ReplaceMealResponse` |
| `chat_answer` | `chat_answer` | [`ChatService.post_message`](../backend/app/chat/service.py) | Yes — `ChatAnswerResponse` |
| Image generate | `ImageGenerationService.enqueue_for_recipe` | Meal plan create / lazy GET image | N/A (image bytes) |

Catalog fallback ([`fallback_plans.py`](../backend/app/ai/fallback_plans.py)) bypasses live AI when quota/provider fails.

## 2. Structured output

- OpenAI Responses + JSON schema via [`json_schema_for` / `OPERATION_SCHEMAS`](../backend/app/ai/schemas.py).
- `OPENAI_RESPONSE_SCHEMA_VERSION` in settings; cache fingerprint includes schema version.
- Repair loop: parse/`ValidationError` → one bounded retry with feedback (`OPENAI_TEXT_MAX_ATTEMPTS`, default 2).

## 3. Where AI can influence nutrition

AI **must not** own final macros/calories/cost. Current path:

1. AI returns ingredients + quantities (candidate).
2. [`RecipeEngine.canonicalize`](../backend/app/recipes/engine.py) maps names → catalog.
3. Nutrition/cost from ingredient `*_per_100g` × grams.
4. [`MealPlanEngine`](../backend/app/meal_plans/engine.py) checks day targets / constraints.

**Risk:** if AI invents ingredients that soft-match wrong catalog rows, nutrition is wrong but still “engine-calculated”. Strict `allowed_ingredients` + unknown-ingredient rejection mitigate this.

AI fields that look nutritional in prompts are explicitly **non-authoritative**; backend overwrites.

## 4. Missing validation (Phase 20 gaps)

| Gap | Notes |
|---|---|
| No unified `AIResponseValidator` stages | Validation scattered in RecipeEngine / MealPlanEngine |
| No diversity / recent-recipe exclusion as shared post-validator | Partial via plan engine only |
| No dedicated recommend / adapt-day / substitute / variant ops | Only plan / replace / chat |
| Chat actions limited | `replace_meal_item`, `open_shopping_list`, `explain_balance`, `none` — no pantry/cheap/fast intents |
| Prompt versions not versioned constants | Hardcoded strings in [`prompts.py`](../backend/app/ai/prompts.py) |
| Context not centralized | Meal plan and chat each build ad-hoc dicts |
| Cache fingerprint lacks nutrition policy / prompt version | Only operation + model + schema + payload |
| Recommendation quotas | Entitlements cover plan/replace/chat/image — not “suggestion” operations |
| No golden AI fixtures dir | Tests mock provider inline |

## 5. Existing context

**Chat** ([`ChatService._build_context`](../backend/app/chat/service.py)): locale, active goal calorie target, today balance remaining, plan summary, restrictions, preferences, bounded recent messages. No email/JWT/secrets.

**Meal plan generate/replace**: profile goal, meals/day, budget, cook time, pantry, restrictions, preferences, `allowed_ingredients`, remaining day balance (replace), notes/reason.

No single `AIContextBuilder`.

## 6. Cache

- Redis / memory: [`TextAICache`](../backend/app/ai/cache.py).
- Key: `ai:text:v{schema_version}:{sha256(operation,model,schema,payload)}`.
- TTL: `AI_CACHE_TTL_SECONDS`.
- Cache hit recorded in `ai_text_usage` with status `cached` (service path).
- Replace/chat typically `use_cache=False`.

## 7. Quota

[`EntitlementsService.consume`](../backend/app/entitlements/service.py):

- `meal_plan_generate` (Free daily, raised in Phase 18)
- `meal_plan_replace`
- `chat_message`
- `image_regenerate` (Premium-only)

Atomic check before paid call. Idempotency-Key on replace (Phase 17/18).

## 8. Usage / cost

`ai_text_usage`: user_id, conversation_id, operation, model, tokens, estimated_cost, status, duration_ms, error_code, request_fingerprint, schema_version. **No prompts.**

`ai_image_usage`: image pipeline (reused status exists; name-based reuse added post–Phase 19).

Admin aggregates: `/admin/ai/*`.

## 9. Chat architecture

- Conversations + messages in Postgres (`ai_conversations`, `ai_messages`).
- API: create conversation, get, post message.
- Assistant may return `suggested_actions[]`; Android must call separate mutation APIs (principle already documented).
- Medical/diagnosis → safe refusal in prompt.

## 10. Prompts

[`backend/app/ai/prompts.py`](../backend/app/ai/prompts.py) — four operations + shared `BASE_SAFETY`. **No `*_PROMPT_VERSION` constants yet.**

## 11. Model configuration

From settings / `.env`:

- `OPENAI_API_KEY`, `OPENAI_TEXT_MODEL`, timeouts, max attempts, schema version
- `OPENAI_IMAGE_MODEL` (currently `gpt-image-2` for experiment)
- DeepSeek optional fallback
- Chain: OpenAI → DeepSeek → catalog fallback ([`dependencies.py`](../backend/app/ai/dependencies.py))

## 12. Existing tests

- `tests/test_text_ai_service.py` — schema/cache/usage/mock
- `tests/test_text_ai_fallback.py` — provider fallback
- `tests/test_openai_error_classify.py`, `test_openai_image_params.py`
- Meal plan / chat / recipe tests elsewhere (engine validation, ownership)
- **Missing:** `tests/fixtures/ai/` golden suite, dedicated validator matrix for Phase 20 cases

## Phase 20 mapping (reuse vs new)

| Phase 20 need | Reuse | New |
|---|---|---|
| AIContextBuilder | Chat/meal context fragments | Unified builder + schema version |
| Prompt/context versioning | schema_version | Prompt version constants + cache fields |
| Adaptive Today / adapt day | replace + recipe candidates | New ops + endpoints + confirm UX |
| Ingredient substitution / variants / pantry / budget / cook-time | RecipeEngine + replace | New structured ops + intents |
| Chat 2.0 actions | suggested_actions | Expand action taxonomy + execute path |
| Preference memory | `food_preferences` / restrictions | Confirm-to-save flow; optional cuisine prefs |
| AIResponseValidator | Recipe/MealPlan engines | Shared staged validator + error codes |
| Evaluation suite | MockTextProvider | Golden fixtures |
| Usage UI | entitlements/me | Android surface + recommendation feature keys |

## Non-goals reminder

No autonomous mutations, no raw long-term chat memory, no medical diagnosis, no billing, no FCM/camera/barcode.
