package com.foodai.app.feature.plan

import android.Manifest
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.DirectionsWalk
import androidx.compose.material.icons.automirrored.outlined.ShowChart
import androidx.compose.material.icons.outlined.ChevronRight
import androidx.compose.material.icons.outlined.MenuBook
import androidx.compose.material.icons.outlined.MonitorWeight
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.ShoppingCart
import androidx.compose.material.icons.outlined.WaterDrop
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.foodai.app.core.network.DayProgressDto
import com.foodai.app.core.network.MealPlanItemDto
import com.foodai.app.core.network.NutritionLogDto
import com.foodai.app.core.network.WeekDayDto
import com.foodai.app.core.ui.ErrorPane
import com.foodai.app.core.ui.LoadingPane
import com.foodai.app.core.ui.RecipeImagePane
import com.foodai.app.core.ui.displayRecipeName
import com.foodai.app.core.ui.components.FoodAICard
import com.foodai.app.core.ui.components.FoodAIEmptyState
import com.foodai.app.core.ui.formatKcal
import com.foodai.app.core.ui.formatMoney
import com.foodai.app.core.ui.components.FoodAIMacroBar
import com.foodai.app.core.ui.components.FoodAIOutlinedButton
import com.foodai.app.core.ui.components.FoodAIPrimaryButton
import com.foodai.app.core.ui.components.FoodAIStatusDot
import com.foodai.app.core.ui.components.FoodAITipBanner
import com.foodai.app.core.ui.theme.FoodAIColors
import com.foodai.app.core.ui.theme.FoodAIDimens
import com.foodai.app.core.ui.theme.FoodAIShapes
import com.foodai.app.core.ui.theme.FoodAITypography
import com.foodai.app.feature.ai.AiPreviewSheet
import com.foodai.app.feature.ai.AiPreviewState
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.time.format.TextStyle
import java.util.Locale
import kotlin.math.min

private val replaceReasons = listOf(
    "dislike" to "Не нравится",
    "too_expensive" to "Дорого",
    "too_long" to "Долго готовить",
    "unavailable_ingredients" to "Нет продуктов",
    "more_protein" to "Больше белка",
    "less_calories" to "Меньше калорий",
    "nutrition_balance" to "Баланс БЖУ",
    "other" to "Другое",
)

