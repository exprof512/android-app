# PHASE 20 REPORT

## Status
**PARTIAL**

Adaptive AI backend + Android client landed with green unit/integration tests for the new surface. Physical device smoke is **NOT RUN** in this environment.

## AI Audit
See [phase-20-ai-audit.md](phase-20-ai-audit.md). Baseline: structured TextAI (plan/replace/chat) + Recipe/Nutrition engines; gaps closed with ContextBuilder, new ops, staged validator, golden fixtures.

## AI Context
`AIContextBuilder` (`backend/app/ai/context.py`) builds bounded, sanitized context (`AI_CONTEXT_SCHEMA_VERSION=v2`): goal/targets, remaining today, plan meals, preferences/restrictions/pantry names, recent recipes, cook time/budget. No email/JWT/secrets.

## AI Operations
Explicit ops: plan_generation, meal_replacement, recipe_generation, recipe_variant, ingredient_substitution, daily_adaptation, food_suggestion, shopping_optimization (stub path), chat. Prompt versions in `versions.py`.

## Adaptive Today
`POST /ai/recommendations` → 1–3 candidates with backend nutrition/cost after RecipeEngine. Android: «Что мне съесть?» with confirm-before-apply.

## Smart Replacement
Existing replace + Phase 19 reasons retained; variants/intents (more protein / cheaper / faster / pantry) via `POST /ai/recipe-variant`. Diversity vs recent recipes in validator.

## Pantry AI
Recommendation intent pantry / «Что приготовить из этого?» on Today; context includes available products.

## Budget AI
Variant `budget` / intent make_cheaper; cost from engine, displayed with ≈.

## Recipe Variants
`high_protein` | `budget` | `quick` | `pantry` on Recipe screen.

## Chat
Expanded `suggested_actions`; quick chips; actions require explicit tap → separate apply/mutate. Context via AIContextBuilder.

## Personalization
`remember_dislike` confirm flow; existing food_preferences domain.

## Validation
`AIResponseValidator`: ingredients, allergy/restriction, diversity, cook time, budget soft checks. Invalid candidates not persisted.

## Cache
Fingerprint includes context_version, prompt_version, nutrition_policy_version + operation/model/schema.

## Quota
`FEATURE_AI_RECOMMENDATION` (Free 15/day) + existing plan/replace/chat. Settings shows remaining when present.

## Cost
Existing `ai_text_usage` estimates; recommendation records without raw prompts.

## Evaluation Suite
`tests/fixtures/ai/*.json` + `tests/test_phase20_ai.py` (MockTextProvider).

## Security
Ownership on apply/execute; AI cannot mutate without authenticated action endpoint; no arbitrary tools/SQL.

## Privacy
Sanitized context; no raw prompt logging; analytics allowlist extended without PII properties.

## Backend
Migration `0015_ai_recommendation_records`. Routes under `/ai/*`.

## Database
`ai_recommendation_records` (operation/status/versions/model/recipe_id/error_code — no prompt/body).

## Android
Today recommend/adapt sheets, Recipe variant/substitute, Chat chips, Settings AI usage, `AiRecommendationRepository` + AppStateBus invalidation.

## Tests
```text
docker compose run --rm --no-deps -v "$PWD/backend:/app" backend \
  bash -lc "pip install -e '.[dev]' -q && python -m pytest tests/test_phase20_ai.py -q"
# RESULT: passed (see CI/local run)

cd android && ./gradlew :app:assembleDebug
# RESULT: BUILD SUCCESSFUL
# Phase20AiModelsTest green
```

## APK
`/root/app-android/android-app/android/app/build/outputs/apk/debug/app-debug.apk`  
`API_BASE_URL=http://193.32.179.108:8080/api/v1/`

## Physical Device
**NOT RUN** — install APK and run Phase 20 smoke checklist before PASS.

## Known Limitations
- Ingredient substitution is preview-only (no recipe-mutate apply).
- Adapt-day applies slots sequentially via replace (partial failure possible).
- Shopping optimization AI is minimal/stub vs full Part 34.
- Compose has no source bind-mount: runtime needs `docker compose build backend worker && up -d`.
- Phone smoke not performed by agent.

## Commit
`cbd8d52` — `feat(phase-20): adaptive AI nutrition intelligence`
