package com.foodai.app.feature.diary

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.ArrowBack
import androidx.compose.material.icons.automirrored.outlined.ArrowForward
import androidx.compose.material.icons.outlined.DeleteOutline
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.foodai.app.core.network.NutritionLogDto
import com.foodai.app.core.ui.ErrorPane
import com.foodai.app.core.ui.LoadingPane
import com.foodai.app.core.ui.components.FoodAIPrimaryButton
import com.foodai.app.core.ui.displayRecipeName
import com.foodai.app.core.ui.formatKcal
import com.foodai.app.core.ui.theme.FoodAIColors
import com.foodai.app.core.ui.theme.FoodAIDimens
import com.foodai.app.core.ui.theme.FoodAIShapes
import com.foodai.app.core.ui.theme.FoodAITypography
import com.foodai.app.feature.plan.mealTypeLabel
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.Locale

@Composable
fun DiaryRoute(
    viewModel: DiaryViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var showAdd by remember { mutableStateOf(false) }
    if (showAdd) {
        AddFoodSheet(
            onDismiss = { showAdd = false },
            onSaved = {
                showAdd = false
                viewModel.refresh()
            },
        )
    }
    when {
        state.loading && state.logs.isEmpty() -> LoadingPane("Загружаем дневник…")
        state.error != null && state.logs.isEmpty() -> ErrorPane(
            message = state.error ?: "Ошибка",
            onRetry = viewModel::refresh,
        )
        else -> DiaryScreen(
            state = state,
            onPrevDay = viewModel::prevDay,
            onNextDay = viewModel::nextDay,
            onDelete = viewModel::deleteLog,
            onAdd = { showAdd = true },
        )
    }
}

@Composable
fun DiaryScreen(
    state: DiaryUiState,
    onPrevDay: () -> Unit,
    onNextDay: () -> Unit,
    onDelete: (String) -> Unit,
    onAdd: () -> Unit,
) {
    val locale = Locale("ru")
    val headline = remember(state.date) {
        runCatching {
            LocalDate.parse(state.date)
                .format(DateTimeFormatter.ofPattern("d MMMM", locale))
        }.getOrDefault(state.date)
    }
    val grouped = remember(state.logs) {
        listOf("breakfast", "lunch", "dinner", "snack").map { meal ->
            meal to state.logs.filter { it.mealType == meal }
        }
    }
    val emptyMeals = grouped.filter { it.second.isEmpty() }.map { mealTypeLabel(it.first) }
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(
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
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                IconButton(onClick = onPrevDay) {
                    Icon(
                        Icons.AutoMirrored.Outlined.ArrowBack,
                        contentDescription = "Предыдущий день",
                        tint = FoodAIColors.TextSecondary,
                    )
                }
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text("Дневник", style = FoodAITypography.headlineSmall)
                    Text(
                        headline,
                        style = FoodAITypography.bodyMedium,
                        color = FoodAIColors.TextSecondary,
                    )
                }
                IconButton(onClick = onNextDay) {
                    Icon(
                        Icons.AutoMirrored.Outlined.ArrowForward,
                        contentDescription = "Следующий день",
                        tint = FoodAIColors.TextSecondary,
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
                    "Съедено за день",
                    style = FoodAITypography.labelMedium,
                    color = FoodAIColors.TextSecondary,
                )
                Text(
                    "${formatKcal(state.totalsKcal)} ккал",
                    style = FoodAITypography.headlineLarge,
                )
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                ) {
                    DiaryMacro("Белки", state.proteinG.toInt())
                    DiaryMacro("Жиры", state.fatG.toInt())
                    DiaryMacro("Углеводы", state.carbsG.toInt())
                }
                Text(
                    "Только фактически съеденное — план сюда не входит.",
                    style = FoodAITypography.labelSmall,
                    color = FoodAIColors.TextMuted,
                )
            }
        }
        item {
            Text(
                if (state.date == LocalDate.now().toString()) "Сегодня по приёмам" else "По приёмам",
                style = FoodAITypography.titleLarge,
            )
        }
        for ((meal, rows) in grouped.filter { it.second.isNotEmpty() }) {
            item {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(FoodAIShapes.Card)
                        .background(FoodAIColors.Surface)
                        .padding(FoodAIDimens.Space16),
                    verticalArrangement = Arrangement.spacedBy(FoodAIDimens.Space8),
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(mealTypeLabel(meal), style = FoodAITypography.titleMedium)
                        Text(
                            "${rows.sumOf { it.caloriesKcal }} ккал",
                            style = FoodAITypography.labelMedium,
                            color = FoodAIColors.TextSecondary,
                        )
                    }
                    rows.forEach { log ->
                        DiaryEntryRow(log = log, onDelete = { onDelete(log.id) })
                    }
                }
            }
        }
        if (emptyMeals.isNotEmpty()) {
            item {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(FoodAIShapes.Card)
                        .background(FoodAIColors.Surface)
                        .padding(FoodAIDimens.Space16),
                    verticalArrangement = Arrangement.spacedBy(FoodAIDimens.Space4),
                ) {
                    Text("Пока не записано", style = FoodAITypography.titleMedium)
                    Text(
                        emptyMeals.joinToString(" · "),
                        style = FoodAITypography.bodySmall,
                        color = FoodAIColors.TextSecondary,
                    )
                    Text(
                        "Добавьте еду, чтобы день считался полностью.",
                        style = FoodAITypography.labelSmall,
                        color = FoodAIColors.TextMuted,
                    )
                }
            }
        }
        item {
            FoodAIPrimaryButton(
                label = "Добавить еду",
                onClick = onAdd,
                showArrow = false,
            )
        }
        item { Spacer(Modifier.height(FoodAIDimens.Space16)) }
    }
}

@Composable
private fun DiaryMacro(label: String, grams: Int) {
    Column {
        Text("$grams г", style = FoodAITypography.titleMedium)
        Text(
            label,
            style = FoodAITypography.labelSmall,
            color = FoodAIColors.TextSecondary,
        )
    }
}

@Composable
private fun DiaryEntryRow(log: NutritionLogDto, onDelete: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = FoodAIDimens.Space4),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text(
                displayRecipeName(log.description),
                style = FoodAITypography.titleSmall,
                maxLines = 2,
            )
            Text(
                "${log.caloriesKcal} ккал · Б ${log.proteinG.toInt()} · Ж ${log.fatG.toInt()} · У ${log.carbohydrateG.toInt()}",
                style = FoodAITypography.bodySmall,
                color = FoodAIColors.TextSecondary,
            )
        }
        IconButton(onClick = onDelete) {
            Icon(
                Icons.Outlined.DeleteOutline,
                contentDescription = "Удалить запись",
                tint = FoodAIColors.TextMuted,
            )
        }
    }
}
