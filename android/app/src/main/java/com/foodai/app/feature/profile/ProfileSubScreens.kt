package com.foodai.app.feature.profile

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import com.foodai.app.core.network.ProfileResponse
import com.foodai.app.core.network.UserSummaryDto
import com.foodai.app.core.ui.components.FoodAIAvatar
import com.foodai.app.core.ui.components.FoodAICard
import com.foodai.app.core.ui.components.FoodAIInfoCard
import com.foodai.app.core.ui.components.FoodAIPrimaryButton
import com.foodai.app.core.ui.theme.FoodAIColors
import com.foodai.app.core.ui.theme.FoodAIDimens
import com.foodai.app.core.ui.theme.FoodAITypography

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsRoute(
    onBack: () -> Unit,
    onEditQuestionnaire: () -> Unit,
) {
    val context = LocalContext.current
    val prefs = remember {
        context.getSharedPreferences("foodai_settings", android.content.Context.MODE_PRIVATE)
    }
    var tips by remember { mutableStateOf(prefs.getBoolean("tips_enabled", true)) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Настройки") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Назад")
                    }
                },
            )
        },
        containerColor = FoodAIColors.Background,
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(FoodAIDimens.ScreenPadding)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(FoodAIDimens.Space16),
        ) {
            FoodAICard {
                Text("Приложение", style = FoodAITypography.titleMedium)
                Spacer(Modifier.height(FoodAIDimens.Space8))
                Text("Язык: Русский", style = FoodAITypography.bodyMedium)
                Text("Регион: Россия", style = FoodAITypography.bodyMedium)
                Text("Версия: 0.1.0-rc1", style = FoodAITypography.bodySmall)
            }
            FoodAICard {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(Modifier.weight(1f)) {
                        Text("Подсказки в приложении", style = FoodAITypography.titleMedium)
                        Text("Показывать обучающие баннеры", style = FoodAITypography.bodySmall)
                    }
                    Switch(
                        checked = tips,
                        onCheckedChange = {
                            tips = it
                            prefs.edit().putBoolean("tips_enabled", it).apply()
                        },
                        colors = SwitchDefaults.colors(checkedTrackColor = FoodAIColors.Primary),
                    )
                }
            }
            FoodAIPrimaryButton(
                label = "Изменить анкету питания",
                onClick = onEditQuestionnaire,
                showArrow = true,
            )
            FoodAIInfoCard(text = "Анкету можно обновить в любой момент — план пересчитается при следующем «Пересобрать».")
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NotificationsRoute(onBack: () -> Unit) {
    val context = LocalContext.current
    val prefs = remember {
        context.getSharedPreferences("foodai_notifications", android.content.Context.MODE_PRIVATE)
    }
    var meals by remember { mutableStateOf(prefs.getBoolean("meals", true)) }
    var water by remember { mutableStateOf(prefs.getBoolean("water", true)) }
    var tips by remember { mutableStateOf(prefs.getBoolean("tips", false)) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Уведомления") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Назад")
                    }
                },
            )
        },
        containerColor = FoodAIColors.Background,
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(FoodAIDimens.ScreenPadding),
            verticalArrangement = Arrangement.spacedBy(FoodAIDimens.Space12),
        ) {
            NotifToggle("Приёмы пищи", "Напоминания о завтраке, обеде и ужине", meals) {
                meals = it
                prefs.edit().putBoolean("meals", it).apply()
            }
            NotifToggle("Вода", "Напоминания выпить воды", water) {
                water = it
                prefs.edit().putBoolean("water", it).apply()
            }
            NotifToggle("Мотивация", "Советы и прогресс за день", tips) {
                tips = it
                prefs.edit().putBoolean("tips", it).apply()
            }
            FoodAIInfoCard(text = "Пуши появятся в следующем релизе. Сейчас настройки сохраняются локально.")
        }
    }
}

@Composable
private fun NotifToggle(
    title: String,
    subtitle: String,
    checked: Boolean,
    onChange: (Boolean) -> Unit,
) {
    FoodAICard {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f)) {
                Text(title, style = FoodAITypography.titleMedium)
                Text(subtitle, style = FoodAITypography.bodySmall)
            }
            Switch(
                checked = checked,
                onCheckedChange = onChange,
                colors = SwitchDefaults.colors(checkedTrackColor = FoodAIColors.Primary),
            )
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProfileDetailsRoute(
    email: String,
    user: UserSummaryDto?,
    profile: ProfileResponse?,
    onBack: () -> Unit,
    onEditQuestionnaire: () -> Unit,
) {
    val name = email.substringBefore("@").replaceFirstChar { it.uppercase() }
    val p = profile?.profile
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Профиль") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Назад")
                    }
                },
            )
        },
        containerColor = FoodAIColors.Background,
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(FoodAIDimens.ScreenPadding)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(FoodAIDimens.Space16),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            FoodAIAvatar(initials = name.take(2))
            Text(name, style = FoodAITypography.headlineSmall)
            Text(email, style = FoodAITypography.bodyMedium, color = FoodAIColors.TextSecondary)
            Text(
                "Тариф: ${user?.tier ?: "free"}",
                style = FoodAITypography.labelMedium,
                color = FoodAIColors.Primary,
            )
            FoodAICard {
                Text("Параметры", style = FoodAITypography.titleMedium)
                Spacer(Modifier.height(FoodAIDimens.Space8))
                DetailRow("Возраст", p?.ageYears?.let { "$it лет" } ?: "—")
                DetailRow("Рост", p?.heightCm?.let { "${it.toInt()} см" } ?: "—")
                DetailRow("Вес", p?.currentWeightKg?.let { "${it.toInt()} кг" } ?: "—")
                DetailRow("Активность", p?.activityLevel ?: "—")
                DetailRow("Приёмов пищи", p?.mealsPerDay?.toString() ?: "—")
            }
            FoodAIPrimaryButton(
                label = "Редактировать анкету",
                onClick = onEditQuestionnaire,
                showArrow = true,
            )
        }
    }
}

@Composable
private fun DetailRow(label: String, value: String) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = FoodAIDimens.Space4),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text(label, style = FoodAITypography.bodyMedium, color = FoodAIColors.TextSecondary)
        Text(value, style = FoodAITypography.titleSmall)
    }
}