@Composable
fun TodayRoute(
    onOpenRecipe: (recipeId: String, itemId: String) -> Unit,
    onOpenShopping: () -> Unit = {},
    onOpenProgress: () -> Unit = {},
    onOpenPlan: () -> Unit = {},
    onOpenDiary: () -> Unit = {},
    pendingAiAction: String? = null,
    onAiActionConsumed: () -> Unit = {},
    viewModel: TodayViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { granted -> viewModel.onStepsPermissionResult(granted) }
    var replaceNonce by remember { mutableIntStateOf(0) }
    LaunchedEffect(Unit) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            permissionLauncher.launch(Manifest.permission.ACTIVITY_RECOGNITION)
        } else {
            viewModel.onStepsPermissionResult(true)
        }
    }
    LaunchedEffect(pendingAiAction) {
        when (pendingAiAction) {
            "what_to_eat" -> viewModel.requestWhatToEat()
            "adapt_day" -> viewModel.requestAdaptDay()
            "replace" -> replaceNonce += 1
            null -> Unit
        }
        if (pendingAiAction != null) onAiActionConsumed()
    }
    when {
        state.generating -> LoadingPane("Создаём план питания…")
        state.loading && state.plan == null -> LoadingPane("Загружаем сегодня…")
        state.error != null && state.plan == null -> ErrorPane(
            message = state.error ?: "Ошибка",
            onRetry = viewModel::refresh,
            onSecondary = if (state.missingPlan) viewModel::generatePlan else null,
            secondaryLabel = "Создать план на неделю",
        )
        else -> TodayScreen(
            state = state,
            onRefresh = viewModel::refresh,
            onRebuild = viewModel::rebuildPlan,
            onComplete = viewModel::complete,
            onSkip = viewModel::skip,
            onReplace = viewModel::replace,
            onAddWater = viewModel::addWater,
            onUndoWater = viewModel::undoWater,
            onAddFood = viewModel::addFood,
            onDeleteFood = viewModel::deleteFood,
            onAddWeight = viewModel::addWeight,
            onRequestStepsPermission = {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    permissionLauncher.launch(Manifest.permission.ACTIVITY_RECOGNITION)
                } else {
                    viewModel.onStepsPermissionResult(true)
                }
            },
            onOpenRecipe = onOpenRecipe,
            onOpenShopping = onOpenShopping,
            onOpenProgress = onOpenProgress,
            onOpenPlan = onOpenPlan,
            onOpenDiary = onOpenDiary,
            replaceNonce = replaceNonce,
            onWhatToEat = { viewModel.requestWhatToEat() },
            onAdaptDay = viewModel::requestAdaptDay,
            onPantryCook = { viewModel.requestWhatToEat(intent = "pantry_cook") },
            onDismissAi = viewModel::dismissAiPreview,
            onSelectAiCandidate = viewModel::selectAiCandidate,
            onConfirmAiRecommendation = viewModel::confirmAiRecommendation,
            onConfirmAdaptDay = viewModel::confirmAdaptDay,
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TodayScreen(
    state: TodayUiState,
    onRefresh: () -> Unit,
    onRebuild: () -> Unit,
    onComplete: (MealPlanItemDto) -> Unit,
    onSkip: (MealPlanItemDto) -> Unit,
    onReplace: (MealPlanItemDto, String) -> Unit,
    onAddWater: (Int) -> Unit,
    onUndoWater: () -> Unit,
    onAddFood: (description: String, calories: Int, protein: Double, fat: Double, carbs: Double) -> Unit,
    onDeleteFood: (String) -> Unit = {},
    onAddWeight: (Double) -> Unit,
    onRequestStepsPermission: () -> Unit = {},
    onOpenRecipe: (recipeId: String, itemId: String) -> Unit,
    onOpenShopping: () -> Unit = {},
    onOpenProgress: () -> Unit = {},
    onOpenPlan: () -> Unit = {},
    onOpenDiary: () -> Unit = {},
    replaceNonce: Int = 0,
    onWhatToEat: () -> Unit = {},
    onAdaptDay: () -> Unit = {},
    onPantryCook: () -> Unit = {},
    onDismissAi: () -> Unit = {},
    onSelectAiCandidate: (Int) -> Unit = {},
    onConfirmAiRecommendation: () -> Unit = {},
    onConfirmAdaptDay: () -> Unit = {},
) {
    val plan = state.plan
    val progress = plan?.dayProgress
    val selectedDay = state.selectedDate.take(10)
    val todayItems = plan?.items.orEmpty()
        .filter { it.date.take(10) == selectedDay }
        .sortedBy { it.sortOrder }
    val nextMeal = progress?.nextMealItemId?.let { id -> todayItems.firstOrNull { it.id == id } }
        ?: todayItems.firstOrNull { it.status == "planned" && !it.isCompleted }
    val metrics = state.metrics
    val waterTotal = state.water?.totalMl ?: metrics.waterMl
    val waterGoal = state.water?.goalMl ?: metrics.waterGoalMl
    val weight = state.profile?.profile?.currentWeightKg
    val locale = Locale("ru")
    val dateHeadline = remember(state.selectedDate) {
        runCatching {
            val d = LocalDate.parse(state.selectedDate)
            val weekday = d.dayOfWeek.getDisplayName(TextStyle.FULL, locale)
                .replaceFirstChar { it.titlecase(locale) }
            val formatted = d.format(DateTimeFormatter.ofPattern("d MMMM", locale))
            "$weekday, $formatted"
        }.getOrDefault(state.selectedDate)
    }

    var replaceTarget by remember { mutableStateOf<MealPlanItemDto?>(null) }
    var showWeight by remember { mutableStateOf(false) }
    var weightInput by remember { mutableStateOf(weight?.toString().orEmpty()) }

    if (replaceTarget != null) {
        ReplaceReasonDialog(
            onDismiss = { replaceTarget = null },
            onConfirm = { reason ->
                replaceTarget?.let { onReplace(it, reason) }
                replaceTarget = null
            },
        )
    }
    LaunchedEffect(replaceNonce) {
        if (replaceNonce > 0) {
            replaceTarget = nextMeal ?: todayItems.firstOrNull { !it.isCompleted && it.status != "skipped" }
        }
    }
    if (showWeight) {
        WeightDialog(
            initial = weightInput,
            onDismiss = { showWeight = false },
            onConfirm = { value ->
                onAddWeight(value)
                showWeight = false
            },
        )
    }

    if (state.aiPreview !is AiPreviewState.Idle) {
        AiPreviewSheet(
            state = state.aiPreview,
            onDismiss = onDismissAi,
            onSelectCandidate = onSelectAiCandidate,
            onConfirmRecommendations = onConfirmAiRecommendation,
            onConfirmAdaptDay = onConfirmAdaptDay,
        )
    }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(FoodAIColors.Background)
            .padding(horizontal = FoodAIDimens.ScreenPadding),
        verticalArrangement = Arrangement.spacedBy(FoodAIDimens.Space16),
        contentPadding = PaddingValues(top = FoodAIDimens.Space16, bottom = FoodAIDimens.Space32),
    ) {
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.Top,
            ) {
                Column(Modifier.weight(1f)) {
                    Text(dateHeadline, style = FoodAITypography.titleLarge)
                    Text(
                        "Сегодня · твой план питания",
                        style = FoodAITypography.bodyMedium,
                        color = FoodAIColors.TextSecondary,
                    )
                }
                Row(verticalAlignment = Alignment.CenterVertically) {
                    IconButton(onClick = onOpenDiary) {
                        Icon(
                            Icons.Outlined.MenuBook,
                            contentDescription = "Дневник",
                            tint = FoodAIColors.TextSecondary,
                        )
                    }
                    IconButton(onClick = onOpenShopping) {
                        Icon(
                            Icons.Outlined.ShoppingCart,
                            contentDescription = "Покупки",
                            tint = FoodAIColors.TextSecondary,
                        )
                    }
                    IconButton(onClick = onRefresh) {
                        Icon(
                            Icons.Outlined.Refresh,
                            contentDescription = "Обновить",
                            tint = FoodAIColors.Primary,
                        )
                    }
                }
            }
        }
        if (state.offlineCached) {
            item {
                Text(
                    "Нет соединения — показан сохранённый план",
                    color = FoodAIColors.Warning,
                    style = FoodAITypography.bodyMedium,
                )
            }
        }
        item {
            DayProgressCard(progress = progress, fallbackTargets = plan?.dailyTargets)
        }
        item {
            Text(
                "План не считается съеденным, пока вы не нажмёте «Съел».",
                style = FoodAITypography.bodySmall,
                color = FoodAIColors.TextSecondary,
            )
        }
        if (state.actionError != null) {
            item { Text(state.actionError, color = FoodAIColors.Error) }
        }
        if (state.infoMessage != null) {
            item { Text(state.infoMessage, color = FoodAIColors.Primary) }
        }
        item {
            Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text("Приёмы пищи", style = FoodAITypography.titleLarge)
                Text(
                    "Отмечай съеденное — калории, БЖУ и остаток дня посчитает сервер.",
                    style = FoodAITypography.bodySmall,
                    color = FoodAIColors.TextSecondary,
                )
            }
        }
        if (todayItems.isEmpty()) {
            item {
                FoodAIEmptyState(
                    title = "Нет запланированных приёмов",
                    subtitle = "Откройте дневник, чтобы записать еду, или соберите план.",
                    actionLabel = "Дневник",
                    onAction = onOpenDiary,
                )
            }
        }
        items(todayItems, key = { it.id }) { item ->
            MealTimelineCard(
                item = item,
                highlighted = item.id == nextMeal?.id,
                onOpen = { onOpenRecipe(item.recipe.id, item.id) },
                onComplete = { onComplete(item) },
                onSkip = { onSkip(item) },
                onReplace = { replaceTarget = item },
            )
        }
        item {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(FoodAIShapes.Card)
                    .background(FoodAIColors.Surface)
                    .padding(horizontal = FoodAIDimens.Space16, vertical = FoodAIDimens.Space12),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column {
                    Text("Вода", style = FoodAITypography.titleMedium)
                    Text(
                        String.format("%.1f из %.1f л", waterTotal / 1000f, waterGoal / 1000f),
                        style = FoodAITypography.bodyMedium,
                        color = FoodAIColors.TextSecondary,
                    )
                }
                Row(horizontalArrangement = Arrangement.spacedBy(FoodAIDimens.Space8)) {
                    TextButton(onClick = { onAddWater(250) }) {
                        Text("+250 мл", color = FoodAIColors.Primary)
                    }
                    if (waterTotal > 0) {
                        TextButton(onClick = onUndoWater) {
                            Text("Отменить", color = FoodAIColors.TextSecondary)
                        }
                    }
                }
            }
        }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(FoodAIDimens.Space8)) {
                TodayMetric(
                    title = "Шаги",
                    value = when {
                        metrics.stepsPermissionNeeded -> "Разрешить"
                        metrics.stepsAvailable || metrics.steps > 0 -> "%,d".format(metrics.steps)
                        else -> "Нет датчика"
                    },
                    icon = Icons.AutoMirrored.Outlined.DirectionsWalk,
                    modifier = Modifier.weight(1f),
                    onClick = if (metrics.stepsPermissionNeeded) onRequestStepsPermission else null,
                )
                TodayMetric(
                    title = "Вес",
                    value = weight?.let { "${it.toInt()} кг" } ?: "—",
                    icon = Icons.Outlined.MonitorWeight,
                    modifier = Modifier.weight(1f),
                    onClick = {
                        weightInput = weight?.toString().orEmpty()
                        showWeight = true
                    },
                )
                TodayMetric(
                    title = "Прогресс",
                    value = "Смотреть",
                    icon = Icons.AutoMirrored.Outlined.ShowChart,
                    modifier = Modifier.weight(1f),
                    onClick = onOpenProgress,
                )
            }
        }
    }
}

