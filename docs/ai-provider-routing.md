# AI Provider Routing

FoodAI uses **explicit** provider routing. Text and vision/image are never interchangeable.

## Rule

| Capability | Provider | Notes |
|---|---|---|
| All user-facing / structured **text** AI | **DeepSeek** | Chat, plans, recipes, replacements, adaptations, suggestions, substitutions, variants, shopping text |
| Food **photo** understanding | **OpenAI Vision** | Identify foods / estimate portions only |
| Recipe **image generation** | **OpenAI Images** | Existing async pipeline |
| Authoritative calories / macros / cost | **Backend Nutrition Engine** | Never AI |

Android never holds API keys. Routing is backend-only (`Settings` + DI).

## Operation matrix

| Operation | Provider | Module |
|---|---|---|
| `chat_answer` | DeepSeek | `DeepSeekChatProvider` |
| `generate_meal_plan_proposal` | DeepSeek | `DeepSeekChatProvider` |
| `generate_recipe_candidates` | DeepSeek | `DeepSeekChatProvider` |
| `replace_meal_item` | DeepSeek | `DeepSeekChatProvider` |
| `food_suggestion` | DeepSeek | `DeepSeekChatProvider` |
| `daily_adaptation` | DeepSeek | `DeepSeekChatProvider` |
| `ingredient_substitution` | DeepSeek | `DeepSeekChatProvider` |
| `recipe_variant` | DeepSeek | `DeepSeekChatProvider` |
| `food_photo_analysis` | OpenAI Vision | `OpenAIVisionProvider` |
| Recipe image generate / regenerate | OpenAI Images | `OpenAIImageProvider` |

## Configuration

```
DEEPSEEK_API_KEY
DEEPSEEK_TEXT_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_TEXT_TIMEOUT_SECONDS=60

OPENAI_API_KEY
OPENAI_VISION_MODEL=gpt-4.1-mini
OPENAI_VISION_TIMEOUT_SECONDS=60
OPENAI_VISION_MAX_IMAGE_BYTES=5242880
OPENAI_IMAGE_MODEL=gpt-image-2
```

`OPENAI_TEXT_MODEL` is retained for legacy config compatibility. Product text prefers DeepSeek; if the DeepSeek key is rejected (`ai_auth_error`), rate-limited, or the provider is unavailable, `FallbackTextProvider` retries the same structured request on OpenAI Responses (`OPENAI_TEXT_MODEL`, default `gpt-4.1-mini`). An auth failure disables that provider for the process, so a revoked key costs one failed attempt, not one per request. Fix the DeepSeek key and restart backend/worker to return to the primary provider.

## Selection code

- Text: `build_text_provider()` → DeepSeek only (mock in test / when no DeepSeek key).
- Vision: `build_vision_provider()` → OpenAI Vision (mock in test).
- Images: existing `OpenAIImageProvider` in the worker.

`FallbackTextProvider` may still exist for tests, but production text routing does **not** fall through to OpenAI Responses for product text AI.

## Usage accounting

| Table | Provider traffic |
|---|---|
| `ai_text_usage` | DeepSeek text ops (+ mock) |
| `ai_image_usage` | OpenAI image generation |
| Vision calls | Recorded in `ai_text_usage` with `operation=food_photo_analysis` and vision model, or dedicated fields in the same audit trail — never log image bytes |

## Tests

See `tests/test_ai_provider_routing.py` — mocks only, no live network.
