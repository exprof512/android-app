package com.foodai.app.core.ui.theme

import android.app.Activity
import android.content.Context
import android.content.ContextWrapper
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat
import dagger.hilt.EntryPoint
import dagger.hilt.InstallIn
import dagger.hilt.android.EntryPointAccessors
import dagger.hilt.components.SingletonComponent
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import javax.inject.Inject
import javax.inject.Singleton

enum class ThemeMode { SYSTEM, LIGHT, DARK }

@Singleton
class ThemePreferences @Inject constructor(
    @dagger.hilt.android.qualifiers.ApplicationContext context: Context,
) {
    private val prefs = context.getSharedPreferences("foodai_settings", Context.MODE_PRIVATE)
    private val _mode = MutableStateFlow(readMode())
    val mode: StateFlow<ThemeMode> = _mode.asStateFlow()

    private fun readMode(): ThemeMode {
        val raw = prefs.getString("theme_mode", null)
        if (raw != null) {
            return runCatching { ThemeMode.valueOf(raw) }.getOrDefault(ThemeMode.SYSTEM)
        }
        return if (prefs.getBoolean("prefer_system_theme", true)) ThemeMode.SYSTEM else ThemeMode.LIGHT
    }

    fun setMode(mode: ThemeMode) {
        prefs.edit()
            .putString("theme_mode", mode.name)
            .putBoolean("prefer_system_theme", mode == ThemeMode.SYSTEM)
            .apply()
        _mode.value = mode
    }
}

@Singleton
class UnitPreferences @Inject constructor(
    @dagger.hilt.android.qualifiers.ApplicationContext context: Context,
) {
    private val prefs = context.getSharedPreferences("foodai_settings", Context.MODE_PRIVATE)
    private val _metric = MutableStateFlow(prefs.getBoolean("units_metric", true))
    val metric: StateFlow<Boolean> = _metric.asStateFlow()

    fun setMetric(metric: Boolean) {
        prefs.edit().putBoolean("units_metric", metric).apply()
        _metric.value = metric
    }

    fun formatWeightKg(kg: Double?): String {
        if (kg == null) return "—"
        return if (_metric.value) {
            "${kg.toInt()} кг"
        } else {
            String.format("%.1f lb", kg * 2.2046226218)
        }
    }

    fun parseWeightInputToKg(raw: String): Double? {
        val value = raw.replace(',', '.').toDoubleOrNull() ?: return null
        return if (_metric.value) value else value / 2.2046226218
    }
}

private val LightScheme = lightColorScheme(
    primary = LightPalette.primary,
    onPrimary = LightPalette.onPrimary,
    primaryContainer = LightPalette.primaryLight,
    onPrimaryContainer = LightPalette.primaryDark,
    secondary = LightPalette.primaryDark,
    onSecondary = LightPalette.onPrimary,
    tertiary = LightPalette.warning,
    onTertiary = LightPalette.onPrimary,
    background = LightPalette.background,
    onBackground = LightPalette.textPrimary,
    surface = LightPalette.surface,
    onSurface = LightPalette.textPrimary,
    surfaceVariant = LightPalette.surfaceMuted,
    onSurfaceVariant = LightPalette.textSecondary,
    outline = LightPalette.divider,
    outlineVariant = LightPalette.divider,
    error = LightPalette.error,
    onError = LightPalette.onPrimary,
)

private val DarkScheme = darkColorScheme(
    primary = DarkPalette.primary,
    onPrimary = DarkPalette.onPrimary,
    primaryContainer = DarkPalette.primaryLight,
    onPrimaryContainer = DarkPalette.primary,
    secondary = DarkPalette.primary,
    onSecondary = DarkPalette.onPrimary,
    tertiary = DarkPalette.warning,
    onTertiary = DarkPalette.background,
    background = DarkPalette.background,
    onBackground = DarkPalette.textPrimary,
    surface = DarkPalette.surface,
    onSurface = DarkPalette.textPrimary,
    surfaceVariant = DarkPalette.surfaceMuted,
    onSurfaceVariant = DarkPalette.textSecondary,
    outline = DarkPalette.divider,
    outlineVariant = DarkPalette.divider,
    error = DarkPalette.error,
    onError = DarkPalette.onPrimary,
)

private fun Context.findActivity(): Activity? {
    var current: Context? = this
    while (current is ContextWrapper) {
        if (current is Activity) return current
        current = current.baseContext
    }
    return current as? Activity
}

@EntryPoint
@InstallIn(SingletonComponent::class)
interface ThemePreferencesEntryPoint {
    fun themePreferences(): ThemePreferences
}

@Composable
fun FoodAiTheme(content: @Composable () -> Unit) {
    val context = LocalView.current.context
    val prefs = EntryPointAccessors.fromApplication(
        context.applicationContext,
        ThemePreferencesEntryPoint::class.java,
    ).themePreferences()
    val mode by prefs.mode.collectAsState()
    val systemDark = isSystemInDarkTheme()
    val useDark = when (mode) {
        ThemeMode.SYSTEM -> systemDark
        ThemeMode.LIGHT -> false
        ThemeMode.DARK -> true
    }
    val palette = if (useDark) DarkPalette else LightPalette
    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = context.findActivity()?.window ?: return@SideEffect
            val controller = WindowCompat.getInsetsController(window, view)
            controller.isAppearanceLightStatusBars = !useDark
            controller.isAppearanceLightNavigationBars = !useDark
        }
    }
    CompositionLocalProvider(LocalFoodAPalette provides palette) {
        MaterialTheme(
            colorScheme = if (useDark) DarkScheme else LightScheme,
            typography = FoodAITypography,
            shapes = FoodAIMaterialShapes,
            content = content,
        )
    }
}
