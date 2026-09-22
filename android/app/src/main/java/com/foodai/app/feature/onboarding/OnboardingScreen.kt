package com.foodai.app.feature.onboarding

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.FilterChip
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.foodai.app.core.network.TargetPreviewResponse
import com.foodai.app.core.ui.LoadingPane
import com.foodai.app.core.ui.theme.FoodAiTokens

private const val DISCLAIMER =
    "Расчёты приблизительны и не заменяют врача или диетолога."

@Composable
fun OnboardingRoute(
    generatePlan: Boolean = true,
    onFinished: () -> Unit,
    viewModel: OnboardingViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) {
        viewModel.setGeneratePlan(generatePlan)
    }
    LaunchedEffect(state.finished) {
        if (state.finished) onFinished()
    }
    if (state.step == OnboardingStep.Loading) {
        LoadingPane(
            if (generatePlan) OnboardingStep.Loading.title else "Сохраняем профиль…",
        )
        return
    }
    OnboardingScreen(
        state = state,
        onDraftChange = viewModel::updateDraft,
        onBack = viewModel::back,
        onNext = viewModel::next,
        onRefreshPreview = viewModel::refreshPreview,
    )
}

@Composable
fun OnboardingScreen(
    state: OnboardingUiState,
    onDraftChange: ((OnboardingDraft) -> OnboardingDraft) -> Unit,
    onBack: () -> Unit,
    onNext: () -> Unit,
    onRefreshPreview: () -> Unit,
) {
    val progress = (state.step.index + 1) / OnboardingStep.formSteps.size.toFloat()
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(FoodAiTokens.SpaceLg.dp),
    ) {
        LinearProgressIndicator(
            progress = { progress },
            modifier = Modifier.fillMaxWidth(),
        )
        Spacer(Modifier.height(FoodAiTokens.SpaceMd.dp))
        Text(state.step.title, style = MaterialTheme.typography.headlineMedium)
        Spacer(Modifier.height(FoodAiTokens.SpaceMd.dp))
        Column(
            modifier = Modifier
                .weight(1f)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(FoodAiTokens.SpaceMd.dp),
        ) {
            when (state.step) {
                OnboardingStep.Goal -> GoalStep(state.draft, onDraftChange)
                OnboardingStep.AboutYou -> AboutStep(state.draft, onDraftChange)
                OnboardingStep.Eating -> EatingStep(state.draft, onDraftChange)
                OnboardingStep.Foods -> FoodsStep(state.draft, onDraftChange)
                OnboardingStep.Budget -> BudgetStep(state.draft, onDraftChange)
                OnboardingStep.CookTime -> CookTimeStep(state.draft, onDraftChange)
                OnboardingStep.Pantry -> PantryStep(state.draft, state.preview, onDraftChange, onRefreshPreview)
                OnboardingStep.Loading -> Unit
            }
            if (state.error != null) {
                Text(state.error, color = MaterialTheme.colorScheme.error)
            }
        }
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            TextButton(
                onClick = onBack,
                enabled = state.step != OnboardingStep.Goal && !state.isSubmitting,
            ) { Text("Назад") }
            Button(onClick = onNext, enabled = !state.isSubmitting) {
                Text(if (state.step == OnboardingStep.Pantry) "Создать план" else "Далее")
            }
        }
    }
}

