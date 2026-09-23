package com.foodai.app.core.ui.theme

import android.content.Context
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
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
        // Migrate legacy prefer_system_theme boolean.
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
            val lb = kg * 2.2046226218
            String.format("%.1f lb", lb)
        }
    }

    fun parseWeightInputToKg(raw: String): Double? {
        val value = raw.replace(',', '.').toDoubleOrNull() ?: return null
        return if (_metric.value) value else value / 2.2046226218
    }
}

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

@EntryPoint
@InstallIn(SingletonComponent::class)
interface ThemePreferencesEntryPoint {
    fun themePreferences(): ThemePreferences
}

@Composable
fun FoodAiTheme(
    content: @Composable () -> Unit,
) {
    val context = LocalContext.current
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
    MaterialTheme(
        colorScheme = if (useDark) DarkColors else LightColors,
        typography = FoodAITypography,
        shapes = FoodAIMaterialShapes,
        content = content,
    )
}