@Composable
private fun DayProgressCard(
    progress: DayProgressDto?,
    fallbackTargets: com.foodai.app.core.network.DailyTargetsDto?,
) {
    val consumed = progress?.consumedKcal ?: 0
    val target = progress?.targetKcal ?: fallbackTargets?.caloriesKcal ?: 0
    val remaining = progress?.remainingKcal ?: (target - consumed).coerceAtLeast(0)
    val overTarget = progress?.overTargetKcal
        ?: (consumed - target).coerceAtLeast(0).takeIf { target > 0 } ?: 0
    val plannedRemaining = progress?.plannedRemainingKcal ?: 0
    val fromDiary = progress?.fromDiaryKcal ?: 0
    val ring = if (target > 0) min(1f, consumed.toFloat() / target.toFloat()) else 0f
    val protein = progress?.protein
    val fat = progress?.fat
    val carbs = progress?.carbs
    val headline = when {
        target <= 0 -> "Цель не задана"
        overTarget > 0 -> "+${formatKcal(overTarget)} ккал сверх цели"
        else -> "${formatKcal(remaining)} ккал осталось"
    }
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(FoodAIShapes.CardLarge)
            .background(FoodAIColors.Surface)
            .padding(FoodAIDimens.Space16),
    ) {
        Text(
            if (target > 0) "Цель · ${formatKcal(target)} ккал" else "Калории",
            style = FoodAITypography.labelMedium,
            color = FoodAIColors.TextSecondary,
        )
        Spacer(Modifier.height(FoodAIDimens.Space8))
        Row(verticalAlignment = Alignment.CenterVertically) {
            CalorieRing(progress = ring, eaten = consumed, target = target)
            Spacer(Modifier.width(FoodAIDimens.Space16))
            Column(Modifier.weight(1f)) {
                Text("Съедено", style = FoodAITypography.labelSmall, color = FoodAIColors.TextSecondary)
                Text(
                    "${formatKcal(consumed)} / ${formatKcal(target)} ккал",
                    style = FoodAITypography.headlineSmall,
                    fontWeight = FontWeight.Bold,
                    color = if (overTarget > 0) FoodAIColors.Warning else FoodAIColors.TextPrimary,
                )
                Text(
                    headline,
                    style = FoodAITypography.titleMedium,
                    color = if (overTarget > 0) FoodAIColors.Warning else FoodAIColors.Primary,
                )
                if (fromDiary > 0) {
                    Text(
                        "Вне плана: ${formatKcal(fromDiary)} ккал",
                        style = FoodAITypography.bodySmall,
                        color = FoodAIColors.TextSecondary,
                    )
                }
                if (plannedRemaining > 0) {
                    Text(
                        "В плане ещё ${formatKcal(plannedRemaining)} ккал — не съедено",
                        style = FoodAITypography.bodySmall,
                        color = FoodAIColors.TextSecondary,
                    )
                }
            }
        }
        Spacer(Modifier.height(FoodAIDimens.Space16))
        FoodAIMacroBar(
            label = "Белки",
            current = (protein?.consumedG ?: 0.0).toInt(),
            target = (protein?.targetG ?: fallbackTargets?.proteinG ?: 0.0).toInt(),
            color = FoodAIColors.Primary,
        )
        Spacer(Modifier.height(FoodAIDimens.Space8))
        FoodAIMacroBar(
            label = "Жиры",
            current = (fat?.consumedG ?: 0.0).toInt(),
            target = (fat?.targetG ?: fallbackTargets?.fatG ?: 0.0).toInt(),
            color = FoodAIColors.Warning,
        )
        Spacer(Modifier.height(FoodAIDimens.Space8))
        FoodAIMacroBar(
            label = "Углеводы",
            current = (carbs?.consumedG ?: 0.0).toInt(),
            target = (carbs?.targetG ?: fallbackTargets?.carbohydrateG ?: 0.0).toInt(),
            color = FoodAIColors.Gold,
        )
    }
}

