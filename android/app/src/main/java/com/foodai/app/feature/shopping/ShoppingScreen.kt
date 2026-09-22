package com.foodai.app.feature.shopping

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Checkbox
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.foodai.app.core.network.ShoppingListItemDto
import com.foodai.app.core.ui.ErrorPane
import com.foodai.app.core.ui.LoadingPane
import com.foodai.app.core.ui.theme.FoodAiTokens

@Composable
fun ShoppingRoute(
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
) {
    val list = state.list
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(FoodAiTokens.SpaceMd.dp),
        verticalArrangement = Arrangement.spacedBy(FoodAiTokens.SpaceSm.dp),
    ) {
        item {
            Text("Shopping", style = MaterialTheme.typography.headlineMedium)
            if (list != null) {
                Text(
                    "${list.fromDate} — ${list.toDate}",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text("Исключать продукты из кладовой")
                Switch(
                    checked = state.excludePantry,
                    onCheckedChange = onToggleExclude,
                )
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = onRegenerate, enabled = !state.regenerating) {
                    Text(if (state.regenerating) "Обновляем…" else "Пересобрать")
                }
                TextButton(onClick = onRefresh) { Text("Обновить") }
            }
            if (state.actionError != null) {
                Text(state.actionError, color = MaterialTheme.colorScheme.error)
            }
            list?.warnings.orEmpty().forEach { warning ->
                Text(warning, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        val items = list?.items.orEmpty()
        if (items.isEmpty()) {
            item {
                Text(
                    "Список пуст. Если план есть — возможно, всё уже есть в кладовой.",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
        items(items, key = { it.id }) { item ->
            ShoppingRow(item = item, onToggle = { onToggleItem(item) })
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
            .clickable(onClick = onToggle)
            .padding(vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Checkbox(checked = item.isCompleted, onCheckedChange = { onToggle() })
        Column(modifier = Modifier.weight(1f)) {
            Text(
                item.displayName,
                style = MaterialTheme.typography.titleMedium,
                color = if (item.isCompleted) {
                    MaterialTheme.colorScheme.onSurfaceVariant
                } else {
                    MaterialTheme.colorScheme.onSurface
                },
            )
            Text(
                "${formatQty(item.quantityValue)} ${item.unit}" +
                    if (item.sourceRecipeCount > 1) " · ${item.sourceRecipeCount} рецепта" else "",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

private fun formatQty(value: Double): String =
    if (value % 1.0 == 0.0) value.toInt().toString() else "%.1f".format(value)
