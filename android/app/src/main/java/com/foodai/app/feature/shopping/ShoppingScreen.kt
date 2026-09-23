package com.foodai.app.feature.shopping

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CheckboxDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
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
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.foodai.app.core.network.ShoppingListItemDto
import com.foodai.app.core.ui.ErrorPane
import com.foodai.app.core.ui.LoadingPane
import com.foodai.app.core.ui.foodEmojiFor
import com.foodai.app.core.ui.components.FoodAIEmptyState
import com.foodai.app.core.ui.components.FoodAITipBanner
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
            onClearCompleted = viewModel::clearCompleted,
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
    onClearCompleted: () -> Unit,
    onToggleExclude: (Boolean) -> Unit,
    onToggleItem: (ShoppingListItemDto) -> Unit,
    onBack: (() -> Unit)? = null,
) {
    val list = state.list
    val grouped = list?.items.orEmpty()
        .groupBy { categoryLabel(it.category, it.displayName) }
        .toSortedMap()
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
            Spacer(Modifier.size(FoodAIDimens.Space8))
            FoodAITipBanner(
                tipId = "shopping_check",
                text = "Отмечай купленное галочкой. Включи «Уже есть дома», чтобы скрыть продукты из кладовой.",
            )
            if (list != null) {
                Text(
                    "${list.fromDate} — ${list.toDate}",
                    style = FoodAITypography.bodySmall,
                )
                list.estimatedTotalAmount?.let { total ->
                    Text(
                        "Ориентировочно: ${"%.0f".format(total)} ${currencySymbol(list.currency)}",
                        style = FoodAITypography.titleMedium,
                    )
                }
            }
            if (list?.stale == true) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(FoodAIShapes.Card)
                        .background(FoodAIColors.Warning.copy(alpha = 0.15f))
                        .padding(FoodAIDimens.Space12),
                ) {
                    Text(
                        "Список покупок изменился",
                        style = FoodAITypography.titleSmall,
                        color = FoodAIColors.Warning,
                    )
                    Text(
                        "План обновился — пересоберите список, чтобы синхронизировать ингредиенты.",
                        style = FoodAITypography.bodySmall,
                    )
                    TextButton(onClick = onRegenerate, enabled = !state.regenerating) {
                        Text(
                            if (state.regenerating) "Собираем…" else "Пересобрать",
                            color = FoodAIColors.Primary,
                        )
                    }
                }
            }
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Column(Modifier.weight(1f)) {
                    Text("Уже есть дома", style = FoodAITypography.titleSmall)
                    Text(
                        "Скрыть из списка продукты, которые ты отметил в кладовой",
                        style = FoodAITypography.bodySmall,
                        color = FoodAIColors.TextSecondary,
                    )
                }
                Switch(
                    checked = state.excludePantry,
                    onCheckedChange = onToggleExclude,
                    colors = SwitchDefaults.colors(checkedTrackColor = FoodAIColors.Primary),
                )
            }
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                TextButton(onClick = onRegenerate, enabled = !state.regenerating) {
                    Text(
                        if (state.regenerating) "Собираем…" else "Пересобрать список",
                        color = FoodAIColors.Primary,
                    )
                }
                TextButton(
                    onClick = onClearCompleted,
                    enabled = list?.items?.any { it.isCompleted } == true,
                ) {
                    Text("Очистить купленное", color = FoodAIColors.TextSecondary)
                }
                IconButton(onClick = onRefresh) {
                    Icon(
                        imageVector = Icons.Outlined.Refresh,
                        contentDescription = "Обновить список покупок с сервера",
                        tint = FoodAIColors.Primary,
                    )
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
        Box(
            modifier = Modifier
                .size(44.dp)
                .clip(FoodAIShapes.Tile)
                .background(FoodAIColors.PrimarySoft),
            contentAlignment = Alignment.Center,
        ) {
            Text(foodEmojiFor(item.displayName), fontSize = 22.sp)
        }
        Spacer(Modifier.size(FoodAIDimens.Space12))
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
        Checkbox(
            checked = item.isCompleted,
            onCheckedChange = { onToggle() },
            colors = CheckboxDefaults.colors(checkedColor = FoodAIColors.Primary),
        )
    }
}

private fun formatQty(value: Double): String =
    if (value % 1.0 == 0.0) value.toInt().toString() else "%.1f".format(value)

private fun currencySymbol(code: String): String = when (code.uppercase()) {
    "RUB", "RUR" -> "₽"
    "USD" -> "$"
    "EUR" -> "€"
    else -> code
}

private fun categoryLabel(apiCategory: String?, displayName: String): String {
    return when (apiCategory?.lowercase()) {
        "vegetables" -> "Овощи и фрукты"
        "meat" -> "Мясо и рыба"
        "dairy" -> "Молочные продукты"
        "grains" -> "Крупы"
        "other" -> heuristicCategory(displayName)
        null, "" -> heuristicCategory(displayName)
        else -> heuristicCategory(displayName)
    }
}

private fun heuristicCategory(name: String): String {
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