@Composable
private fun DiaryLogRow(
    log: NutritionLogDto,
    onDelete: () -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(FoodAIShapes.Card)
            .background(FoodAIColors.Surface)
            .padding(horizontal = FoodAIDimens.Space12, vertical = FoodAIDimens.Space12),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text(displayRecipeName(log.description), style = FoodAITypography.titleMedium, maxLines = 2)
            Text(
                "${log.caloriesKcal} ккал · ${mealTypeLabel(log.mealType)}",
                style = FoodAITypography.bodySmall,
                color = FoodAIColors.TextSecondary,
            )
        }
        TextButton(onClick = onDelete) {
            Text("Удалить", color = FoodAIColors.Error)
        }
    }
}

@Composable
private fun NextMealCard(
    item: MealPlanItemDto,
    onOpen: () -> Unit,
    onComplete: () -> Unit,
    onSkip: () -> Unit,
    onReplace: () -> Unit,
) {
    val title = displayRecipeName(item.recipe.name)
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(FoodAIShapes.Card)
            .background(FoodAIColors.Surface)
            .padding(FoodAIDimens.Space12),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .clickable(onClick = onOpen),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            RecipeImagePane(
                image = item.recipe.image,
                contentDescription = title,
                modifier = Modifier.size(64.dp).clip(FoodAIShapes.Tile),
                enforceAspect = false,
            )
            Spacer(Modifier.width(FoodAIDimens.Space12))
            Column(Modifier.weight(1f)) {
                Text(
                    mealTypeLabel(item.mealType),
                    style = FoodAITypography.labelMedium,
                    color = FoodAIColors.Primary,
                )
                Text(title, style = FoodAITypography.titleMedium, maxLines = 2)
                Text(
                    "${formatKcal(item.recipe.caloriesKcal)} ккал · ${item.recipe.cookTimeMinutes} мин",
                    style = FoodAITypography.bodySmall,
                    color = FoodAIColors.TextSecondary,
                )
            }
        }
        Spacer(Modifier.height(FoodAIDimens.Space8))
        Row(
            modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(FoodAIDimens.Space8),
        ) {
            TextButton(onClick = onComplete) {
                Text("Я съел", color = FoodAIColors.Primary)
            }
            TextButton(onClick = onSkip) {
                Text("Пропустить", color = FoodAIColors.TextSecondary)
            }
            TextButton(onClick = onReplace) {
                Text("Заменить", color = FoodAIColors.TextSecondary)
            }
        }
    }
}

