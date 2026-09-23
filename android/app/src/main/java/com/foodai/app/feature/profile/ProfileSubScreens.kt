package com.foodai.app.feature.profile

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.outlined.CameraAlt
import androidx.compose.material.icons.outlined.Delete
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.foodai.app.core.network.ProfileResponse
import com.foodai.app.core.network.UserSummaryDto
import com.foodai.app.core.ui.components.FoodAIAvatar
import com.foodai.app.core.ui.components.FoodAICard
import com.foodai.app.core.ui.components.FoodAIInfoCard
import com.foodai.app.core.ui.components.FoodAIInput
import com.foodai.app.core.ui.components.FoodAIPrimaryButton
import com.foodai.app.core.ui.components.FoodAITipBanner
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
    val themePrefs = remember {
        dagger.hilt.android.EntryPointAccessors.fromApplication(
            context.applicationContext,
            com.foodai.app.core.ui.theme.ThemePreferencesEntryPoint::class.java,
        ).themePreferences()
    }
    val themeMode by themePrefs.mode.collectAsStateWithLifecycle()
    var unitsMetric by remember { mutableStateOf(prefs.getBoolean("units_metric", true)) }

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
            FoodAITipBanner(
                tipId = "settings_tips",
                text = "Здесь можно отключить обучающие баннеры и сбросить скрытые подсказки.",
            )
            FoodAICard {
                Text("Приложение", style = FoodAITypography.titleMedium)
                Spacer(Modifier.height(FoodAIDimens.Space8))
                Text("Язык: Русский", style = FoodAITypography.bodyMedium)
                Text("Регион: Россия", style = FoodAITypography.bodyMedium)
                Text("Версия: 0.1.0-rc1", style = FoodAITypography.bodySmall)
            }
            FoodAICard {
                SettingsToggleRow(
                    title = "Подсказки в приложении",
                    subtitle = "Обучающие баннеры на экранах",
                    checked = tips,
                    onChange = {
                        tips = it
                        prefs.edit().putBoolean("tips_enabled", it).apply()
                    },
                )
                Spacer(Modifier.height(FoodAIDimens.Space8))
                TextButton(
                    onClick = {
                        val editor = prefs.edit()
                        prefs.all.keys.filter { it.startsWith("tip_dismissed_") }.forEach { editor.remove(it) }
                        editor.apply()
                    },
                ) {
                    Text("Сбросить скрытые подсказки", color = FoodAIColors.Primary)
                }
            }
            FoodAICard {
                Text("Единицы измерения", style = FoodAITypography.titleMedium)
                Spacer(Modifier.height(FoodAIDimens.Space8))
                SettingsToggleRow(
                    title = "Метрическая система",
                    subtitle = if (unitsMetric) "кг, см, мл" else "lb, ft/in (хранение на сервере — кг)",
                    checked = unitsMetric,
                    onChange = {
                        unitsMetric = it
                        prefs.edit().putBoolean("units_metric", it).apply()
                    },
                )
                Spacer(Modifier.height(FoodAIDimens.Space12))
                Text("Тема", style = FoodAITypography.titleMedium)
                Spacer(Modifier.height(FoodAIDimens.Space8))
                listOf(
                    com.foodai.app.core.ui.theme.ThemeMode.SYSTEM to "Системная",
                    com.foodai.app.core.ui.theme.ThemeMode.LIGHT to "Светлая",
                    com.foodai.app.core.ui.theme.ThemeMode.DARK to "Тёмная",
                ).forEach { (mode, label) ->
                    TextButton(
                        onClick = { themePrefs.setMode(mode) },
                        enabled = themeMode != mode,
                    ) {
                        Text(
                            if (themeMode == mode) "✓ $label" else label,
                            color = FoodAIColors.Primary,
                        )
                    }
                }
            }
            FoodAIPrimaryButton(
                label = "Изменить анкету питания",
                onClick = onEditQuestionnaire,
                showArrow = true,
            )
            FoodAIInfoCard(
                text = "Анкету можно обновить в любой момент — план пересчитается при следующем «Пересобрать».",
            )
        }
    }
}

@Composable
private fun SettingsToggleRow(
    title: String,
    subtitle: String,
    checked: Boolean,
    onChange: (Boolean) -> Unit,
) {
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
    viewModel: ProfileViewModel = hiltViewModel(),
) {
    val local by viewModel.localProfile.collectAsStateWithLifecycle()
    val name = viewModel.displayNameOrFallback(email)
    var nameDraft by remember(local.displayName, email) {
        mutableStateOf(if (local.displayName.isNotBlank()) local.displayName else name)
    }
    var bioDraft by remember(local.bio) { mutableStateOf(local.bio) }
    var savedHint by remember { mutableStateOf<String?>(null) }
    val p = profile?.profile

    val picker = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.PickVisualMedia(),
    ) { uri ->
        if (uri != null && viewModel.setAvatar(uri)) {
            savedHint = "Аватар обновлён"
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Редактировать профиль") },
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
            FoodAITipBanner(
                tipId = "profile_edit",
                text = "Имя и фото хранятся на устройстве. Анкета питания (вес, цели) — отдельно в «Мои данные».",
            )
            Box(contentAlignment = Alignment.BottomEnd) {
                FoodAIAvatar(
                    initials = nameDraft.ifBlank { name }.take(2),
                    imagePath = local.avatarPath,
                    size = 96.dp,
                )
                Box(
                    modifier = Modifier
                        .size(36.dp)
                        .clip(CircleShape)
                        .background(FoodAIColors.Primary)
                        .clickable {
                            picker.launch(
                                PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly),
                            )
                        },
                    contentAlignment = Alignment.Center,
                ) {
                    Icon(
                        Icons.Outlined.CameraAlt,
                        contentDescription = "Выбрать фото",
                        tint = FoodAIColors.TextOnPrimary,
                        modifier = Modifier.size(18.dp),
                    )
                }
            }
            if (local.avatarPath != null) {
                TextButton(onClick = {
                    viewModel.clearAvatar()
                    savedHint = "Аватар удалён"
                }) {
                    Icon(Icons.Outlined.Delete, null, tint = FoodAIColors.Error, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.size(6.dp))
                    Text("Удалить фото", color = FoodAIColors.Error)
                }
            }
            Text(email, style = FoodAITypography.bodyMedium, color = FoodAIColors.TextSecondary)
            Text(
                "Тариф: ${user?.tier ?: "free"}",
                style = FoodAITypography.labelMedium,
                color = FoodAIColors.Primary,
            )
            FoodAIInput(
                value = nameDraft,
                onValueChange = { nameDraft = it.take(40) },
                label = "Имя",
                placeholder = "Как к тебе обращаться",
            )
            FoodAIInput(
                value = bioDraft,
                onValueChange = { bioDraft = it.take(120) },
                label = "О себе",
                singleLine = false,
                placeholder = "Коротко о целях",
            )
            FoodAIPrimaryButton(
                label = "Сохранить",
                onClick = {
                    viewModel.setDisplayName(nameDraft)
                    viewModel.setBio(bioDraft)
                    savedHint = "Сохранено"
                },
                showArrow = false,
            )
            if (savedHint != null) {
                Text(savedHint!!, color = FoodAIColors.Primary, style = FoodAITypography.labelMedium)
            }
            FoodAICard {
                Text("Параметры из анкеты", style = FoodAITypography.titleMedium)
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
