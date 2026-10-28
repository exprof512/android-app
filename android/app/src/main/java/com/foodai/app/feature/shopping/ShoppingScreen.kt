package com.foodai.app.feature.shopping

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
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
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CheckboxDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.foodai.app.core.network.ShoppingListItemDto
import com.foodai.app.core.prices.ManualPrice
import com.foodai.app.core.prices.PriceBookStore
import com.foodai.app.core.ui.ErrorPane
import com.foodai.app.core.ui.formatMoney
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
    var inStore by remember { mutableStateOf(false) }
    val allItems = list?.items.orEmpty()
    val context = LocalContext.current
    val priceBook = remember { PriceBookStore(context) }
    var priceVersion by remember { mutableStateOf(0) }
    val stores = remember(priceVersion) { priceBook.stores() }
    val manualPrices = remember(priceVersion) { priceBook.prices() }
    val activeStore = stores.firstOrNull()
    var showPrices by remember { mutableStateOf(false) }
    val manualCount = allItems.count { manualItemCost(it, activeStore, manualPrices) != null }
    val manualTotal = allItems.sumOf { manualItemCost(it, activeStore, manualPrices) ?: 0.0 }
    val estimatedTotal = list?.estimatedTotalAmount ?: 0.0
    val computedTotal = if (manualCount > 0) {
        val remainingShare = (allItems.size - manualCount).toDouble() / allItems.size.coerceAtLeast(1)
        manualTotal + estimatedTotal * remainingShare
    } else {
        estimatedTotal
    }
    val visibleItems = if (inStore) allItems.filter { !it.isCompleted } else allItems
    val bought = allItems.count { it.isCompleted }
    val grouped = visibleItems
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
                "Ингредиенты на неделю. Отмечайте купленное.",
                style = FoodAITypography.bodyMedium,
                color = FoodAIColors.TextSecondary,
            )
            if (list != null) {
                Text(
                    "${list.fromDate} — ${list.toDate}",
                    style = FoodAITypography.bodySmall,
                    color = FoodAIColors.TextSecondary,
                )
                Text(
                    "Итого: ${formatMoney(computedTotal)} ${currencySymbol(list.currency)}",
                    style = FoodAITypography.titleMedium,
                )
                Text(
                    if (manualCount > 0) {
                        "Ваши цены · ${activeStore ?: "без магазина"}"
                    } else {
                        "Оценка · добавьте свои цены, чтобы точнее"
                    },
                    style = FoodAITypography.labelSmall,
                    color = FoodAIColors.TextSecondary,
                )
                TextButton(onClick = { showPrices = true }) {
                    Text("Мои цены", color = FoodAIColors.Primary)
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
                Column(Modifier.weight(1f)) {
                    Text("Режим магазина", style = FoodAITypography.titleSmall)
                    Text(
                        if (inStore) {
                            "Осталось купить: ${allItems.size - bought} из ${allItems.size}"
                        } else {
                            "Скрыть купленное и идти по списку"
                        },
                        style = FoodAITypography.bodySmall,
                        color = FoodAIColors.TextSecondary,
                    )
                }
                Switch(
                    checked = inStore,
                    onCheckedChange = { inStore = it },
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

    if (showPrices) {
        PriceBookDialog(
            stores = stores.ifEmpty {
                listOf("Пятёрочка", "Магнит", "Лента", "Перекрёсток", "ВкусВилл", "Рынок")
            },
            prices = manualPrices,
            defaultStore = activeStore,
            onSave = { store, product, price ->
                priceBook.upsert(store, product, price)
                priceVersion++
            },
            onDelete = { store, product ->
                priceBook.remove(store, product)
                priceVersion++
            },
            onDismiss = { showPrices = false },
        )
    }
}

@Composable
private fun PriceBookDialog(
    stores: List<String>,
    prices: List<ManualPrice>,
    defaultStore: String?,
    onSave: (String, String, Double) -> Unit,
    onDelete: (String, String) -> Unit,
    onDismiss: () -> Unit,
) {
    var store by remember { mutableStateOf(defaultStore ?: stores.first()) }
    var product by remember { mutableStateOf("") }
    var price by remember { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Мои цены") },
        text = {
            Column(
                modifier = Modifier.verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Text(
                    "Цена за 100 г/мл или за штуку — список покупок посчитается по вашим данным.",
                    style = FoodAITypography.bodySmall,
                    color = FoodAIColors.TextSecondary,
                )
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    stores.take(3).forEach { name ->
                        FilterChip(
                            selected = store == name,
                            onClick = { store = name },
                            label = { Text(name) },
                            colors = FilterChipDefaults.filterChipColors(
                                selectedContainerColor = FoodAIColors.PrimaryLight,
                            ),
                        )
                    }
                }
                OutlinedTextField(
                    value = product,
                    onValueChange = { product = it },
                    label = { Text("Продукт") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = price,
                    onValueChange = { price = it },
                    label = { Text("Цена, ₽") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                    modifier = Modifier.fillMaxWidth(),
                )
                TextButton(
                    onClick = {
                        val value = price.replace(',', '.').toDoubleOrNull()
                        if (value != null && value > 0 && product.isNotBlank()) {
                            onSave(store, product, value)
                            product = ""
                            price = ""
                        }
                    },
                ) {
                    Text("Сохранить", color = FoodAIColors.Primary)
                }
                val forStore = prices.filter { it.store == store }
                if (forStore.isNotEmpty()) {
                    Text("Сохранённые", style = FoodAITypography.titleSmall)
                    forStore.forEach { row ->
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Text(
                                "${row.product} — ${formatMoney(row.price)} ₽",
                                style = FoodAITypography.bodySmall,
                            )
                            TextButton(onClick = { onDelete(row.store, row.product) }) {
                                Text("Удалить", color = FoodAIColors.TextSecondary)
                            }
                        }
                    }
                }
            }
        },
        confirmButton = {
            TextButton(onClick = onDismiss) { Text("Готово") }
        },
    )
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
                "${formatQty(item.quantityValue)} ${unitLabel(item.unit)}" +
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

private fun manualItemCost(
    item: ShoppingListItemDto,
    store: String?,
    prices: List<ManualPrice>,
): Double? {
    if (store == null) return null
    val normalized = item.displayName.trim().lowercase()
    val price = prices.firstOrNull {
        it.store == store && it.product == normalized
    }?.price ?: return null
    return when (item.unit.lowercase()) {
        "g", "ml" -> price * item.quantityValue / 100.0
        "kg", "l" -> price * item.quantityValue * 10.0
        "pcs", "pc", "piece", "pieces" -> price * item.quantityValue
        else -> null
    }
}

private fun formatQty(value: Double): String =
    if (value % 1.0 == 0.0) value.toInt().toString() else "%.1f".format(value)

private fun unitLabel(unit: String): String = when (unit.lowercase()) {
    "g", "gr", "gram" -> "г"
    "kg" -> "кг"
    "ml" -> "мл"
    "l" -> "л"
    "pcs", "pc", "piece", "pieces" -> "шт"
    "tbsp" -> "ст. л."
    "tsp" -> "ч. л."
    else -> unit
}

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