@Composable
private fun MealTimelineCard(
    item: MealPlanItemDto,
    highlighted: Boolean,
    onOpen: () -> Unit,
    onComplete: () -> Unit,
    onSkip: () -> Unit,
    onReplace: () -> Unit,
) {
    val statusLabel = mealStatusLabel(item)
    val title = displayRecipeName(item.recipe.name)
    val accent = when {
        item.status == "completed" || item.isCompleted -> FoodAIColors.Success
        item.status == "skipped" -> FoodAIColors.TextMuted
        item.status == "replaced" -> FoodAIColors.Warning
        highlighted -> FoodAIColors.Primary
        else -> FoodAIColors.TextMuted
    }
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(FoodAIShapes.Card)
            .background(FoodAIColors.Surface)
            .padding(FoodAIDimens.Space12),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().clickable(onClick = onOpen),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                modifier = Modifier
                    .width(4.dp)
                    .height(48.dp)
                    .clip(FoodAIShapes.Pill)
                    .background(accent),
            )
            Spacer(Modifier.width(FoodAIDimens.Space12))
            Column(Modifier.weight(1f)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                ) {
                    Text(
                        mealTypeLabel(item.mealType),
                        style = FoodAITypography.labelMedium,
                        color = FoodAIColors.TextSecondary,
                    )
                    Text(statusLabel, style = FoodAITypography.labelSmall, color = accent)
                }
                Text(title, style = FoodAITypography.titleMedium, maxLines = 1)
                Text(
                    "${item.recipe.caloriesKcal} ккал · ${item.recipe.cookTimeMinutes} мин",
                    style = FoodAITypography.bodySmall,
                    color = FoodAIColors.TextSecondary,
                )
            }
            Icon(Icons.Outlined.ChevronRight, null, tint = FoodAIColors.TextMuted)
        }
        if (item.status == "planned" || (!item.isCompleted && item.status != "skipped" && item.status != "completed")) {
            Spacer(Modifier.height(FoodAIDimens.Space8))
            Row(horizontalArrangement = Arrangement.spacedBy(FoodAIDimens.Space12)) {
                Text(
                    "Я съел",
                    color = FoodAIColors.Primary,
                    style = FoodAITypography.labelMedium,
                    modifier = Modifier.clickable(onClick = onComplete),
                )
                Text(
                    "Пропустить",
                    color = FoodAIColors.TextSecondary,
                    style = FoodAITypography.labelMedium,
                    modifier = Modifier.clickable(onClick = onSkip),
                )
                Text(
                    "Заменить",
                    color = FoodAIColors.TextSecondary,
                    style = FoodAITypography.labelMedium,
                    modifier = Modifier.clickable(onClick = onReplace),
                )
            }
        }
    }
}

@Composable
private fun ReplaceReasonDialog(
    onDismiss: () -> Unit,
    onConfirm: (String) -> Unit,
) {
    var selected by remember { mutableStateOf("other") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Почему заменить?") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                replaceReasons.forEach { (key, label) ->
                    FilterChip(
                        selected = selected == key,
                        onClick = { selected = key },
                        label = { Text(label) },
                        colors = FilterChipDefaults.filterChipColors(
                            selectedContainerColor = FoodAIColors.PrimarySoft,
                        ),
                    )
                }
            }
        },
        confirmButton = {
            TextButton(onClick = { onConfirm(selected) }) {
                Text("Заменить", color = FoodAIColors.Primary)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Отмена") }
        },
    )
}

