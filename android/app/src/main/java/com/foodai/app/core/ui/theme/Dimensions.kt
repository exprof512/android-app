package com.foodai.app.core.ui.theme

import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

/** Spacing, radii, and control sizes from FoodAI design references. */
object FoodAIDimens {
    val Space4: Dp = 4.dp
    val Space8: Dp = 8.dp
    val Space12: Dp = 12.dp
    val Space16: Dp = 16.dp
    val Space20: Dp = 20.dp
    val Space24: Dp = 24.dp
    val Space32: Dp = 32.dp
    val Space40: Dp = 40.dp
    val Space48: Dp = 48.dp

    /** Horizontal screen padding used on onboarding / welcome. */
    val ScreenPadding: Dp = 22.dp

    val Radius12: Dp = 12.dp
    val Radius16: Dp = 16.dp
    val Radius20: Dp = 20.dp
    val Radius24: Dp = 24.dp
    val Radius28: Dp = 28.dp
    val RadiusPill: Dp = 28.dp

    val ButtonHeight: Dp = 56.dp
    val CompactButtonHeight: Dp = 48.dp
    val IconButtonSize: Dp = 40.dp
    val TouchTarget: Dp = 48.dp
    val StepBarHeight: Dp = 6.dp
    val SelectableIconSize: Dp = 40.dp
    val FoodTileSize: Dp = 64.dp
}

/** Alias used by screens that talk about spacing rather than the full token set. */
typealias FoodAISpacing = FoodAIDimens
