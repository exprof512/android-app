package com.foodai.app.feature.plan

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.ChevronRight
import androidx.compose.material.icons.outlined.MonitorWeight
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.ShoppingCart
import androidx.compose.material.icons.outlined.WaterDrop
import androidx.compose.material.icons.automirrored.outlined.DirectionsWalk
import androidx.compose.material.icons.automirrored.outlined.ShowChart
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import android.Manifest
import android.os.Build
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.foodai.app.core.network.MealPlanItemDto
import com.foodai.app.core.ui.ErrorPane
import com.foodai.app.core.ui.LoadingPane
import com.foodai.app.core.ui.RecipeImagePane
import com.foodai.app.core.ui.components.FoodAIEmptyState
import com.foodai.app.core.ui.components.FoodAIMacroBar
import com.foodai.app.core.ui.components.FoodAIOutlinedButton
import com.foodai.app.core.ui.components.FoodAIStatusDot
import com.foodai.app.core.ui.components.FoodAITipBanner
import com.foodai.app.core.ui.theme.FoodAIColors
import com.foodai.app.core.ui.theme.FoodAIDimens
import com.foodai.app.core.ui.theme.FoodAIShapes
import com.foodai.app.core.ui.theme.FoodAITypography
import kotlin.math.min

@Composable
fun TodayRoute(
    onOpenRecipe: (recipeId: String, itemId: String) -> Unit,
    onOpenShopping: () -> Unit = {},
    onOpenProgress: () -> Unit = {},
    viewModel: TodayViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { granted -> viewModel.onStepsPermissionResult(granted) }
    LaunchedEffect(Unit) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            permissionLauncher.launch(Manifest.permission.ACTIVITY_RECOGNITION)
        } else {
            viewModel.onStepsPermissionResult(true)
        }
    }
    when {
        state.loading || state.generating -> LoadingPane(
            if (state.generating) "Создаём план питания…" else "Загружаем сегодня…",
        )
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
            onReplace = viewModel::replace,
            onAddWater = viewModel::addWater,
            onAddSnack = { viewModel.addManualSnack("Перекус", 150) },
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
        )
    }
}

