package com.foodai.app.feature.progress

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.foodai.app.core.network.WeightEntryDto
import com.foodai.app.core.ui.ErrorPane
import com.foodai.app.core.ui.LoadingPane
import com.foodai.app.core.ui.theme.FoodAiTokens

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
        )
    }
}

@Composable
fun ProgressScreen(
    state: ProgressUiState,
    onWeightInput: (String) -> Unit,
    onSave: () -> Unit,
    onRefresh: () -> Unit,
) {
    val summary = state.summary
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(FoodAiTokens.SpaceMd.dp),
        verticalArrangement = Arrangement.spacedBy(FoodAiTokens.SpaceMd.dp),
    ) {
        item {
            Text("Progress", style = MaterialTheme.typography.headlineMedium)
            TextButton(onClick = onRefresh) { Text("Обновить") }
        }
        item {
            Text(
                "Текущий вес: ${summary?.currentWeightKg?.let { "$it кг" } ?: "—"}",
                style = MaterialTheme.typography.titleMedium,
            )
            if (summary?.startWeightKg != null || summary?.targetWeightKg != null) {
                Text(
                    "Старт ${summary.startWeightKg ?: "—"} → цель ${summary.targetWeightKg ?: "—"} кг",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            summary?.progressPercent?.let {
                Text("Прогресс к цели: ${"%.0f".format(it)}%")
            }
            summary?.trend7dKg?.let {
                val sign = if (it > 0) "+" else ""
                Text("Тренд 7 дней: $sign$it кг")
            }
            summary?.weightDeltaKg?.let {
                val sign = if (it > 0) "+" else ""
                Text("Изменение с старта: $sign$it кг")
            }
        }
        item {
            val today = summary?.today
            Text("Сегодня", style = MaterialTheme.typography.titleLarge)
            if (today != null) {
                Text(
                    "Съедено ${today.consumedCaloriesKcal} / план ${today.plannedCaloriesKcal} ккал" +
                        (today.targetCaloriesKcal?.let { " (цель $it)" } ?: ""),
                )
                Text(
                    "Б ${today.proteinG} / Ж ${today.fatG} / У ${today.carbohydrateG} · " +
                        "${today.completedMeals}/${today.plannedMeals} приёмов",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            } else {
                Text("Нет данных по плану на сегодня", color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        item {
            Text("Записать вес", style = MaterialTheme.typography.titleLarge)
            OutlinedTextField(
                value = state.weightInput,
                onValueChange = onWeightInput,
                label = { Text("кг") },
                modifier = Modifier.fillMaxWidth(),
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                singleLine = true,
            )
            if (state.actionError != null) {
                Text(state.actionError, color = MaterialTheme.colorScheme.error)
            }
            Button(onClick = onSave, enabled = !state.saving) {
                Text(if (state.saving) "Сохраняем…" else "Сохранить")
            }
        }
        item {
            summary?.disclaimer?.takeIf { it.isNotBlank() }?.let {
                Text(it, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            summary?.warnings.orEmpty().forEach { warning ->
                Text(warning, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        item {
            Text("История", style = MaterialTheme.typography.titleLarge)
        }
        val entries = summary?.recentEntries.orEmpty()
        if (entries.isEmpty()) {
            item {
                Text("Пока нет записей веса", color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        items(entries, key = { it.id }) { entry ->
            WeightRow(entry)
        }
    }
}

@Composable
private fun WeightRow(entry: WeightEntryDto) {
    Column(modifier = Modifier.fillMaxWidth()) {
        Text("${entry.weightKg} кг", style = MaterialTheme.typography.titleMedium)
        Text(
            entry.measuredAt.take(16).replace('T', ' '),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        entry.note?.takeIf { it.isNotBlank() }?.let {
            Text(it, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}
