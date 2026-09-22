package com.foodai.app.feature.plan

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
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.foodai.app.core.network.MealPlanItemDto
import com.foodai.app.core.ui.ErrorPane
import com.foodai.app.core.ui.LoadingPane
import com.foodai.app.core.ui.RecipeImagePane
import com.foodai.app.core.ui.theme.FoodAiTokens
import kotlin.math.min

@Composable
fun TodayRoute(
    onOpenRecipe: (recipeId: String, itemId: String) -> Unit,
    viewModel: TodayViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
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
    val eaten = todayItems.filter { it.isCompleted }.sumOf { it.recipe.caloriesKcal }
    val target = plan?.dailyTargets?.caloriesKcal ?: goal?.calorieTargetKcal ?: 0
    val progress = if (target > 0) min(1f, eaten.toFloat() / target.toFloat()) else 0f

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(FoodAiTokens.SpaceMd.dp),
        verticalArrangement = Arrangement.spacedBy(FoodAiTokens.SpaceMd.dp),
    ) {
        item {
            Text(
                "Привет! 👋",
                style = MaterialTheme.typography.headlineMedium,
            )
            Text(
                "Твой план на сегодня",
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        item {
            Card(
                colors = CardDefaults.cardColors(containerColor = ColorWhite),
                shape = RoundedCornerShape(FoodAiTokens.RadiusMd.dp),
                elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
            ) {
                Column(Modifier.padding(FoodAiTokens.SpaceMd.dp)) {
                    Text(
                        if (target > 0) "$eaten из $target ккал" else "Цель калорий не задана",
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.SemiBold,
                    )
                    Spacer(Modifier.height(8.dp))
                    LinearProgressIndicator(
                        progress = { progress },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(10.dp)
                            .clip(RoundedCornerShape(FoodAiTokens.RadiusPill.dp)),
                        color = FoodAiTokens.Forest,
                        trackColor = FoodAiTokens.Fog,
                    )
                    if (goal != null) {
                        Spacer(Modifier.height(12.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            MacroChip("Б", "${goal.macroTargetsG.protein} г")
                            MacroChip("Ж", "${goal.macroTargetsG.fat} г")
                            MacroChip("У", "${goal.macroTargetsG.carbohydrate} г")
                        }
                    }
                }
            }
        }
        if (state.actionError != null) {
            item {
                Text(state.actionError, color = MaterialTheme.colorScheme.error)
            }
        }
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text("Приёмы пищи", style = MaterialTheme.typography.titleMedium)
                TextButton(onClick = onRefresh) { Text("Обновить") }
            }
        }
        if (todayItems.isEmpty()) {
            item {
                Text(
                    "На сегодня нет приёмов пищи. Создайте план на неделю.",
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

private val ColorWhite = androidx.compose.ui.graphics.Color.White

@Composable
private fun MacroChip(label: String, value: String) {
    Surface(
        color = FoodAiTokens.Fog,
        shape = RoundedCornerShape(FoodAiTokens.RadiusSm.dp),
    ) {
        Column(Modifier.padding(horizontal = 12.dp, vertical = 8.dp)) {
            Text(label, style = MaterialTheme.typography.labelLarge, color = FoodAiTokens.Forest)
            Text(value, style = MaterialTheme.typography.bodyMedium)
        }
    }
}

@Composable
fun WeekRoute(
    onOpenRecipe: (recipeId: String, itemId: String) -> Unit,
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
            Text("План на неделю", style = MaterialTheme.typography.headlineMedium)
            TextButton(onClick = onRefresh) { Text("Обновить") }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                dates.forEach { date ->
                    val selected = date == state.selectedDate
                    Surface(
                        onClick = { onSelectDate(date) },
                        color = if (selected) FoodAiTokens.Forest else FoodAiTokens.Fog,
                        shape = RoundedCornerShape(FoodAiTokens.RadiusPill.dp),
                    ) {
                        Text(
                            date.takeLast(5),
                            modifier = Modifier.padding(horizontal = 14.dp, vertical = 8.dp),
                            color = if (selected) ColorWhite else FoodAiTokens.Ink,
                            style = MaterialTheme.typography.labelLarge,
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
        colors = CardDefaults.cardColors(containerColor = ColorWhite),
        shape = RoundedCornerShape(FoodAiTokens.RadiusMd.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
    ) {
        Column(Modifier.padding(FoodAiTokens.SpaceMd.dp)) {
            RecipeImagePane(
                image = item.recipe.image,
                contentDescription = item.recipe.name,
            )
            Spacer(Modifier.height(8.dp))
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                if (item.isCompleted) {
                    Box(
                        modifier = Modifier
                            .size(22.dp)
                            .clip(CircleShape)
                            .background(FoodAiTokens.Forest),
                        contentAlignment = Alignment.Center,
                    ) {
                        Text("✓", color = ColorWhite, style = MaterialTheme.typography.labelLarge)
                    }
                }
                Text(
                    mealTypeLabel(item.mealType),
                    style = MaterialTheme.typography.labelLarge,
                    color = MaterialTheme.colorScheme.primary,
                )
            }
            Text(item.recipe.name, style = MaterialTheme.typography.titleMedium)
            Text(
                "${item.recipe.caloriesKcal} ккал · ${item.recipe.cookTimeMinutes} мин" +
                    if (item.isCompleted) " · готово" else "",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                if (onComplete != null) {
                    OutlinedButton(
                        onClick = onComplete,
                        shape = RoundedCornerShape(FoodAiTokens.RadiusPill.dp),
                    ) {
                        Text(if (item.isCompleted) "Снять отметку" else "Съедено")
                    }
                }
                if (onReplace != null) {
                    Button(
                        onClick = onReplace,
                        shape = RoundedCornerShape(FoodAiTokens.RadiusPill.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = FoodAiTokens.Forest),
                    ) {
                        Text("Заменить")
                    }
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
