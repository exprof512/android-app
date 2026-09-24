package com.foodai.app.feature.diary

import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.ArrowBack
import androidx.compose.material.icons.automirrored.outlined.ArrowForward
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
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.foodai.app.core.network.NutritionLogDto
import com.foodai.app.core.ui.ErrorPane
import com.foodai.app.core.ui.LoadingPane
import com.foodai.app.core.ui.displayRecipeName
import com.foodai.app.core.ui.theme.FoodAIColors
import com.foodai.app.core.ui.theme.FoodAIDimens
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
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = FoodAIDimens.ScreenPadding),
        contentPadding = PaddingValues(vertical = FoodAIDimens.Space16),
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
                    )
                }
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text("Дневник", style = FoodAITypography.titleLarge)
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
                    )
                }
            }
        }
        item {
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(
                    "%,d ккал".format(state.totalsKcal),
                    style = FoodAITypography.headlineMedium,
                )
                Text(
                    "Б ${state.proteinG.toInt()} · Ж ${state.fatG.toInt()} · У ${state.carbsG.toInt()} г",
                    style = FoodAITypography.bodyMedium,
                    color = FoodAIColors.TextSecondary,
                )
                Text(
                    "Фактически съеденное — без запланированных приёмов.",
                    style = FoodAITypography.labelSmall,
                    color = FoodAIColors.TextMuted,
                )
            }
        }
        item {
            val eatenTitle = if (state.date == LocalDate.now().toString()) "Сегодня съедено" else "Съедено"
            Text(eatenTitle, style = FoodAITypography.titleMedium)
        }
        for ((meal, rows) in grouped) {
            item {
                Text(mealTypeLabel(meal), style = FoodAITypography.titleSmall, color = FoodAIColors.TextSecondary)
            }
            if (rows.isEmpty()) {
                item {
                    Text("Нет записей", style = FoodAITypography.bodySmall, color = FoodAIColors.TextMuted)
                }
            } else {
                items(rows, key = { it.id }) { log ->
                    DiaryEntryRow(log = log, onDelete = { onDelete(log.id) })
                }
            }
        }
        item {
            com.foodai.app.core.ui.components.FoodAIPrimaryButton(
                label = "Добавить еду",
                onClick = onAdd,
                showArrow = false,
            )
        }
        item { Spacer(Modifier.height(FoodAIDimens.Space32)) }
    }
}

@Composable
private fun DiaryEntryRow(log: NutritionLogDto, onDelete: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = FoodAIDimens.Space8),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text(
                displayRecipeName(log.description),
                style = FoodAITypography.titleMedium,
                maxLines = 2,
            )
            Text(
                "${log.caloriesKcal} ккал · Б ${log.proteinG.toInt()} · Ж ${log.fatG.toInt()} · У ${log.carbohydrateG.toInt()}",
                style = FoodAITypography.bodySmall,
                color = FoodAIColors.TextSecondary,
            )
        }
        Text(
            "Удалить",
            color = FoodAIColors.Error,
            style = FoodAITypography.labelMedium,
            modifier = Modifier.clickable(onClick = onDelete),
        )
    }
}
