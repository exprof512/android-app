package com.foodai.app.feature.plan

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.foodai.app.core.network.MealPlanItemDto
import com.foodai.app.core.ui.ErrorPane
import com.foodai.app.core.ui.LoadingPane
import com.foodai.app.core.ui.RecipeImagePane
import com.foodai.app.core.ui.theme.FoodAiTokens

@Composable
fun TodayRoute(
    onOpenRecipe: (recipeId: String, itemId: String) -> Unit,
    viewModel: TodayViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    when {
        state.loading -> LoadingPane("Загружаем сегодня…")
        state.error != null && state.plan == null -> ErrorPane(
            message = state.error ?: "Ошибка",
            onRetry = viewModel::refresh,
        )
        else -> TodayScreen(
            state = state,
            onRefresh = viewModel::refresh,
            onComplete = viewModel::complete,
            onReplace = viewModel::replace,
            onOpenRecipe = onOpenRecipe,
        )
    }
}

@Composable
fun TodayScreen(
    state: TodayUiState,
    onRefresh: () -> Unit,
    onComplete: (MealPlanItemDto) -> Unit,
    onReplace: (MealPlanItemDto) -> Unit,
    onOpenRecipe: (recipeId: String, itemId: String) -> Unit,
) {
    val plan = state.plan
    val goal = state.profile?.goal
    val todayItems = plan?.items.orEmpty()
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(FoodAiTokens.SpaceMd.dp),
        verticalArrangement = Arrangement.spacedBy(FoodAiTokens.SpaceMd.dp),
    ) {
        item {
            Text("TODAY", style = MaterialTheme.typography.headlineMedium)
            if (goal != null) {
                Text(
                    "Цель: ${goal.calorieTargetKcal} ккал · " +
                        "Б ${goal.macroTargetsG.protein} / Ж ${goal.macroTargetsG.fat} / " +
                        "У ${goal.macroTargetsG.carbohydrate}",
                    style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            plan?.dailyTargets?.let { t ->
                Text(
                    "План дня: ${t.caloriesKcal} ккал",
                    style = MaterialTheme.typography.titleMedium,
                )
            }
            if (state.actionError != null) {
                Text(state.actionError, color = MaterialTheme.colorScheme.error)
            }
            TextButton(onClick = onRefresh) { Text("Обновить") }
        }
        if (todayItems.isEmpty()) {
            item {
                Text(
                    "На сегодня нет приёмов пищи. Сгенерируйте план в онбординге или позже.",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
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
        item { Spacer(Modifier.height(24.dp)) }
    }
}

@Composable
fun WeekRoute(
    onOpenRecipe: (recipeId: String, itemId: String) -> Unit,
    viewModel: WeekViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    when {
        state.loading -> LoadingPane("Загружаем неделю…")
        state.error != null && state.plan == null -> ErrorPane(
            message = state.error ?: "Ошибка",
            onRetry = viewModel::refresh,
        )
        else -> WeekScreen(
            state = state,
            onSelectDate = viewModel::selectDate,
            onRefresh = viewModel::refresh,
            onOpenRecipe = onOpenRecipe,
        )
    }
}

@Composable
fun WeekScreen(
    state: WeekUiState,
    onSelectDate: (String) -> Unit,
    onRefresh: () -> Unit,
    onOpenRecipe: (recipeId: String, itemId: String) -> Unit,
) {
    val plan = state.plan
    val dates = plan?.items.orEmpty().map { it.date }.distinct().sorted()
    val dayItems = plan?.items.orEmpty().filter { it.date == state.selectedDate }
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(FoodAiTokens.SpaceMd.dp),
        verticalArrangement = Arrangement.spacedBy(FoodAiTokens.SpaceMd.dp),
    ) {
        item {
            Text("Plan", style = MaterialTheme.typography.headlineMedium)
            TextButton(onClick = onRefresh) { Text("Обновить") }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                dates.forEach { date ->
                    val selected = date == state.selectedDate
                    OutlinedButton(onClick = { onSelectDate(date) }) {
                        Text(
                            date.takeLast(5),
                            color = if (selected) {
                                MaterialTheme.colorScheme.primary
                            } else {
                                MaterialTheme.colorScheme.onSurface
                            },
                        )
                    }
                }
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
    }
}

@Composable
fun MealItemCard(
    item: MealPlanItemDto,
    onOpen: () -> Unit,
    onComplete: (() -> Unit)?,
    onReplace: (() -> Unit)?,
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onOpen),
    ) {
        Column(Modifier.padding(FoodAiTokens.SpaceMd.dp)) {
            RecipeImagePane(
                image = item.recipe.image,
                contentDescription = item.recipe.name,
            )
            Spacer(Modifier.height(8.dp))
            Text(
                mealTypeLabel(item.mealType),
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.primary,
            )
            Text(item.recipe.name, style = MaterialTheme.typography.titleMedium)
            Text(
                "${item.recipe.caloriesKcal} ккал · ${item.recipe.cookTimeMinutes} мин" +
                    if (item.isCompleted) " · готово" else "",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                if (onComplete != null) {
                    OutlinedButton(onClick = onComplete) {
                        Text(if (item.isCompleted) "Снять отметку" else "Съедено")
                    }
                }
                if (onReplace != null) {
                    Button(onClick = onReplace) { Text("Заменить") }
                }
            }
        }
    }
}

fun mealTypeLabel(raw: String): String = when (raw) {
    "breakfast" -> "Завтрак"
    "lunch" -> "Обед"
    "dinner" -> "Ужин"
    "snack" -> "Перекус"
    else -> raw
}