@Composable
private fun GoalStep(
    draft: OnboardingDraft,
    onDraftChange: ((OnboardingDraft) -> OnboardingDraft) -> Unit,
) {
    Text(DISCLAIMER, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
    ChipRow(
        options = listOf(
            "lose_weight" to "Похудеть",
            "maintain_weight" to "Сохранить вес",
            "gain_weight" to "Набрать вес",
        ),
        selected = draft.goalType,
        onSelect = { value -> onDraftChange { it.copy(goalType = value) } },
    )
    Field("Целевой вес, кг", draft.targetWeightKg) {
        onDraftChange { d -> d.copy(targetWeightKg = it) }
    }
    Field("Скорость, кг/нед (макс. 1.0)", draft.desiredWeeklyChangeKg) {
        onDraftChange { d -> d.copy(desiredWeeklyChangeKg = it) }
    }
    Text(
        "Безопасный максимум NutritionEngine — 1 кг в неделю.",
        style = MaterialTheme.typography.bodySmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
}

@Composable
private fun AboutStep(
    draft: OnboardingDraft,
    onDraftChange: ((OnboardingDraft) -> OnboardingDraft) -> Unit,
) {
    ChipRow(
        options = listOf("female" to "Женский", "male" to "Мужской", "other" to "Другое"),
        selected = draft.sex,
        onSelect = { value -> onDraftChange { it.copy(sex = value) } },
    )
    Field("Возраст", draft.ageYears) { onDraftChange { d -> d.copy(ageYears = it) } }
    Field("Рост, см", draft.heightCm) { onDraftChange { d -> d.copy(heightCm = it) } }
    Field("Текущий вес, кг", draft.currentWeightKg) { onDraftChange { d -> d.copy(currentWeightKg = it) } }
}

@Composable
private fun EatingStep(
    draft: OnboardingDraft,
    onDraftChange: ((OnboardingDraft) -> OnboardingDraft) -> Unit,
) {
    ChipRow(
        options = listOf(
            "sedentary" to "Сидячий",
            "light" to "Лёгкий",
            "moderate" to "Средний",
            "high" to "Высокий",
            "very_high" to "Очень высокий",
        ),
        selected = draft.activityLevel,
        onSelect = { value -> onDraftChange { it.copy(activityLevel = value) } },
    )
    Field("Приёмов пищи в день", draft.mealsPerDay) {
        onDraftChange { d -> d.copy(mealsPerDay = it) }
    }
    ChipRow(
        options = listOf(
            "auto" to "Авто",
            "deficit" to "Дефицит",
            "surplus" to "Профицит",
            "target" to "Точная цель",
        ),
        selected = draft.dailyCalorieMode,
        onSelect = { value -> onDraftChange { it.copy(dailyCalorieMode = value) } },
    )
    if (draft.dailyCalorieMode != "auto") {
        Field("Значение, ккал", draft.dailyCalorieValue) {
            onDraftChange { d -> d.copy(dailyCalorieValue = it) }
        }
    }
}

@Composable
private fun FoodsStep(
    draft: OnboardingDraft,
    onDraftChange: ((OnboardingDraft) -> OnboardingDraft) -> Unit,
) {
    Field("Любимые (через запятую)", draft.likedFoods) {
        onDraftChange { d -> d.copy(likedFoods = it) }
    }
    Field("Нелюбимые", draft.dislikedFoods) { onDraftChange { d -> d.copy(dislikedFoods = it) } }
    Field("Исключения", draft.excludedFoods) { onDraftChange { d -> d.copy(excludedFoods = it) } }
    Field("Аллергии", draft.allergies) { onDraftChange { d -> d.copy(allergies = it) } }
}

@Composable
private fun BudgetStep(
    draft: OnboardingDraft,
    onDraftChange: ((OnboardingDraft) -> OnboardingDraft) -> Unit,
) {
    Field("Бюджет на неделю", draft.groceryBudgetWeekly) {
        onDraftChange { d -> d.copy(groceryBudgetWeekly = it) }
    }
    Field("Валюта", draft.currency) { onDraftChange { d -> d.copy(currency = it.uppercase()) } }
    Field("Размер семьи", draft.householdSize) {
        onDraftChange { d -> d.copy(householdSize = it) }
    }
}

@Composable
private fun CookTimeStep(
    draft: OnboardingDraft,
    onDraftChange: ((OnboardingDraft) -> OnboardingDraft) -> Unit,
) {
    Field("Макс. время готовки, мин", draft.maxCookTimeMinutes) {
        onDraftChange { d -> d.copy(maxCookTimeMinutes = it) }
    }
}

@Composable
private fun ColumnScope.PantryStep(
    draft: OnboardingDraft,
    preview: TargetPreviewResponse?,
    onDraftChange: ((OnboardingDraft) -> OnboardingDraft) -> Unit,
    onRefreshPreview: () -> Unit,
) {
    Text(
        "Проверьте ответы. Продукты дома — по строке: «яйца», «яйца 10» или «рис 2 kg».",
        style = MaterialTheme.typography.bodyMedium,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
    Field("Что есть дома", draft.pantryText, singleLine = false) {
        onDraftChange { d -> d.copy(pantryText = it) }
    }
    TextButton(onClick = onRefreshPreview) { Text("Обновить preview цели") }
    if (preview != null) {
        Text(
            "Цель: ${preview.recommendedCalorieTargetKcal} ккал · " +
                "Б ${preview.macroTargetsG.protein} / Ж ${preview.macroTargetsG.fat} / " +
                "У ${preview.macroTargetsG.carbohydrate}",
            style = MaterialTheme.typography.titleMedium,
        )
        preview.warnings.forEach { warning ->
            Text(warning, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    } else {
        Text(DISCLAIMER, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
private fun Field(
    label: String,
    value: String,
    singleLine: Boolean = true,
    onChange: (String) -> Unit,
) {
    OutlinedTextField(
        value = value,
        onValueChange = onChange,
        modifier = Modifier.fillMaxWidth(),
        label = { Text(label) },
        singleLine = singleLine,
        minLines = if (singleLine) 1 else 3,
    )
}

@Composable
private fun ChipRow(
    options: List<Pair<String, String>>,
    selected: String,
    onSelect: (String) -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        options.forEach { (value, label) ->
            FilterChip(
                selected = selected == value,
                onClick = { onSelect(value) },
                label = { Text(label) },
            )
        }
    }
}
