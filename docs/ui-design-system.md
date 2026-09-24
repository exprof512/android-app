# FoodAI UI Design System (Phase 22)

Clean Minimal + Soft & Friendly. Calm health app — not an enterprise dashboard.

## Color roles

| Role | Token | Hex | Usage |
|---|---|---|---|
| primary | `FoodAIColors.Primary` | `#2FA84F` | Primary actions, selected, positive progress |
| primaryContainer | `PrimarySoft` / `PrimaryLight` | `#F3FAF4` / `#EAF7ED` | Soft fills, selected backgrounds |
| surface | `Surface` | `#FFFFFF` | Cards, sheets |
| surfaceVariant | `SurfaceMuted` | `#F3F4F6` | Secondary panels |
| background | `Background` | `#FAFBFA` | Screen canvas |
| textPrimary | `TextPrimary` | `#111827` | Titles, values |
| textSecondary | `TextSecondary` | `#6B7280` | Captions, meta |
| success | `Success` (= Primary) | `#2FA84F` | Eaten / complete |
| warning | `Warning` | `#F59E0B` | Over target, caution |
| error | `Error` | `#DC2626` | Destructive, failures |

**Rule:** Green is for primary action, success, selection, positive progress — **not** every container border.

## Typography

| Role | Style |
|---|---|
| display | `headlineMedium`+ |
| headline | `headlineMedium` |
| title | `titleLarge` / `titleMedium` |
| body | `bodyLarge` / `bodyMedium` |
| label | `labelLarge` / `labelMedium` |
| caption | `labelSmall` / `bodySmall` |

## Spacing

`4 · 8 · 12 · 16 · 20 · 24 · 32` (`FoodAIDimens.Space*`)

Screen padding: `20dp`.

## Corner radii

| Size | Token | Value |
|---|---|---|
| small | `Radius12` | 12 |
| medium | `Radius16`–`20` | Card |
| large | `Radius24` | CardLarge / sheets |

## Buttons

| Type | Component |
|---|---|
| primary | `FoodAIPrimaryButton` |
| secondary | `FoodAIOutlinedButton` / `FoodAISecondaryButton` |
| text | Material `TextButton` |
| destructive | Text/button with `Error` color |

## Cards

| Type | Treatment |
|---|---|
| default | Surface + subtle elevation (no green outline) |
| highlighted | Left accent bar or soft primary container |
| warning | Warning text / amber accent |
| success | Success accent / check state |

## Terminology (RU)

- **ккал** (lowercase in body)
- **Белки / Жиры / Углеводы**
- **Съедено / Запланировано / Пропущено / Заменено**
- **Съедено** = consumed totals only (never planned slots)

## Nutrition display invariants

- Consumed values come from API `day_progress` — Android does not re-aggregate from mixed sources.
- Over target → show `+N ккал сверх цели`, never `0 осталось` as the main message.
- Planned remaining is informational and separate from consumed.
