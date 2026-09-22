# FoodAI Design System

Primary visual references: [`screens/`](screens/).

## Screen map

| File | Screen |
|------|--------|
| `00-app-icon.jpg` | App icon |
| `01-welcome.jpg` | Welcome |
| `02-goal.jpg` | Onboarding — goal |
| `03-about-you.jpg` | Onboarding — about you |
| `04-activity.jpg` | Onboarding — activity |
| `05-meals.jpg` | Onboarding — meals |
| `06-preferences.jpg` | Onboarding — preferences |
| `07-budget.jpg` | Onboarding — budget |
| `08-cook-time.jpg` | Onboarding — cook time |
| `09-pantry.jpg` | Onboarding — pantry |
| `10-ai-generating.jpg` | Onboarding — AI plan loading |
| `11-home-today.jpg` | Home / Today |
| `12-recipe-detail.jpg` | Recipe detail |
| `13-week-plan.jpg` | Weekly plan |
| `14-shopping.jpg` | Shopping list |
| `15-progress.jpg` | Progress |
| `16-profile.jpg` | Profile |
| `17-premium.jpg` | Premium |
| `18-ui-states.jpg` | UI states sheet |

## Colors (`FoodAIColors`)

| Token | Value | Use |
|-------|-------|-----|
| Primary | `#2FA84F` | CTA, selected, brand |
| PrimaryDark | `#21883E` | Pressed / emphasis |
| PrimaryLight / PrimarySoft | `#EAF7ED` / `#F3FAF4` | Selected fills, banners |
| Background | `#FAFBFA` | Screen bg |
| Surface | `#FFFFFF` | Cards |
| TextPrimary | `#111827` | Headlines |
| TextSecondary | `#6B7280` | Body / captions |
| TextMuted | `#9CA3AF` | Hints |
| Border / Divider | `#E5E7EB` | Hairlines |
| Error / Warning / Success | red / orange / primary | States |
| Gold | `#C9A227` | Premium accents |

Do **not** hardcode `Color(0xFF…)` inside screen composables — use tokens.

## Typography (`FoodAITypography`)

Display → HeadlineLarge/Medium → TitleLarge/Medium → BodyLarge/Medium/Small → LabelLarge/Medium.

Headlines: bold. Body: regular. Buttons: semibold. Avoid making the whole UI bold.
Watch Russian wrapping — prefer layout changes over tiny fonts.

## Spacing (`FoodAIDimens`)

Scale: 4 / 8 / 12 / 16 / 20 / 24 / 32 / 40 / 48 dp.  
Screen horizontal padding: `ScreenPadding` = 20 dp.

## Shapes (`FoodAIShapes`)

Cards 20–24 dp, large cards 24 dp, buttons ~24 dp, inputs 16 dp, chips 12–16 dp.

## Elevation (`FoodAIElevation`)

Prefer subtle elevation (1–2 dp) or thin borders — no heavy Material shadows.

## Components (`com.foodai.app.core.ui.components`)

- Buttons: `FoodAIPrimaryButton`, `FoodAISecondaryButton`, `FoodAIOutlinedButton`, `FoodAIIconButton`
- Cards: `FoodAICard`, `FoodAISelectableCard`, `FoodAIRecipeCard`, `FoodAIMetricCard`, `FoodAIProgressCard`, `FoodAIInfoCard`
- Inputs: `FoodAIInput`, `FoodAISearchField`, `FoodAIStepper`, `FoodAIChip`
- Chrome: `FoodAILogo`, `FoodAIHeader`, `FoodAIOnboardingTopBar`, `FoodAIStepIndicator`, `OnboardingScaffold`
- Nav: `FoodAINavigationBar` (Сегодня · План · **FAB** · Прогресс · Профиль)
- States: `FoodAILoading`, `FoodAIEmptyState`, `FoodAIToast`, `FoodAIStatusDot`, `FoodAIMacroBar`, `FoodAIDangerButton`

## Images

- Logo mark: `ic_foodai_mark.xml` (transparent vector). PNG logo cleaned for alpha.
- Welcome hero: `img_hero_bowl.png` — **not** the app logo.
- Recipe images: Coil + `RecipeImagePane` states PENDING / PROCESSING / READY / FAILED ("Готовим фото блюда…").

## Navigation

Main tabs: Сегодня · План · center FAB (Ask AI) · Прогресс · Профиль.  
Shopping opens from Plan/Today CTA. Chat from FAB or recipe.

### Profile destinations (do not all open questionnaire)

| Entry | Destination |
|-------|-------------|
| Avatar / name card | Profile details (read-only summary) |
| Настройки | Settings (language, tips, link to questionnaire) |
| Мои данные / Изменить цель | Onboarding questionnaire (`generatePlan=false`) |
| Уведомления | Notifications toggles (local prefs) |
| Премиум → Управлять | Premium screen |

### Today metrics

- **Вода** — tap adds 250 ml (local, scoped by user id).
- **Шаги** — `TYPE_STEP_COUNTER` + `ACTIVITY_RECOGNITION` permission.
- **Вес / Прогресс** — open Progress tab.
- Refresh actions use a circular refresh icon; rebuild stays as «Пересобрать».

### Week plan

`GET /meal-plans/week` returns items for the full plan window (`start_date`…`end_date`). UI date chips always cover that range.

### Account switch

Login / register / logout clear onboarding draft and daily metrics via `LocalSessionCleaner` so a new account never sees the previous user's local questionnaire or water/steps.

## Light mode

Primary product experience is light. Dark `ColorScheme` is wired for later — not auto-enabled.