@Composable
private fun WeightDialog(
    initial: String,
    onDismiss: () -> Unit,
    onConfirm: (Double) -> Unit,
) {
    var value by remember { mutableStateOf(initial) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Вес сегодня") },
        text = {
            OutlinedTextField(
                value = value,
                onValueChange = { value = it.filter { ch -> ch.isDigit() || ch == '.' || ch == ',' } },
                label = { Text("кг") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                modifier = Modifier.fillMaxWidth(),
            )
        },
        confirmButton = {
            TextButton(
                onClick = {
                    value.replace(',', '.').toDoubleOrNull()?.let(onConfirm)
                },
            ) { Text("Сохранить", color = FoodAIColors.Primary) }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Отмена") }
        },
    )
}

@Composable
private fun CalorieRing(progress: Float, eaten: Int, target: Int) {
    val trackColor = FoodAIColors.Divider
    val activeColor = FoodAIColors.Primary
    Box(contentAlignment = Alignment.Center, modifier = Modifier.size(96.dp)) {
        androidx.compose.foundation.Canvas(modifier = Modifier.size(96.dp)) {
            val stroke = 10.dp.toPx()
            drawArc(
                color = trackColor,
                startAngle = -90f,
                sweepAngle = 360f,
                useCenter = false,
                style = Stroke(width = stroke, cap = StrokeCap.Round),
            )
            drawArc(
                color = activeColor,
                startAngle = -90f,
                sweepAngle = 360f * progress.coerceIn(0f, 1f),
                useCenter = false,
                style = Stroke(width = stroke, cap = StrokeCap.Round),
            )
        }
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(
                if (target > 0) formatKcal(eaten) else "—",
                style = FoodAITypography.titleMedium,
                fontWeight = FontWeight.Bold,
            )
            Text(
                if (target > 0) "из ${formatKcal(target)}" else "ккал",
                style = FoodAITypography.labelSmall,
            )
        }
    }
}

@Composable
private fun TodayMetric(
    title: String,
    value: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    modifier: Modifier = Modifier,
    onClick: (() -> Unit)? = null,
) {
    Column(
        modifier = modifier
            .clip(FoodAIShapes.Card)
            .background(FoodAIColors.Surface)
            .border(1.dp, FoodAIColors.Divider, FoodAIShapes.Card)
            .then(if (onClick != null) Modifier.clickable(onClick = onClick) else Modifier)
            .padding(vertical = FoodAIDimens.Space12, horizontal = FoodAIDimens.Space8),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Icon(icon, null, tint = FoodAIColors.Primary, modifier = Modifier.size(20.dp))
        Spacer(Modifier.height(4.dp))
        Text(value, style = FoodAITypography.labelMedium, color = FoodAIColors.TextPrimary, maxLines = 1)
        Text(title, style = FoodAITypography.labelSmall)
    }
}

@Composable
fun WeekRoute(
    onOpenRecipe: (recipeId: String, itemId: String) -> Unit,
    onOpenShopping: () -> Unit = {},
    viewModel: WeekViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    when {
        state.loading || state.generating -> LoadingPane(
            if (state.generating) "Создаём план питания…" else "Загружаем неделю…",
        )
        state.error != null && state.plan == null -> ErrorPane(
            message = state.error ?: "Ошибка",
            onRetry = viewModel::refresh,
            onSecondary = if (state.missingPlan) viewModel::generatePlan else null,
            secondaryLabel = "Создать план на неделю",
        )
        else -> WeekScreen(
            state = state,
            onSelectDate = viewModel::selectDate,
            onRefresh = viewModel::refresh,
            onRebuild = viewModel::rebuildPlan,
            onOpenRecipe = onOpenRecipe,
            onOpenShopping = onOpenShopping,
        )
    }
}

