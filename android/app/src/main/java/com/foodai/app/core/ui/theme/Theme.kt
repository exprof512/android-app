package com.foodai.app.core.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val LightColors = lightColorScheme(
    primary = FoodAIColors.Primary,
    onPrimary = FoodAIColors.TextOnPrimary,
    primaryContainer = FoodAIColors.PrimaryLight,
    onPrimaryContainer = FoodAIColors.PrimaryDark,
    secondary = FoodAIColors.PrimaryDark,
    onSecondary = FoodAIColors.TextOnPrimary,
    background = FoodAIColors.Background,
    onBackground = FoodAIColors.TextPrimary,
    surface = FoodAIColors.Surface,
    onSurface = FoodAIColors.TextPrimary,
    surfaceVariant = FoodAIColors.PrimarySoft,
    onSurfaceVariant = FoodAIColors.TextSecondary,
    outline = FoodAIColors.Divider,
    error = FoodAIColors.Error,
    onError = FoodAIColors.TextOnPrimary,
)

private val DarkColors = darkColorScheme(
    primary = FoodAIColors.Primary,
    onPrimary = Color.White,
    primaryContainer = FoodAIColors.PrimaryDark,
    onPrimaryContainer = FoodAIColors.PrimaryLight,
    secondary = FoodAIColors.PrimaryLight,
    onSecondary = FoodAIColors.PrimaryDark,
    background = Color(0xFF0F1412),
    onBackground = FoodAIColors.Background,
    surface = Color(0xFF171C1A),
    onSurface = FoodAIColors.Background,
    surfaceVariant = Color(0xFF1E2622),
    onSurfaceVariant = FoodAIColors.PrimaryLight,
    outline = Color(0xFF3A4440),
    error = Color(0xFFF97066),
    onError = FoodAIColors.PrimaryDark,
)

@Composable
fun FoodAiTheme(
    darkTheme: Boolean = false,
    content: @Composable () -> Unit,
) {
    // Primary product experience is light mode (design references).
    // Dark scheme is wired for future use; do not auto-force from system yet.
    val useDark = darkTheme && isSystemInDarkTheme()
    MaterialTheme(
        colorScheme = if (useDark) DarkColors else LightColors,
        typography = FoodAITypography,
        shapes = FoodAIMaterialShapes,
        content = content,
    )
}
