package com.foodai.app.feature.progress

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
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
import androidx.compose.ui.draw.clip
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
import com.foodai.app.core.ui.formatKcal
import com.foodai.app.core.ui.theme.FoodAIColors
import com.foodai.app.core.ui.theme.FoodAIDimens
import com.foodai.app.core.ui.theme.FoodAIShapes
import com.foodai.app.core.ui.theme.FoodAITypography
import java.util.Locale

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
    val progress = ((summary?.progressPercent ?: 0.0) / 100.0).coerceIn(0.0, 1.0)
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(
            start = FoodAIDimens.ScreenPadding,
            end = FoodAIDimens.ScreenPadding,
            top = FoodAIDimens.Space16,
            bottom = FoodAIDimens.Space32,
        ),
        verticalArrangement = Arrangement.spacedBy(FoodAIDimens.Space12),
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
                        "Вес, калории и путь к цели — без гонки за цифрами.",
                        style = FoodAITypography.bodyMedium,
                        color = FoodAIColors.TextSecondary,
                    )
                }
                IconButton(onClick = onRefresh) {
                    Icon(
                        imageVector = Icons.Outlined.Refresh,
                        contentDescription = "Обновить прогресс",
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
                            selectedContainerColor = FoodAIColors.PrimaryLight,
                        ),
                    )
                }
            }
        }
        item {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(FoodAIShapes.CardLarge)
                    .background(FoodAIColors.Surface)
                    .padding(FoodAIDimens.Space16),
                verticalArrangement = Arrangement.spacedBy(FoodAIDimens.Space8),
            ) {
                Text(
                    "Текущий вес",
                    style = FoodAITypography.labelMedium,
                    color = FoodAIColors.TextSecondary,
                )
                Row(verticalAlignment = Alignment.Bottom) {
                    Text(
                        formatWeight(summary?.currentWeightKg),
                        style = FoodAITypography.displayMedium,
                    )
                    Spacer(Modifier.height(0.dp))
                    Text(
                        "  кг",
                        style = FoodAITypography.titleMedium,
                        color = FoodAIColors.TextSecondary,
                    )
                }
                val delta = summary?.weightDeltaKg
                Row(horizontalArrangement = Arrangement.spacedBy(FoodAIDimens.Space8)) {
                    if (delta != null) {
                        val sign = if (delta > 0) "+" else ""
                        Text(
                            "$sign${formatWeightValue(delta)} кг с начала",
                            style = FoodAITypography.bodySmall,
                            color = FoodAIColors.Primary,
                        )
                    }
                    Text(
                        "${(progress * 100).toInt()}% к цели",
                        style = FoodAITypography.bodySmall,
                        color = FoodAIColors.TextSecondary,
                    )
                }
                Spacer(Modifier.height(FoodAIDimens.Space4))
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(8.dp)
                        .clip(FoodAIShapes.Pill)
                        .background(FoodAIColors.SurfaceMuted),
                ) {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth(progress.toFloat())
                            .fillMaxHeight()
                            .clip(FoodAIShapes.Pill)
                            .background(FoodAIColors.Primary),
                    )
                }
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                ) {
                    Text(
                        "Старт ${formatWeightValue(summary?.startWeightKg)} кг",
                        style = FoodAITypography.labelSmall,
                        color = FoodAIColors.TextSecondary,
                    )
                    Text(
                        "Цель ${formatWeightValue(summary?.targetWeightKg)} кг",
                        style = FoodAITypography.labelSmall,
                        color = FoodAIColors.TextSecondary,
                    )
                }
            }
        }
        item {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(FoodAIShapes.CardLarge)
                    .background(FoodAIColors.Surface)
                    .padding(FoodAIDimens.Space16),
                verticalArrangement = Arrangement.spacedBy(FoodAIDimens.Space8),
            ) {
                Text("Динамика за ${state.period} дн.", style = FoodAITypography.titleMedium)
                val weightSeries = series.filter { it.weightKg != null }
                when {
                    weightSeries.size >= 2 -> SeriesChart(
                        points = weightSeries,
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(170.dp),
                    )
                    entries.size >= 2 -> WeightChart(
                        entries = entries,
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(170.dp),
                    )
                    else -> Text(
                        "Добавьте минимум две записи веса — появится график.",
                        color = FoodAIColors.TextSecondary,
                        style = FoodAITypography.bodySmall,
                    )
                }
                summary?.trend7dKg?.let {
                    val sign = if (it > 0) "+" else ""
                    Text(
                        "Тренд 7 дней: $sign${formatWeightValue(it)} кг",
                        style = FoodAITypography.labelSmall,
                        color = FoodAIColors.TextSecondary,
                    )
                }
            }
        }
        item {
            val daysWithFood = series.count { it.consumedKcal > 0 }
            val avgKcal = if (daysWithFood > 0) {
                series.filter { it.consumedKcal > 0 }.map { it.consumedKcal }.average().toInt()
            } else {
                0
            }
            val weights = series.mapNotNull { it.weightKg }
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(FoodAIShapes.CardLarge)
                    .background(FoodAIColors.Surface)
                    .padding(FoodAIDimens.Space16),
                verticalArrangement = Arrangement.spacedBy(FoodAIDimens.Space8),
            ) {
                Text("Итоги периода", style = FoodAITypography.titleMedium)
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                ) {
                    ProgressStat("Дней с едой", "$daysWithFood/${series.size}")
                    ProgressStat(
                        "Средние ккал",
                        if (avgKcal > 0) formatKcal(avgKcal) else "—",
                    )
                    ProgressStat(
                        "Вес",
                        if (weights.size >= 2) {
                            "${formatWeightValue(weights.last() - weights.first())} кг"
                        } else {
                            "—"
                        },
                    )
                }
            }
        }
        item {
            val today = summary?.today
            val goalKcal = summary?.calorieTargetKcal ?: today?.targetCaloriesKcal
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(FoodAIShapes.CardLarge)
                    .background(FoodAIColors.Surface)
                    .padding(FoodAIDimens.Space16),
                verticalArrangement = Arrangement.spacedBy(FoodAIDimens.Space8),
            ) {
                Text("Сегодня", style = FoodAITypography.titleMedium)
                if (today != null) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                    ) {
                        ProgressStat("Съедено", "${formatKcal(today.consumedCaloriesKcal)}")
                        ProgressStat("Цель", goalKcal?.let { formatKcal(it) } ?: "—")
                        ProgressStat("Приёмы", "${today.completedMeals}/${today.plannedMeals}")
                    }
                    Text(
                        "Б ${today.proteinG.toInt()} · Ж ${today.fatG.toInt()} · У ${today.carbohydrateG.toInt()} г",
                        style = FoodAITypography.bodySmall,
                        color = FoodAIColors.TextSecondary,
                    )
                } else {
                    Text(
                        "Нет данных по плану на сегодня",
                        color = FoodAIColors.TextSecondary,
                        style = FoodAITypography.bodySmall,
                    )
                }
            }
        }
        item {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(FoodAIShapes.CardLarge)
                    .background(FoodAIColors.Surface)
                    .padding(FoodAIDimens.Space16),
                verticalArrangement = Arrangement.spacedBy(FoodAIDimens.Space12),
            ) {
                Text("Записать вес", style = FoodAITypography.titleMedium)
                OutlinedTextField(
                    value = state.weightInput,
                    onValueChange = onWeightInput,
                    label = { Text("кг") },
                    modifier = Modifier.fillMaxWidth(),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                    singleLine = true,
                    shape = FoodAIShapes.Input,
                )
                if (state.actionError != null) {
                    Text(state.actionError, color = FoodAIColors.Error)
                }
                Button(
                    onClick = onSave,
                    enabled = !state.saving,
                    modifier = Modifier.fillMaxWidth().height(FoodAIDimens.ButtonHeight),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = FoodAIColors.Primary,
                        contentColor = FoodAIColors.TextOnPrimary,
                    ),
                    shape = FoodAIShapes.Button,
                ) {
                    Text(if (state.saving) "Сохраняем…" else "Сохранить")
                }
            }
        }
        item {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(FoodAIShapes.CardLarge)
                    .background(FoodAIColors.Surface)
                    .padding(FoodAIDimens.Space16),
                verticalArrangement = Arrangement.spacedBy(FoodAIDimens.Space8),
            ) {
                Text("История", style = FoodAITypography.titleMedium)
                if (entries.isEmpty()) {
                    Text(
                        "Пока нет записей веса",
                        color = FoodAIColors.TextSecondary,
                        style = FoodAITypography.bodySmall,
                    )
                } else {
                    entries.asReversed().forEach { entry ->
                        WeightRow(entry)
                    }
                }
            }
        }
        item {
            summary?.disclaimer?.takeIf { it.isNotBlank() }?.let {
                Text(it, style = FoodAITypography.bodySmall, color = FoodAIColors.TextSecondary)
            }
            summary?.warnings.orEmpty().forEach { warning ->
                Text(warning, color = FoodAIColors.TextSecondary, style = FoodAITypography.bodySmall)
            }
        }
    }
}

private fun formatWeightValue(value: Double?): String =
    value?.let { String.format(Locale("ru"), "%.1f", it) } ?: "—"

private fun formatWeight(value: Double?): String =
    value?.let { String.format(Locale("ru"), "%.1f", it) } ?: "—"

@Composable
private fun ProgressStat(label: String, value: String) {
    Column {
        Text(value, style = FoodAITypography.titleMedium)
        Text(
            label,
            style = FoodAITypography.labelSmall,
            color = FoodAIColors.TextSecondary,
        )
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
        val values = points.map { it.weightKg!!.toFloat() }
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
        Text(
            "${formatWeight(entry.weightKg)} кг",
            style = FoodAITypography.titleSmall,
        )
        Text(
            entry.measuredAt.take(16).replace('T', ' '),
            style = FoodAITypography.labelSmall,
            color = FoodAIColors.TextSecondary,
        )
        entry.note?.takeIf { it.isNotBlank() }?.let {
            Text(
                it,
                color = FoodAIColors.TextSecondary,
                style = FoodAITypography.bodySmall,
            )
        }
    }
}
