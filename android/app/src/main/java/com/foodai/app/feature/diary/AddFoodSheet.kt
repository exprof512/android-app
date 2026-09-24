package com.foodai.app.feature.diary

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.foodai.app.core.ui.components.FoodAIOutlinedButton
import com.foodai.app.core.ui.components.FoodAIPrimaryButton
import com.foodai.app.core.ui.theme.FoodAIColors
import com.foodai.app.core.ui.theme.FoodAIDimens
import com.foodai.app.core.ui.theme.FoodAITypography

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
fun AddFoodSheet(
    onDismiss: () -> Unit,
    onSaved: () -> Unit,
    viewModel: AddFoodViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    var description by remember { mutableStateOf("") }
    var calories by remember { mutableStateOf("") }
    var protein by remember { mutableStateOf("") }
    var fat by remember { mutableStateOf("") }
    var carbs by remember { mutableStateOf("") }

    val gallery = rememberLauncherForActivityResult(
        ActivityResultContracts.GetContent(),
    ) { uri ->
        if (uri != null) viewModel.analyzePhoto(uri)
    }

    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = sheetState) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .padding(FoodAIDimens.ScreenPadding)
                .padding(bottom = FoodAIDimens.Space32),
            verticalArrangement = Arrangement.spacedBy(FoodAIDimens.Space12),
        ) {
            Text("Добавить еду", style = FoodAITypography.titleLarge)
            Text(
                "Сфотографируйте блюдо или найдите продукт — FoodAI оценит ккал и БЖУ.",
                style = FoodAITypography.bodySmall,
                color = FoodAIColors.TextSecondary,
            )

            FoodAIPrimaryButton(
                label = "Сфотографировать",
                onClick = {
                    viewModel.setTab("photo")
                    gallery.launch("image/*")
                },
                showArrow = false,
            )
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(FoodAIDimens.Space8),
            ) {
                FoodAIOutlinedButton(
                    label = "Найти продукт",
                    onClick = { viewModel.setTab("search") },
                    modifier = Modifier.weight(1f),
                )
                FoodAIOutlinedButton(
                    label = "Недавние",
                    onClick = { viewModel.setTab("recent") },
                    modifier = Modifier.weight(1f),
                )
            }
            FoodAIOutlinedButton(
                label = "Быстрые калории",
                onClick = { viewModel.setTab("quick") },
            )

            Text("Приём пищи", style = FoodAITypography.labelMedium, color = FoodAIColors.TextSecondary)
            FlowRow(
                horizontalArrangement = Arrangement.spacedBy(FoodAIDimens.Space8),
                verticalArrangement = Arrangement.spacedBy(FoodAIDimens.Space8),
            ) {
                listOf(
                    "breakfast" to "Завтрак",
                    "lunch" to "Обед",
                    "dinner" to "Ужин",
                    "snack" to "Перекус",
                ).forEach { (key, label) ->
                    FilterChip(
                        selected = state.mealType == key,
                        onClick = { viewModel.setMealType(key) },
                        label = {
                            Text(label, modifier = Modifier.padding(horizontal = 4.dp))
                        },
                        modifier = Modifier.heightIn(min = FoodAIDimens.TouchTarget),
                    )
                }
            }

            val errorText = state.error
            if (errorText != null) {
                Text(errorText, style = FoodAITypography.bodyMedium, color = FoodAIColors.Error)
            }

            when (state.tab) {
                "quick" -> {
                    Text("Что вы съели?", style = FoodAITypography.titleMedium)
                    OutlinedTextField(
                        value = description,
                        onValueChange = { description = it },
                        label = { Text("Название блюда") },
                        modifier = Modifier.fillMaxWidth(),
                    )
                    OutlinedTextField(
                        value = calories,
                        onValueChange = { calories = it.filter(Char::isDigit) },
                        label = { Text("ккал") },
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                        modifier = Modifier.fillMaxWidth(),
                    )
                    Text(
                        "БЖУ (необязательно)",
                        style = FoodAITypography.labelSmall,
                        color = FoodAIColors.TextMuted,
                    )
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedTextField(
                            value = protein,
                            onValueChange = { protein = it },
                            label = { Text("Белки") },
                            modifier = Modifier.weight(1f),
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                        )
                        OutlinedTextField(
                            value = fat,
                            onValueChange = { fat = it },
                            label = { Text("Жиры") },
                            modifier = Modifier.weight(1f),
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                        )
                        OutlinedTextField(
                            value = carbs,
                            onValueChange = { carbs = it },
                            label = { Text("Углеводы") },
                            modifier = Modifier.weight(1f),
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                        )
                    }
                    FoodAIPrimaryButton(
                        label = if (state.loading) "Сохраняем…" else "Добавить в дневник",
                        onClick = {
                            val kcal = calories.toIntOrNull() ?: return@FoodAIPrimaryButton
                            if (description.isBlank()) return@FoodAIPrimaryButton
                            viewModel.addQuick(
                                description.trim(),
                                kcal,
                                protein.replace(',', '.').toDoubleOrNull() ?: 0.0,
                                fat.replace(',', '.').toDoubleOrNull() ?: 0.0,
                                carbs.replace(',', '.').toDoubleOrNull() ?: 0.0,
                            ) {
                                onSaved()
                                onDismiss()
                            }
                        },
                        enabled = !state.loading && description.isNotBlank() &&
                            (calories.toIntOrNull() ?: 0) > 0,
                        showArrow = false,
                    )
                }
                "search" -> {
                    OutlinedTextField(
                        value = state.searchQuery,
                        onValueChange = viewModel::search,
                        label = { Text("Найти продукт") },
                        modifier = Modifier.fillMaxWidth(),
                    )
                    state.searchHits.forEach { hit ->
                        Text(
                            "${hit.name} · ${hit.caloriesPer100g.toInt()} ккал/100г",
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable { viewModel.selectHit(hit) }
                                .padding(vertical = 8.dp),
                            style = FoodAITypography.bodyLarge,
                        )
                    }
                    val hit = state.selectedHit
                    if (hit != null) {
                        Text("Выбрано: ${hit.name}", style = FoodAITypography.titleMedium)
                        OutlinedTextField(
                            value = state.grams,
                            onValueChange = viewModel::setGrams,
                            label = { Text("Граммы") },
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                            modifier = Modifier.fillMaxWidth(),
                        )
                        val kcal = state.calcKcal
                        if (kcal != null) {
                            Text(
                                "≈ $kcal ккал · Б ${state.calcProtein} · Ж ${state.calcFat} · У ${state.calcCarbs}",
                                style = FoodAITypography.bodyMedium,
                            )
                        }
                        FoodAIPrimaryButton(
                            label = "Добавить в дневник",
                            onClick = {
                                viewModel.addSearchFood {
                                    onSaved()
                                    onDismiss()
                                }
                            },
                            enabled = !state.loading,
                            showArrow = false,
                        )
                    }
                }
                "recent" -> {
                    if (state.recent.isEmpty()) {
                        Text(
                            "Пока нет недавних продуктов",
                            style = FoodAITypography.bodyMedium,
                            color = FoodAIColors.TextSecondary,
                        )
                    }
                    state.recent.forEach { item ->
                        Text(
                            "${item.description} · ${item.caloriesKcal} ккал",
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable {
                                    viewModel.addRecent(item) {
                                        onSaved()
                                        onDismiss()
                                    }
                                }
                                .padding(vertical = 8.dp),
                            style = FoodAITypography.bodyLarge,
                        )
                    }
                }
                "photo", "photo_review" -> {
                    if (state.loading) {
                        Text("Распознаём фото…", style = FoodAITypography.bodyLarge)
                    }
                    val warning = state.photoWarning
                    if (warning != null) {
                        Text(warning, style = FoodAITypography.bodyMedium)
                    }
                    if (state.photoReview.isEmpty() && !state.loading) {
                        FoodAIOutlinedButton(
                            label = "Выбрать фото",
                            onClick = { gallery.launch("image/*") },
                        )
                    }
                    state.photoReview.forEachIndexed { index, item ->
                        Column(modifier = Modifier.fillMaxWidth()) {
                            Text(
                                "${item.name}${if (item.lowConfidence) " (?)" else ""}",
                                style = FoodAITypography.titleMedium,
                            )
                            OutlinedTextField(
                                value = item.grams.toInt().toString(),
                                onValueChange = { viewModel.updatePhotoGrams(index, it) },
                                label = { Text("Граммы") },
                                enabled = item.matched,
                                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                                modifier = Modifier.fillMaxWidth(),
                            )
                            val itemKcal = item.caloriesKcal
                            if (itemKcal != null) {
                                Text("≈ $itemKcal ккал", style = FoodAITypography.bodyMedium)
                            }
                            FoodAIOutlinedButton(
                                label = "Убрать",
                                onClick = { viewModel.removePhotoItem(index) },
                            )
                        }
                    }
                    if (state.photoReview.isNotEmpty()) {
                        val total = state.photoReview.sumOf { it.caloriesKcal ?: 0 }
                        Text("Итого ≈ $total ккал", style = FoodAITypography.titleMedium)
                        FoodAIPrimaryButton(
                            label = "Добавить в дневник",
                            onClick = {
                                viewModel.confirmPhoto {
                                    onSaved()
                                    onDismiss()
                                }
                            },
                            enabled = !state.loading,
                            showArrow = false,
                        )
                    }
                }
            }
            Spacer(modifier = Modifier.height(FoodAIDimens.Space16))
        }
    }
}
