package com.foodai.app.feature.progress

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.foodai.app.core.network.ProgressSeriesPointDto
import com.foodai.app.core.network.WeightEntryDto
import com.foodai.app.core.ui.ErrorPane
import com.foodai.app.core.ui.LoadingPane
import com.foodai.app.core.ui.theme.FoodAIColors
import com.foodai.app.core.ui.theme.FoodAIDimens
import com.foodai.app.core.ui.theme.FoodAITypography

@Composable
fun ProgressRoute(
    viewModel: ProgressViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    when {
        state.loading && state.summary == null -> LoadingPane("Загружаем прогресс…")
        state.error != null && state.summary == null -> ErrorPane(
            message = state.error ?: "Ошибка",
            onRetry = viewModel::refresh,
        )
        else -> ProgressScreen(
            state = state,
            onWeightInput = viewModel::onWeightInput,
            onSave = viewModel::saveWeight,
            onRefresh = viewModel::refresh,
            onPeriod = viewModel::setPeriod,
        )
    }
}

@Composable
fun ProgressScreen(
    state: ProgressUiState,
    onWeightInput: (String) -> Unit,
    onSave: () -> Unit,
    onRefresh: () -> Unit,
    onPeriod: (Int) -> Unit,
) {
    val summary = state.summary
    val entries = summary?.recentEntries.orEmpty().sortedBy { it.measuredAt }
    val series = summary?.series.orEmpty()
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(FoodAIColors.Background)
            .padding(FoodAIDimens.ScreenPadding),
        verticalArrangement = Arrangement.spacedBy(FoodAIDimens.Space16),
    ) {
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.Top,
            ) {
                Column(Modifier.weight(1f)) {
                    Text("Прогресс", style = FoodAITypography.headlineMedium)
                    Text(
                        "Ты делаешь это отлично! Маленькие шаги приводят к большим результатам.",
                        style = FoodAITypography.bodyMedium,
                        color = FoodAIColors.TextSecondary,
                    )
                }
                IconButton(onClick = onRefresh) {
                    Icon(
                        imageVector = Icons.Outlined.Refresh,
                        contentDescription = "Синхронизировать вес и калории с сервера",
                        tint = FoodAIColors.Primary,
                    )
                }
            }
        }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf(7, 30, 90).forEach { days ->
                    FilterChip(
                        selected = state.period == days,
                        onClick = { onPeriod(days) },
                        label = { Text("$days дн.") },
                        colors = FilterChipDefaults.filterChipColors(
                            selectedContainerColor = FoodAIColors.PrimarySoft,
                        ),
                    )
                }
            }
        }
        item {
            Text(
                "Текущий вес: ${summary?.currentWeightKg?.let { "$it кг" } ?: "—"}",
                style = FoodAITypography.titleLarge,
            )
            if (summary?.startWeightKg != null || summary?.targetWeightKg != null) {
                Text(
                    "Старт ${summary.startWeightKg ?: "—"} → цель ${summary.targetWeightKg ?: "—"} кг",
                    style = FoodAITypography.bodyMedium,
                    color = FoodAIColors.TextSecondary,
                )
            }
            summary?.progressPercent?.let {
                Text("Прогресс к цели: ${"%.0f".format(it)}%", style = FoodAITypography.bodyMedium)
            }
            summary?.trend7dKg?.let {
                val sign = if (it > 0) "+" else ""
                Text("Тренд 7 дней: $sign$it кг", style = FoodAITypography.bodyMedium)
            }
            summary?.weightDeltaKg?.let {
                val sign = if (it > 0) "+" else ""
                Text("Изменение с старта: $sign$it кг", style = FoodAITypography.bodyMedium)
            }
        }
        item {
            Text("Динамика за ${state.period} дн.", style = FoodAITypography.titleLarge)
            when {
                series.size >= 2 -> SeriesChart(
                    points = series,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(180.dp),
                )
                entries.size >= 2 -> WeightChart(
                    entries = entries,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(180.dp),
                )
                else -> Text(
                    "Добавьте минимум две записи — появится график.",
                    color = FoodAIColors.TextSecondary,
                    style = FoodAITypography.bodyMedium,
                )
            }
        }
        item {
            val today = summary?.today
            val goalKcal = summary?.calorieTargetKcal ?: today?.targetCaloriesKcal
            Text("Сегодня", style = FoodAITypography.titleLarge)
            if (today != null) {
                Text(
                    "Съедено ${today.consumedCaloriesKcal} / цель ${goalKcal ?: "—"} ккал" +
                        " · план ${today.plannedCaloriesKcal}",
                    style = FoodAITypography.bodyMedium,
                )
                Text(
                    "Б ${today.proteinG} / Ж ${today.fatG} / У ${today.carbohydrateG} · " +
                        "${today.completedMeals}/${today.plannedMeals} приёмов",
                    color = FoodAIColors.TextSecondary,
                    style = FoodAITypography.bodySmall,
                )
            } else {
                Text("Нет данных по плану на сегодня", color = FoodAIColors.TextSecondary)
            }
        }
        item {
            Text("Записать вес", style = FoodAITypography.titleLarge)
            OutlinedTextField(
                value = state.weightInput,
                onValueChange = onWeightInput,
                label = { Text("кг") },
                modifier = Modifier.fillMaxWidth(),
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                singleLine = true,
                shape = com.foodai.app.core.ui.theme.FoodAIShapes.Input,
            )
            if (state.actionError != null) {
                Text(state.actionError, color = FoodAIColors.Error)
            }
            Button(
                onClick = onSave,
                enabled = !state.saving,
                colors = ButtonDefaults.buttonColors(containerColor = FoodAIColors.Primary),
                shape = com.foodai.app.core.ui.theme.FoodAIShapes.Button,
            ) {
                Text(if (state.saving) "Сохраняем…" else "Сохранить")
            }
        }
        item {
            summary?.disclaimer?.takeIf { it.isNotBlank() }?.let {
                Text(it, style = FoodAITypography.bodySmall, color = FoodAIColors.TextSecondary)
            }
            summary?.warnings.orEmpty().forEach { warning ->
                Text(warning, color = FoodAIColors.TextSecondary)
            }
        }
        item {
            Text("История", style = FoodAITypography.titleLarge)
            if (entries.isEmpty()) {
                Text("Пока нет записей веса", color = FoodAIColors.TextSecondary)
            } else {
                entries.asReversed().forEach { entry ->
                    Spacer(Modifier.height(8.dp))
                    WeightRow(entry)
                }
            }
        }
    }
}