@Composable
fun TodayScreen(
    state: TodayUiState,
    onRefresh: () -> Unit,
    onRebuild: () -> Unit,
    onComplete: (MealPlanItemDto) -> Unit,
    onReplace: (MealPlanItemDto) -> Unit,
    onAddWater: () -> Unit,
    onAddSnack: () -> Unit = {},
    onRequestStepsPermission: () -> Unit = {},
    onOpenRecipe: (recipeId: String, itemId: String) -> Unit,
    onOpenShopping: () -> Unit = {},
    onOpenProgress: () -> Unit = {},
) {
    val plan = state.plan
    val goal = state.profile?.goal
    val todayItems = plan?.items.orEmpty()
    val eaten = todayItems.filter { it.isCompleted }.sumOf { it.recipe.caloriesKcal }
    val target = goal?.calorieTargetKcal
        ?: plan?.dailyTargets?.caloriesKcal
        ?: 0
    val remaining = (target - eaten).coerceAtLeast(0)
    val progress = if (target > 0) min(1f, eaten.toFloat() / target.toFloat()) else 0f
    val macros = goal?.macroTargetsG
    val weight = state.profile?.profile?.currentWeightKg
    val metrics = state.metrics
    val waterLiters = metrics.waterMl / 1000f

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
                    Text("Привет! 👋", style = FoodAITypography.headlineMedium)
                    Text(
                        "Вкусное и полезное питание сегодня — это шаг к большим целям!",
                        style = FoodAITypography.bodyMedium,
                        color = FoodAIColors.TextSecondary,
                    )
                }
                IconButton(onClick = onRefresh) {
                    Icon(
                        Icons.Outlined.Refresh,
                        contentDescription = "Обновить план на сегодня",
                        tint = FoodAIColors.Primary,
                    )
                }
            }
        }
        item {
            FoodAITipBanner(
                tipId = "today_meals",
                text = "Отмечай съеденное — калории и прогресс обновятся автоматически. Нажми на блюдо, чтобы открыть рецепт.",
            )
        }
        item {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(FoodAIShapes.CardLarge)
                    .background(FoodAIColors.PrimarySoft)
                    .padding(FoodAIDimens.Space16),
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    CalorieRing(progress = progress, eaten = eaten, target = target)
                    Spacer(Modifier.width(FoodAIDimens.Space16))
                    Column(Modifier.weight(1f)) {
                        Text("Калории на сегодня", style = FoodAITypography.labelMedium)
                        Text(
                            if (target > 0) "Ещё $remaining ккал" else "Цель не задана",
                            style = FoodAITypography.titleLarge,
                            fontWeight = FontWeight.Bold,
                        )
                        if (macros != null) {
                            Spacer(Modifier.height(FoodAIDimens.Space12))
                            FoodAIMacroBar(
                                label = "Белки",
                                current = (macros.protein * progress).toInt(),
                                target = macros.protein,
                                color = FoodAIColors.Primary,
                            )
                            Spacer(Modifier.height(FoodAIDimens.Space8))
                            FoodAIMacroBar(
                                label = "Жиры",
                                current = (macros.fat * progress).toInt(),
                                target = macros.fat,
                                color = FoodAIColors.Warning,
                            )
                            Spacer(Modifier.height(FoodAIDimens.Space8))
                            FoodAIMacroBar(
                                label = "Углеводы",
                                current = (macros.carbohydrate * progress).toInt(),
                                target = macros.carbohydrate,
                                color = androidx.compose.ui.graphics.Color(0xFF8B7CF6),
                            )
                        }
                    }
                }
            }
        }
        if (state.actionError != null) {
            item { Text(state.actionError, color = FoodAIColors.Error) }
        }
        if (state.infoMessage != null) {
            item { Text(state.infoMessage, color = FoodAIColors.Primary) }
        }
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text("Приёмы пищи", style = FoodAITypography.titleLarge)
                TextButton(onClick = onRebuild) {
                    Text("Пересобрать", color = FoodAIColors.Primary)
                }
            }
        }
        if (todayItems.isEmpty()) {
            item {
                FoodAIEmptyState(
                    title = "Нет приёмов пищи",
                    subtitle = "Создайте план на неделю, чтобы увидеть меню на сегодня.",
                    actionLabel = "Пересобрать план",
                    onAction = onRebuild,
                )
            }
        }
        items(todayItems, key = { it.id }) { item ->
            MealItemCard(
                item = item,
                onOpen = { onOpenRecipe(item.recipe.id, item.id) },
                onComplete = { onComplete(item) },
                onReplace = { onReplace(item) },
            )
        }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(FoodAIDimens.Space8)) {
                TodayMetric(
                    title = "Вода",
                    value = String.format("%.1f / %.0f л", waterLiters, metrics.waterGoalMl / 1000f),
                    icon = Icons.Outlined.WaterDrop,
                    modifier = Modifier.weight(1f),
                    onClick = onAddWater,
                )
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
                    onClick = onOpenProgress,
                )
                TodayMetric(
                    title = "Прогресс",
                    value = "Смотреть",
                    icon = Icons.AutoMirrored.Outlined.ShowChart,
                    modifier = Modifier.weight(1f),
                    onClick = onOpenProgress,
                )
            }
            Text(
                "Нажми «Вода», чтобы добавить 250 мл. Шаги берутся с шагомера телефона.",
                style = FoodAITypography.labelSmall,
                color = FoodAIColors.TextMuted,
            )
        }
        item {
            val logKcal = state.nutritionLogs.sumOf { it.caloriesKcal }
            Text("Дневник питания", style = FoodAITypography.titleLarge)
            Text(
                "Дополнительно в дневнике: $logKcal ккал · ${state.nutritionLogs.size} записей",
                style = FoodAITypography.bodySmall,
                color = FoodAIColors.TextSecondary,
            )
            state.nutritionLogs.take(5).forEach { log ->
                Text(
                    "${log.mealType}: ${log.description} — ${log.caloriesKcal} ккал",
                    style = FoodAITypography.bodyMedium,
                )
            }
            TextButton(onClick = onAddSnack) {
                Text("Добавить перекус 150 ккал", color = FoodAIColors.Primary)
            }
        }
        item {
            FoodAIOutlinedButton(
                label = "Список покупок",
                onClick = onOpenShopping,
            )
        }
    }
}

