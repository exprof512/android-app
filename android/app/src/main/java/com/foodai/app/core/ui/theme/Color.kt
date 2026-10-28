package com.foodai.app.core.ui.theme

import androidx.compose.runtime.Composable
import androidx.compose.runtime.ReadOnlyComposable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color

/**
 * FoodAI palette: warm neutral surfaces + emerald accent.
 * Light is airy paper; dark is graphite (never pure black) with mint accents.
 */
data class FoodAPalette(
    val primary: Color,
    val onPrimary: Color,
    val primaryDark: Color,
    val primaryLight: Color,
    val primarySoft: Color,
    val background: Color,
    val surface: Color,
    val surfaceMuted: Color,
    val textPrimary: Color,
    val textSecondary: Color,
    val textMuted: Color,
    val divider: Color,
    val error: Color,
    val warning: Color,
    val gold: Color,
    val navBar: Color,
    val navSelected: Color,
    val isDark: Boolean,
)

val LightPalette = FoodAPalette(
    primary = Color(0xFF2E7D5B),
    onPrimary = Color(0xFFFFFFFF),
    primaryDark = Color(0xFF1F5C42),
    primaryLight = Color(0xFFDDF3E7),
    primarySoft = Color(0xFFEDF8F1),
    background = Color(0xFFF7F8F5),
    surface = Color(0xFFFFFFFF),
    surfaceMuted = Color(0xFFEEF2EC),
    textPrimary = Color(0xFF16211B),
    textSecondary = Color(0xFF5D6B63),
    textMuted = Color(0xFF8A9790),
    divider = Color(0xFFE2E8E2),
    error = Color(0xFFC0392B),
    warning = Color(0xFFB45309),
    gold = Color(0xFFB8860B),
    navBar = Color(0xFFFCFDFB),
    navSelected = Color(0xFFDDF3E7),
    isDark = false,
)

val DarkPalette = FoodAPalette(
    primary = Color(0xFF7BD8A8),
    onPrimary = Color(0xFF06251A),
    primaryDark = Color(0xFF4FB684),
    primaryLight = Color(0xFF1D3A2C),
    primarySoft = Color(0xFF182A21),
    background = Color(0xFF0F1412),
    surface = Color(0xFF171D1A),
    surfaceMuted = Color(0xFF202823),
    textPrimary = Color(0xFFE7EDE9),
    textSecondary = Color(0xFFA8B6AD),
    textMuted = Color(0xFF7C8A82),
    divider = Color(0xFF2A352E),
    error = Color(0xFFFF8A7A),
    warning = Color(0xFFF0B45E),
    gold = Color(0xFFE3C26A),
    navBar = Color(0xFF141A17),
    navSelected = Color(0xFF1D3A2C),
    isDark = true,
)

val LocalFoodAPalette = staticCompositionLocalOf { LightPalette }

/**
 * Legacy token names used across screens. They resolve to the active palette,
 * so switching ThemeMode repaints every screen without per-screen changes.
 */
object FoodAIColors {
    val Primary: Color
        @Composable @ReadOnlyComposable get() = LocalFoodAPalette.current.primary
    val PrimaryDark: Color
        @Composable @ReadOnlyComposable get() = LocalFoodAPalette.current.primaryDark
    val PrimaryLight: Color
        @Composable @ReadOnlyComposable get() = LocalFoodAPalette.current.primaryLight
    val PrimarySoft: Color
        @Composable @ReadOnlyComposable get() = LocalFoodAPalette.current.primarySoft

    val Background: Color
        @Composable @ReadOnlyComposable get() = LocalFoodAPalette.current.background
    val Surface: Color
        @Composable @ReadOnlyComposable get() = LocalFoodAPalette.current.surface
    val SurfaceMuted: Color
        @Composable @ReadOnlyComposable get() = LocalFoodAPalette.current.surfaceMuted

    val TextPrimary: Color
        @Composable @ReadOnlyComposable get() = LocalFoodAPalette.current.textPrimary
    val TextSecondary: Color
        @Composable @ReadOnlyComposable get() = LocalFoodAPalette.current.textSecondary
    val TextMuted: Color
        @Composable @ReadOnlyComposable get() = LocalFoodAPalette.current.textMuted
    val TextOnPrimary: Color
        @Composable @ReadOnlyComposable get() = LocalFoodAPalette.current.onPrimary

    val Divider: Color
        @Composable @ReadOnlyComposable get() = LocalFoodAPalette.current.divider
    val Border: Color
        @Composable @ReadOnlyComposable get() = LocalFoodAPalette.current.divider
    val BorderSelected: Color
        @Composable @ReadOnlyComposable get() = LocalFoodAPalette.current.primary

    val Error: Color
        @Composable @ReadOnlyComposable get() = LocalFoodAPalette.current.error
    val Warning: Color
        @Composable @ReadOnlyComposable get() = LocalFoodAPalette.current.warning
    val Success: Color
        @Composable @ReadOnlyComposable get() = LocalFoodAPalette.current.primary

    val NavBar: Color
        @Composable @ReadOnlyComposable get() = LocalFoodAPalette.current.navBar
    val NavSelected: Color
        @Composable @ReadOnlyComposable get() = LocalFoodAPalette.current.navSelected
    val Gold: Color
        @Composable @ReadOnlyComposable get() = LocalFoodAPalette.current.gold
}

/** Backward-compatible aliases used by earlier feature screens. */
object FoodAiTokens {
    val Forest: Color
        @Composable @ReadOnlyComposable get() = FoodAIColors.Primary
    val ForestDeep: Color
        @Composable @ReadOnlyComposable get() = FoodAIColors.PrimaryDark
    val Leaf: Color
        @Composable @ReadOnlyComposable get() = FoodAIColors.Primary
    val LeafSoft: Color
        @Composable @ReadOnlyComposable get() = FoodAIColors.PrimaryLight
    val Mist: Color
        @Composable @ReadOnlyComposable get() = FoodAIColors.Background
    val Fog: Color
        @Composable @ReadOnlyComposable get() = FoodAIColors.PrimarySoft
    val NavBar: Color
        @Composable @ReadOnlyComposable get() = FoodAIColors.NavBar
    val NavSelected: Color
        @Composable @ReadOnlyComposable get() = FoodAIColors.NavSelected
    val Ink: Color
        @Composable @ReadOnlyComposable get() = FoodAIColors.TextPrimary
    val Muted: Color
        @Composable @ReadOnlyComposable get() = FoodAIColors.TextSecondary
    val Danger: Color
        @Composable @ReadOnlyComposable get() = FoodAIColors.Error
    val Warning: Color
        @Composable @ReadOnlyComposable get() = FoodAIColors.Warning
    val Success: Color
        @Composable @ReadOnlyComposable get() = FoodAIColors.Success
    val Gold: Color
        @Composable @ReadOnlyComposable get() = FoodAIColors.Gold

    val SpaceXs = 4
    val SpaceSm = 8
    val SpaceMd = 16
    val SpaceLg = 24
    val SpaceXl = 32

    val RadiusSm = 12
    val RadiusMd = 18
    val RadiusLg = 24
    val RadiusPill = 28
}