@Composable
fun WeekScreen(
    state: WeekUiState,
    onSelectDate: (String) -> Unit,
    onRefresh: () -> Unit,
    onRebuild: () -> Unit,
    onOpenRecipe: (recipeId: String, itemId: String) -> Unit,
    onOpenShopping: () -> Unit = {},
) {
    val plan = state.plan
    val goalKcal = state.profile?.goal?.calorieTargetKcal
        ?: plan?.dailyTargets?.caloriesKcal
    val summaryDays = plan?.weekSummary?.days.orEmpty()
    val dates = state.weekDates.ifEmpty {
        summaryDays.map { it.date }.ifEmpty {
            plan?.items.orEmpty().map { it.date }.distinct().sorted()
        }
    }
    val selectedDay = state.selectedDate.take(10)
    val dayByDate = summaryDays.associateBy { it.date.take(10) }
    val dayItems = plan?.items.orEmpty()
        .filter { it.date.take(10) == selectedDay }
        .sortedBy { it.sortOrder }
    val selectedSummary = dayByDate[selectedDay]
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(FoodAIColors.Background)
            .padding(horizontal = FoodAIDimens.ScreenPadding),
        verticalArrangement = Arrangement.spacedBy(FoodAIDimens.Space16),
        contentPadding = PaddingValues(top = FoodAIDimens.Space16, bottom = FoodAIDimens.Space32),
    ) {
        item {
            Column(verticalArrangement = Arrangement.spacedBy(FoodAIDimens.Space4)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.Top,
                ) {
                    Column(Modifier.weight(1f)) {
                        Text("План на неделю", style = FoodAITypography.headlineMedium)
                        Text(
                            "Блюда на каждый день. В калории дня попадает только съеденное.",
                            style = FoodAITypography.bodyMedium,
                            color = FoodAIColors.TextSecondary,
                        )
                    }
                    IconButton(onClick = onRefresh) {
                        Icon(
                            Icons.Outlined.Refresh,
                            contentDescription = "Обновить план на неделю",
                            tint = FoodAIColors.Primary,
                        )
                    }
                }
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        if (goalKcal != null) "Цель ${formatKcal(goalKcal)} ккал/день · ${dates.size} дн." else "${dates.size} дн.",
                        style = FoodAITypography.bodySmall,
                        color = FoodAIColors.TextSecondary,
                    )
                    TextButton(onClick = onRebuild) {
                        Text("Пересобрать", color = FoodAIColors.Primary)
                    }
                }
                if (state.actionError != null) {
                    Text(state.actionError, color = FoodAIColors.Error)
                }
                if (state.infoMessage != null) {
                    Text(state.infoMessage, color = FoodAIColors.Primary)
                }
            }
        }
        item {
            LazyRow(horizontalArrangement = Arrangement.spacedBy(FoodAIDimens.Space8)) {
                items(dates, key = { it }) { date ->
                    val dayKey = date.take(10)
                    val selected = dayKey == selectedDay
                    val day = dayByDate[dayKey]
                    val todayKey = LocalDate.now().toString()
                    val isToday = dayKey == todayKey
                    val dayLabel = runCatching {
                        val d = LocalDate.parse(dayKey)
                        val dow = d.dayOfWeek.getDisplayName(TextStyle.SHORT, Locale("ru"))
                            .replace(".", "")
                            .uppercase(Locale("ru"))
                        "${d.dayOfMonth} $dow"
                    }.getOrDefault(dayKey.takeLast(5))
                    val status = day?.status ?: state.dayStatuses[date] ?: state.dayStatuses[dayKey] ?: "missing"
                    Box(
                        modifier = Modifier
                            .widthIn(min = 68.dp)
                            .clip(FoodAIShapes.Card)
                            .background(
                                when {
                                    selected -> FoodAIColors.PrimaryLight
                                    isToday -> FoodAIColors.PrimarySoft
                                    else -> FoodAIColors.Surface
                                },
                            )
                            .border(
                                width = 1.dp,
                                color = if (isToday && !selected) {
                                    FoodAIColors.Primary
                                } else {
                                    FoodAIColors.Divider
                                },
                                shape = FoodAIShapes.Card,
                            )
                            .clickable { onSelectDate(dayKey) }
                            .padding(horizontal = 12.dp, vertical = 10.dp),
                    ) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            if (isToday) {
                                Text(
                                    "Сегодня",
                                    color = FoodAIColors.Primary,
                                    style = FoodAITypography.labelSmall,
                                )
                            }
                            Text(
                                dayLabel,
                                color = if (selected) FoodAIColors.PrimaryDark else FoodAIColors.TextPrimary,
                                style = FoodAITypography.labelLarge,
                            )
                            Text(
                                weekChipSubtitle(day, status),
                                color = FoodAIColors.TextSecondary,
                                style = FoodAITypography.labelSmall,
                            )
                        }
                    }
                }
            }
        }
        item {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(FoodAIShapes.Card)
                    .background(FoodAIColors.Surface)
                    .padding(FoodAIDimens.Space16),
                verticalArrangement = Arrangement.spacedBy(FoodAIDimens.Space12),
            ) {
                Text("Итоги недели", style = FoodAITypography.titleMedium)
                if (summaryDays.isNotEmpty()) {
                    val plannedDays = summaryDays.count { it.status != "missing" }
                    val avgKcal = summaryDays.map { it.caloriesKcal }.average().toInt()
                    val completed = summaryDays.sumOf { it.completedMeals }
                    val weekCost = summaryDays.mapNotNull { it.estimatedCostAmount }.sum()
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                    ) {
                        WeekStat("Запланировано", "$plannedDays из ${summaryDays.size}")
                        WeekStat("В среднем", "${formatKcal(avgKcal)} ккал")
                        WeekStat("Съедено", "$completed")
                    }
                    if (weekCost > 0) {
                        Text(
                            "≈ ${formatMoney(weekCost)} ₽ на неделю",
                            style = FoodAITypography.bodySmall,
                            color = FoodAIColors.TextSecondary,
                        )
                    }
                } else {
                    Text(
                        "Нет данных за неделю",
                        style = FoodAITypography.bodySmall,
                        color = FoodAIColors.TextSecondary,
                    )
                }
            }
        }
        if (selectedSummary != null) {
            item {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(FoodAIShapes.Card)
                        .background(FoodAIColors.Surface)
                        .padding(FoodAIDimens.Space16),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column {
                        Text(
                            "Выбранный день",
                            style = FoodAITypography.labelMedium,
                            color = FoodAIColors.TextSecondary,
                        )
                        Text("${formatKcal(selectedSummary.caloriesKcal)} ккал", style = FoodAITypography.titleLarge)
                        Text(
                            "Б ${selectedSummary.proteinG.toInt()} г",
                            style = FoodAITypography.bodySmall,
                            color = FoodAIColors.TextSecondary,
                        )
                    }
                    Column(horizontalAlignment = Alignment.End) {
                        Text(
                            "${selectedSummary.completedMeals} из ${selectedSummary.plannedMeals}",
                            style = FoodAITypography.titleMedium,
                        )
                        Text(
                            "приёмов съедено",
                            style = FoodAITypography.labelSmall,
                            color = FoodAIColors.TextSecondary,
                        )
                        selectedSummary.estimatedCostAmount?.let { cost ->
                            Text(
                                "≈ ${formatMoney(cost)} ₽",
                                style = FoodAITypography.bodySmall,
                                color = FoodAIColors.TextSecondary,
                            )
                        }
                    }
                }
            }
        }
        if (dayItems.isEmpty()) {
            item {
                FoodAIEmptyState(
                    title = "Нет блюд на этот день",
                    subtitle = "Выберите другую дату или пересоберите план.",
                )
            }
        }
        items(dayItems, key = { it.id }) { item ->
            MealItemCard(
                item = item,
                onOpen = { onOpenRecipe(item.recipe.id, item.id) },
                onComplete = null,
                onReplace = null,
            )
        }
        item {
            FoodAIOutlinedButton(
                label = "Открыть список покупок",
                onClick = onOpenShopping,
            )
        }
    }
}

