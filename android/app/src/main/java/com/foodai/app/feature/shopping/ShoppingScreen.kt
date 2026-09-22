package com.foodai.app.feature.shopping

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CheckboxDefaults
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.foodai.app.core.network.ShoppingListItemDto
import com.foodai.app.core.ui.ErrorPane
import com.foodai.app.core.ui.LoadingPane
import com.foodai.app.core.ui.components.FoodAIEmptyState
import com.foodai.app.core.ui.theme.FoodAIColors
import com.foodai.app.core.ui.theme.FoodAIDimens
import com.foodai.app.core.ui.theme.FoodAIShapes
import com.foodai.app.core.ui.theme.FoodAITypography

@Composable
fun ShoppingRoute(
    onBack: (() -> Unit)? = null,
    viewModel: ShoppingViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    when {
        state.loading -> LoadingPane("Собираем список покупок…")
        state.error != null && state.list == null -> ErrorPane(
            message = state.error ?: "Ошибка",
            onRetry = viewModel::refresh,
        )
        else -> ShoppingScreen(
            state = state,
            onRefresh = viewModel::refresh,
            onRegenerate = viewModel::regenerate,
            onToggleExclude = viewModel::setExcludePantry,
            onToggleItem = viewModel::toggleItem,
            onBack = onBack,
        )
    }
}

@Composable
fun ShoppingScreen(
    state: ShoppingUiState,
    onRefresh: () -> Unit,
    onRegenerate: () -> Unit,
    onToggleExclude: (Boolean) -> Unit,
    onToggleItem: (ShoppingListItemDto) -> Unit,
    onBack: (() -> Unit)? = null,
) {
    val list = state.list
    val grouped = list?.items.orEmpty().groupBy { categoryFor(it.displayName) }
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(FoodAIColors.Background)
            .padding(horizontal = FoodAIDimens.ScreenPadding),
        verticalArrangement = Arrangement.spacedBy(FoodAIDimens.Space8),
        contentPadding = PaddingValues(
            top = FoodAIDimens.Space16,
            bottom = FoodAIDimens.Space32,
        ),
    ) {
        item {
            if (onBack != null) {
                TextButton(onClick = onBack) {
                    Text("← Назад", color = FoodAIColors.Primary)
                }
            }
            Text("Список покупок", style = FoodAITypography.headlineMedium)
            Text(
                "Все ингредиенты для твоего плана. Отмечай купленное — и ничего не забудешь!",
                style = FoodAITypography.bodyMedium,
                color = FoodAIColors.TextSecondary,
            )
            if (list != null) {
                Text(
                    "${list.fromDate} — ${list.toDate}",
                    style = FoodAITypography.bodySmall,
                )
            }
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text("Исключать продукты из кладовой", style = FoodAITypography.bodyMedium)
                Switch(
                    checked = state.excludePantry,
                    onCheckedChange = onToggleExclude,
                    colors = SwitchDefaults.colors(checkedTrackColor = FoodAIColors.Primary),
                )
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                TextButton(onClick = onRegenerate, enabled = !state.regenerating) {
                    Text(
                        if (state.regenerating) "Обновляем…" else "Пересобрать",
                        color = FoodAIColors.Primary,
                    )
                }
                TextButton(onClick = onRefresh) {
                    Text("Обновить", color = FoodAIColors.TextSecondary)
                }
            }
            if (state.actionError != null) {
                Text(state.actionError, color = FoodAIColors.Error)
            }
            list?.warnings.orEmpty().forEach { warning ->
                Text(warning, style = FoodAITypography.bodySmall)
            }
        }
        if (grouped.isEmpty()) {
            item {
                FoodAIEmptyState(
                    title = "Список пуст",
                    subtitle = "Если план есть — возможно, всё уже есть в кладовой.",
                )
            }
        }
        grouped.forEach { (category, catItems) ->
            item {
                Text(
                    category,
                    style = FoodAITypography.titleMedium,
                    modifier = Modifier.padding(top = FoodAIDimens.Space12),
                )
            }
            items(catItems, key = { it.id }) { item ->
                ShoppingRow(item = item, onToggle = { onToggleItem(item) })
            }
        }
    }
}

@Composable
private fun ShoppingRow(
    item: ShoppingListItemDto,
    onToggle: () -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(FoodAIShapes.Card)
            .background(if (item.isCompleted) FoodAIColors.PrimarySoft else FoodAIColors.Surface)
            .clickable(onClick = onToggle)
            .padding(horizontal = FoodAIDimens.Space12, vertical = FoodAIDimens.Space8),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Checkbox(
            checked = item.isCompleted,
            onCheckedChange = { onToggle() },
            colors = CheckboxDefaults.colors(checkedColor = FoodAIColors.Primary),
        )
        Column(modifier = Modifier.weight(1f)) {
            Text(
                item.displayName,
                style = FoodAITypography.titleMedium,
                color = if (item.isCompleted) FoodAIColors.TextSecondary else FoodAIColors.TextPrimary,
            )
            Text(
                "${formatQty(item.quantityValue)} ${item.unit}" +
                    if (item.sourceRecipeCount > 1) " · ${item.sourceRecipeCount} рецепта" else "",
                style = FoodAITypography.bodySmall,
            )
        }
    }
}

private fun formatQty(value: Double): String =
    if (value % 1.0 == 0.0) value.toInt().toString() else "%.1f".format(value)

private fun categoryFor(name: String): String {
    val n = name.lowercase()
    return when {
        listOf("помидор", "огурец", "перец", "лук", "чеснок", "морков", "яблок", "банан", "ягод", "салат", "броккол", "капуст", "авокад", "фрукт", "овощ").any { n.contains(it) } ->
            "Овощи и фрукты"
        listOf("куриц", "говяд", "свинин", "индейк", "рыб", "лосос", "мяс", "яйц").any { n.contains(it) } ->
            "Мясо и рыба"
        listOf("рис", "гречк", "макарон", "овсян", "киноа", "круп", "мук", "хлеб").any { n.contains(it) } ->
            "Крупы"
        listOf("молок", "сыр", "йогурт", "творог", "сливк", "кефир").any { n.contains(it) } ->
            "Молочные продукты"
        else -> "Прочее"
    }
}
