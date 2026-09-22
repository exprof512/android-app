package com.foodai.app.core.ui.theme

import androidx.compose.ui.graphics.Color

/**
 * FoodAI color tokens — locked to docs/design/screens references.
 * Prefer these over hardcoded Color(...) in composables.
 */
object FoodAIColors {
    val Primary = Color(0xFF2FA84F)
    val PrimaryDark = Color(0xFF21883E)
    val PrimaryLight = Color(0xFFEAF7ED)
    val PrimarySoft = Color(0xFFF3FAF4)

    val Background = Color(0xFFFAFBFA)
    val Surface = Color(0xFFFFFFFF)
    val SurfaceMuted = Color(0xFFF3F4F6)

    val TextPrimary = Color(0xFF111827)
    val TextSecondary = Color(0xFF6B7280)
    val TextMuted = Color(0xFF9CA3AF)
    val TextOnPrimary = Color(0xFFFFFFFF)

    val Divider = Color(0xFFE5E7EB)
    val Border = Color(0xFFE5E7EB)
    val BorderSelected = Primary

    val Error = Color(0xFFDC2626)
    val Warning = Color(0xFFF59E0B)
    val Success = Primary

    val NavBar = Color(0xFFF5F7F5)
    val NavSelected = PrimarySoft
    val Gold = Color(0xFFC9A227)
}

/**
 * Backward-compatible aliases used by earlier feature screens.
 * New code should prefer [FoodAIColors].
 */
object FoodAiTokens {
    val Forest = FoodAIColors.Primary
    val ForestDeep = FoodAIColors.PrimaryDark
    val Leaf = FoodAIColors.Primary
    val LeafSoft = FoodAIColors.PrimaryLight
    val Mist = FoodAIColors.Background
    val Fog = FoodAIColors.PrimarySoft
    val NavBar = FoodAIColors.NavBar
    val NavSelected = FoodAIColors.NavSelected
    val Ink = FoodAIColors.TextPrimary
    val Muted = FoodAIColors.TextSecondary
    val Danger = FoodAIColors.Error
    val Warning = FoodAIColors.Warning
    val Success = FoodAIColors.Success
    val Gold = FoodAIColors.Gold

    val SpaceXs = FoodAIDimens.Space4.value.toInt()
    val SpaceSm = FoodAIDimens.Space8.value.toInt()
    val SpaceMd = FoodAIDimens.Space16.value.toInt()
    val SpaceLg = FoodAIDimens.Space24.value.toInt()
    val SpaceXl = FoodAIDimens.Space32.value.toInt()

    val RadiusSm = FoodAIDimens.Radius12.value.toInt()
    val RadiusMd = FoodAIDimens.Radius16.value.toInt()
    val RadiusLg = FoodAIDimens.Radius24.value.toInt()
    val RadiusPill = FoodAIDimens.RadiusPill.value.toInt()
}