@Composable
private fun SeriesChart(
    points: List<ProgressSeriesPointDto>,
    modifier: Modifier = Modifier,
) {
    val lineColor = FoodAIColors.Primary
    val gridColor = FoodAIColors.Divider
    val pointColor = FoodAIColors.Gold
    Canvas(modifier = modifier) {
        val values = points.map { (it.weightKg ?: it.consumedKcal.toDouble()).toFloat() }
        val minW = (values.minOrNull() ?: 0f) - 1f
        val maxW = (values.maxOrNull() ?: 1f) + 1f
        val range = (maxW - minW).coerceAtLeast(1f)
        val padX = 24f
        val padY = 20f
        val chartW = size.width - padX * 2
        val chartH = size.height - padY * 2
        for (i in 0..3) {
            val y = padY + chartH * i / 3f
            drawLine(gridColor, Offset(padX, y), Offset(padX + chartW, y), strokeWidth = 2f)
        }
        val path = Path()
        values.forEachIndexed { index, value ->
            val x = padX + if (values.size == 1) chartW / 2f else chartW * index / (values.size - 1)
            val y = padY + chartH * (1f - (value - minW) / range)
            if (index == 0) path.moveTo(x, y) else path.lineTo(x, y)
        }
        drawPath(path, color = lineColor, style = Stroke(width = 5f, cap = StrokeCap.Round))
        values.forEachIndexed { index, value ->
            val x = padX + if (values.size == 1) chartW / 2f else chartW * index / (values.size - 1)
            val y = padY + chartH * (1f - (value - minW) / range)
            drawCircle(pointColor, radius = 7f, center = Offset(x, y))
            drawCircle(lineColor, radius = 3.5f, center = Offset(x, y))
        }
    }
}

@Composable
private fun WeightChart(
    entries: List<WeightEntryDto>,
    modifier: Modifier = Modifier,
) {
    val lineColor = FoodAIColors.Primary
    val gridColor = FoodAIColors.Divider
    val pointColor = FoodAIColors.Gold
    Canvas(modifier = modifier) {
        val weights = entries.map { it.weightKg.toFloat() }
        val minW = (weights.minOrNull() ?: 0f) - 1f
        val maxW = (weights.maxOrNull() ?: 1f) + 1f
        val range = (maxW - minW).coerceAtLeast(1f)
        val padX = 24f
        val padY = 20f
        val chartW = size.width - padX * 2
        val chartH = size.height - padY * 2

        for (i in 0..3) {
            val y = padY + chartH * i / 3f
            drawLine(gridColor, Offset(padX, y), Offset(padX + chartW, y), strokeWidth = 2f)
        }

        val path = Path()
        entries.forEachIndexed { index, entry ->
            val x = padX + if (entries.size == 1) chartW / 2f else chartW * index / (entries.size - 1)
            val y = padY + chartH * (1f - (entry.weightKg.toFloat() - minW) / range)
            if (index == 0) path.moveTo(x, y) else path.lineTo(x, y)
        }
        drawPath(path, color = lineColor, style = Stroke(width = 5f, cap = StrokeCap.Round))
        entries.forEachIndexed { index, entry ->
            val x = padX + if (entries.size == 1) chartW / 2f else chartW * index / (entries.size - 1)
            val y = padY + chartH * (1f - (entry.weightKg.toFloat() - minW) / range)
            drawCircle(pointColor, radius = 7f, center = Offset(x, y))
            drawCircle(lineColor, radius = 3.5f, center = Offset(x, y))
        }
    }
}

@Composable
private fun WeightRow(entry: WeightEntryDto) {
    Column(modifier = Modifier.fillMaxWidth()) {
        Text("${entry.weightKg} кг", style = FoodAITypography.titleMedium)
        Text(
            entry.measuredAt.take(16).replace('T', ' '),
            style = FoodAITypography.bodySmall,
            color = FoodAIColors.TextSecondary,
        )
        entry.note?.takeIf { it.isNotBlank() }?.let {
            Text(it, color = FoodAIColors.TextSecondary, style = FoodAITypography.bodySmall)
        }
    }
}
