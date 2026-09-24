# PHASE 21 REPORT

## Status
PARTIAL

## Summary
Food journal extended on existing `nutrition_logs` (no parallel diary). DeepSeek is exclusive for product text AI; OpenAI is vision + image generation only. Photo analysis → match ingredients → backend nutrition → user confirm → diary.

## AI Provider Routing
Documented in [ai-provider-routing.md](ai-provider-routing.md).

### DeepSeek (text)
- chat, meal plan, recipes, replace, food_suggestion, daily_adaptation, substitution, variant
- `build_text_provider()` → `DeepSeekChatProvider` only (mock if no key; **never** OpenAI text)

### OpenAI
- Vision: `OpenAIVisionProvider` / `food_photo_analysis`
- Images: existing `OpenAIImageProvider`

## Food Diary
- Extended sources: `photo_ai`, `search`, `quick_add`, `planned_meal` (+ existing)
- Meal type `custom` added
- Optional `ingredient_id`, `quantity_g`, `unit`, `notes`, `confidence`
- Endpoints: day summary, history, search, calculate, duplicate, meal templates
- Edit allowed for manual/photo_ai/search/quick_add; grams → backend recalc

## Photo / Vision
- `POST /nutrition/photo/analyze` (multipart)
- Match + authoritative nutrition
- Review + edit grams + confirm (`Idempotency-Key`)
- Low confidence flagged; never auto-persist

## Backend
- Migration `0017_phase21_food_journal`
- `python-multipart` dependency
- Entitlement `food_photo_analysis` (free 10/day default)

## Android
- Extended `NutritionApi` + DTOs
- `AddFoodSheet` / `AddFoodViewModel`: quick, search, recent, photo gallery → review → confirm
- Wired into Today “Добавить еду”
- AppStateBus `NutritionLogChanged` on save

## Tests
```
python -m pytest tests/test_ai_provider_routing.py tests/test_phase21_food_journal.py -q
...........  (11 passed)
```

## APK
`/root/app-android/android-app/android/app/build/outputs/apk/debug/app-debug.apk`

## Physical Device
NOT RUN by agent — do not claim PASS.

## Known Limitations / Remaining DoD
- Camera capture (Take photo) uses gallery picker only for now; camera intent can be added
- Meal templates UI on Android is API-ready but no dedicated templates screen yet
- Plan vs actual comparison UI not fully surfaced beyond day_progress
- Weekly analytics charts not expanded beyond existing Progress
- Android instrumented UI tests not added this phase
- Physical device smoke not performed by agent
- Favorites remain recipe favorites (existing); food-level favorites not duplicated

## Documentation
- `docs/ai-provider-routing.md`
- `docs/phase-21-report.md`
- `docs/ai.md` routing update
- `.env.example` vision + DeepSeek notes

## Commit
`feat(phase-21): food journal and vision nutrition`