@Composable
private fun WeekStat(label: String, value: String) {
    Column {
        Text(value, style = FoodAITypography.titleMedium)
        Text(label, style = FoodAITypography.labelSmall, color = FoodAIColors.TextSecondary)
    }
}

private fun weekChipSubtitle(day: WeekDayDto?, status: String): String {
    if (day != null && day.caloriesKcal > 0) {
        return "${formatKcal(day.caloriesKcal)} ккал"
    }
    return when (status) {
        "planned" -> "есть"
        "generating" -> "…"
        else -> "нет"
    }
}

@Composable
fun MealItemCard(
    item: MealPlanItemDto,
    onOpen: () -> Unit,
    onComplete: (() -> Unit)?,
    onReplace: (() -> Unit)?,
) {
    val recipe = item.recipe
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(FoodAIShapes.CardLarge)
            .background(FoodAIColors.Surface)
            .border(1.dp, FoodAIColors.Divider, FoodAIShapes.CardLarge)
            .clickable(onClick = onOpen)
            .padding(FoodAIDimens.Space12),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box {
            RecipeImagePane(
                image = recipe.image,
                contentDescription = recipe.name,
                modifier = Modifier
                    .size(72.dp)
                    .clip(FoodAIShapes.Tile),
                enforceAspect = false,
            )
            if (item.isCompleted) {
                Box(modifier = Modifier.align(Alignment.TopEnd).padding(4.dp)) {
                    FoodAIStatusDot(complete = true)
                }
            }
        }
        Spacer(Modifier.width(FoodAIDimens.Space12))
        Column(modifier = Modifier.weight(1f)) {
            Text(
                mealTypeLabel(item.mealType),
                style = FoodAITypography.labelMedium,
                color = FoodAIColors.Primary,
            )
            Text(recipe.name, style = FoodAITypography.titleMedium, maxLines = 2)
            Text(
                "${formatKcal(recipe.caloriesKcal)} ккал · ${recipe.cookTimeMinutes} мин",
                style = FoodAITypography.bodySmall,
            )
            Spacer(Modifier.height(FoodAIDimens.Space8))
            Row(horizontalArrangement = Arrangement.spacedBy(FoodAIDimens.Space12)) {
                Text(
                    "Рецепт",
                    color = FoodAIColors.Primary,
                    style = FoodAITypography.labelMedium,
                    modifier = Modifier.clickable(onClick = onOpen),
                )
                if (onComplete != null) {
                    Text(
                        if (item.isCompleted) "Снять" else "Съедено",
                        color = FoodAIColors.Primary,
                        style = FoodAITypography.labelMedium,
                        modifier = Modifier.clickable(onClick = onComplete),
                    )
                }
                if (onReplace != null) {
                    Text(
                        "Заменить",
                        color = FoodAIColors.TextSecondary,
                        style = FoodAITypography.labelMedium,
                        modifier = Modifier.clickable(onClick = onReplace),
                    )
                }
            }
        }
        Icon(Icons.Outlined.ChevronRight, null, tint = FoodAIColors.TextMuted)
    }
}

fun mealTypeLabel(raw: String): String = when (raw) {
    "breakfast" -> "Завтрак"
    "lunch" -> "Обед"
    "dinner" -> "Ужин"
    "snack" -> "Перекус"
    else -> raw
}

fun mealStatusLabel(item: MealPlanItemDto): String = when {
    item.status == "completed" || item.isCompleted -> "Съедено"
    item.status == "skipped" -> "Пропущено"
    item.status == "replaced" -> "Заменено"
    else -> "Запланировано"
}