@Composable
private fun CalorieRing(progress: Float, eaten: Int, target: Int) {
    Box(contentAlignment = Alignment.Center, modifier = Modifier.size(96.dp)) {
        androidx.compose.foundation.Canvas(modifier = Modifier.size(96.dp)) {
            val stroke = 10.dp.toPx()
            drawArc(
                color = FoodAIColors.Divider,
                startAngle = -90f,
                sweepAngle = 360f,
                useCenter = false,
                style = Stroke(width = stroke, cap = StrokeCap.Round),
            )
            drawArc(
                color = FoodAIColors.Primary,
                startAngle = -90f,
                sweepAngle = 360f * progress.coerceIn(0f, 1f),
                useCenter = false,
                style = Stroke(width = stroke, cap = StrokeCap.Round),
            )
        }
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(
                if (target > 0) "$eaten" else "—",
                style = FoodAITypography.titleMedium,
                fontWeight = FontWeight.Bold,
            )
            Text(
                if (target > 0) "из $target" else "ккал",
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
    val dates = state.weekDates.ifEmpty {
        plan?.items.orEmpty().map { it.date }.distinct().sorted()
    }
    val dayItems = plan?.items.orEmpty().filter { it.date == state.selectedDate }
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
                    Text("План на неделю", style = FoodAITypography.headlineMedium)
                    Text(
                        "Вкусное, полезное и разнообразное питание по твоим целям.",
                        style = FoodAITypography.bodyMedium,
                        color = FoodAIColors.TextSecondary,
                    )
                    if (goalKcal != null) {
                        Text(
                            "Цель: $goalKcal ккал/день · ${dates.size} дн.",
                            style = FoodAITypography.bodySmall,
                        )
                    }
                }
                IconButton(onClick = onRefresh) {
                    Icon(
                        Icons.Outlined.Refresh,
                        contentDescription = "Обновить план на неделю",
                        tint = FoodAIColors.Primary,
                    )
                }
            }
            TextButton(onClick = onRebuild) { Text("Пересобрать", color = FoodAIColors.Primary) }
            if (state.actionError != null) {
                Text(state.actionError, color = FoodAIColors.Error)
            }
            if (state.infoMessage != null) {
                Text(state.infoMessage, color = FoodAIColors.Primary)
            }
        }
        item {
            LazyRow(horizontalArrangement = Arrangement.spacedBy(FoodAIDimens.Space8)) {
                items(dates) { date ->
                    val selected = date == state.selectedDate
                    val dayLabel = runCatching {
                        val d = java.time.LocalDate.parse(date)
                        "${d.dayOfMonth}.${d.monthValue.toString().padStart(2, '0')}"
                    }.getOrDefault(date.takeLast(5))
                    Box(
                        modifier = Modifier
                            .clip(FoodAIShapes.Pill)
                            .background(if (selected) FoodAIColors.Primary else FoodAIColors.SurfaceMuted)
                            .clickable { onSelectDate(date) }
                            .padding(horizontal = 14.dp, vertical = 10.dp),
                    ) {
                        Text(
                            dayLabel,
                            color = if (selected) FoodAIColors.TextOnPrimary else FoodAIColors.TextPrimary,
                            style = FoodAITypography.labelLarge,
                        )
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
            Box(modifier = Modifier.align(Alignment.TopEnd).padding(4.dp)) {
                FoodAIStatusDot(complete = item.isCompleted)
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
                "${recipe.caloriesKcal} ккал · ${recipe.cookTimeMinutes} мин",
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
