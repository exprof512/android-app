package com.foodai.app.core.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

/** FoodAI design tokens — green nutrition brand from product mockups. */
object FoodAiTokens {
    val Forest = Color(0xFF1B5E4B)
    val ForestDeep = Color(0xFF0F3D32)
    val Leaf = Color(0xFF2F9B72)
    val LeafSoft = Color(0xFFD8F0E4)
    val Mist = Color(0xFFFAFCFA)
    val Fog = Color(0xFFE8F3EC)
    val NavBar = Color(0xFFF0EAF5)
    val NavSelected = Color(0xFFE0D4F0)
    val Ink = Color(0xFF14201C)
    val Muted = Color(0xFF5A6B64)
    val Danger = Color(0xFFB42318)
    val Warning = Color(0xFFB54708)
    val Success = Color(0xFF027A48)
    val Gold = Color(0xFFC9A227)

    val SpaceXs = 4
    val SpaceSm = 8
    val SpaceMd = 16
    val SpaceLg = 24
    val SpaceXl = 32

    val RadiusSm = 8
    val RadiusMd = 16
    val RadiusLg = 24
    val RadiusPill = 28
}

private val LightColors = lightColorScheme(
    primary = FoodAiTokens.Forest,
    onPrimary = Color.White,
    primaryContainer = FoodAiTokens.LeafSoft,
    onPrimaryContainer = FoodAiTokens.ForestDeep,
    secondary = FoodAiTokens.Leaf,
    onSecondary = Color.White,
    background = FoodAiTokens.Mist,
    onBackground = FoodAiTokens.Ink,
    surface = Color.White,
    onSurface = FoodAiTokens.Ink,
    surfaceVariant = FoodAiTokens.Fog,
    onSurfaceVariant = FoodAiTokens.Muted,
    error = FoodAiTokens.Danger,
    onError = Color.White,
)

private val DarkColors = darkColorScheme(
    primary = FoodAiTokens.Leaf,
    onPrimary = FoodAiTokens.ForestDeep,
    primaryContainer = FoodAiTokens.ForestDeep,
    onPrimaryContainer = FoodAiTokens.Fog,
    secondary = FoodAiTokens.Fog,
    onSecondary = FoodAiTokens.ForestDeep,
    background = Color(0xFF0C1512),
    onBackground = FoodAiTokens.Mist,
    surface = Color(0xFF14201C),
    onSurface = FoodAiTokens.Mist,
    surfaceVariant = Color(0xFF1E2E28),
    onSurfaceVariant = FoodAiTokens.Fog,
    error = Color(0xFFF97066),
    onError = FoodAiTokens.ForestDeep,
)

private val FoodAiTypography = androidx.compose.material3.Typography(
    displayLarge = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Bold,
        fontSize = 40.sp,
        lineHeight = 44.sp,
    ),
    headlineMedium = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.SemiBold,
        fontSize = 28.sp,
        lineHeight = 34.sp,
    ),
    titleLarge = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.SemiBold,
        fontSize = 22.sp,
        lineHeight = 28.sp,
    ),
    titleMedium = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Medium,
        fontSize = 18.sp,
        lineHeight = 24.sp,
    ),
    bodyLarge = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Normal,
        fontSize = 16.sp,
        lineHeight = 24.sp,
    ),
    bodyMedium = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Normal,
        fontSize = 14.sp,
        lineHeight = 20.sp,
    ),
    labelLarge = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Medium,
        fontSize = 14.sp,
        lineHeight = 20.sp,
    ),
)

@Composable
fun FoodAiTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    MaterialTheme(
        // Product mockups are light-first; keep dark only when system forces it.
        colorScheme = if (darkTheme) DarkColors else LightColors,
        typography = FoodAiTypography,
        content = content,
    )
}
