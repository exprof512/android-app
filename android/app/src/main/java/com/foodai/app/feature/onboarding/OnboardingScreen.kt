package com.foodai.app.feature.onboarding

import androidx.compose.foundation.background
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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.DirectionsWalk
import androidx.compose.material.icons.outlined.AccessibilityNew
import androidx.compose.material.icons.outlined.Chair
import androidx.compose.material.icons.outlined.Favorite
import androidx.compose.material.icons.outlined.FitnessCenter
import androidx.compose.material.icons.outlined.LocalFireDepartment
import androidx.compose.material.icons.outlined.MonitorWeight
import androidx.compose.material.icons.outlined.TrackChanges
import androidx.compose.material3.Icon
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.foodai.app.core.ui.components.FoodAIFoodTile
import com.foodai.app.core.ui.components.FoodAIInfoCard
import com.foodai.app.core.ui.components.FoodAIInput
import com.foodai.app.core.ui.components.FoodAILoading
import com.foodai.app.core.ui.components.FoodAIMetricCard
import com.foodai.app.core.ui.components.FoodAIPrivacyBadge
import com.foodai.app.core.ui.components.FoodAISearchField
import com.foodai.app.core.ui.components.FoodAISelectableCard
import com.foodai.app.core.ui.components.FoodAISelectableOption
import com.foodai.app.core.ui.components.FoodAIStepper
import com.foodai.app.core.ui.components.FoodAIStatusDot
import com.foodai.app.core.ui.components.OnboardingScaffold
import com.foodai.app.core.ui.theme.FoodAIColors
import com.foodai.app.core.ui.theme.FoodAIDimens
import com.foodai.app.core.ui.theme.FoodAIShapes
import com.foodai.app.core.ui.theme.FoodAITypography
import kotlin.math.pow
import kotlin.math.roundToInt

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
    if (state.hydrating) {
        FoodAILoading("Загружаем анкету…")
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
    val stepNumber = state.step.index + 1
    OnboardingScaffold(
        step = stepNumber,
        total = OnboardingStep.TOTAL,
        title = state.step.title,
        subtitle = state.step.subtitle,
        onBack = if (state.step == OnboardingStep.Goal || state.isSubmitting) null else onBack,
        primaryLabel = when (state.step) {
            OnboardingStep.Pantry -> "Создать план"
            else -> "Далее"
        },
        onPrimary = onNext,
        primaryEnabled = !state.isSubmitting,
        showPrimary = state.step != OnboardingStep.Loading,
    ) {
        when (state.step) {
            OnboardingStep.Goal -> GoalStep(state.draft, onDraftChange)
            OnboardingStep.AboutYou -> AboutStep(state.draft, onDraftChange)
            OnboardingStep.GoalDetails -> GoalDetailsStep(state.draft, onDraftChange)
            OnboardingStep.Activity -> ActivityStep(state.draft, onDraftChange)
            OnboardingStep.Meals -> MealsStep(state.draft, onDraftChange)
            OnboardingStep.Foods -> FoodsStep(state.draft, onDraftChange)
            OnboardingStep.Budget -> BudgetStep(state.draft, onDraftChange)
            OnboardingStep.CookTime -> CookTimeStep(state.draft, onDraftChange)
            OnboardingStep.Pantry -> PantryStep(state.draft, onDraftChange)
            OnboardingStep.Loading -> GeneratingStep()
        }
        if (state.error != null) {
            Text(state.error, color = FoodAIColors.Error, style = FoodAITypography.bodyMedium)
        }
    }
}

@Composable
private fun GoalStep(
    draft: OnboardingDraft,
    onDraftChange: ((OnboardingDraft) -> OnboardingDraft) -> Unit,
) {
    data class Option(val apiValue: String, val title: String, val subtitle: String, val icon: ImageVector)
    val options = listOf(
        Option("lose_weight", "Похудеть", "Снизить вес и чувствовать себя лучше", Icons.Outlined.MonitorWeight),
        Option("gain_weight", "Набрать вес", "Увеличить массу и силу", Icons.Outlined.FitnessCenter),
        Option("maintain_weight", "Поддерживать вес", "Сохранить текущую форму", Icons.Outlined.TrackChanges),
        Option("maintain_weight", "Улучшить питание", "Питаться полезнее и сбалансированнее", Icons.Outlined.Favorite),
    )
    var selectedIndex by remember {
        mutableStateOf(
            when (draft.goalType) {
                "lose_weight" -> 0
                "gain_weight" -> 1
                else -> 2
            },
        )
    }
    options.forEachIndexed { index, option ->
        FoodAISelectableCard(
            title = option.title,
            subtitle = option.subtitle,
            selected = selectedIndex == index,
            onClick = {
                selectedIndex = index
                onDraftChange {
                    it.copy(
                        goalType = option.apiValue,
                        desiredWeeklyChangeKg = if (option.apiValue == "maintain_weight") {
                            "0"
                        } else {
                            it.desiredWeeklyChangeKg.ifBlank { "0.4" }
                        },
                    )
                }
            },
            leading = {
                Icon(option.icon, contentDescription = null, tint = FoodAIColors.Primary, modifier = Modifier.size(36.dp))
            },
        )
    }
    FoodAIInfoCard(text = "Ты всегда можешь изменить цель в настройках профиля")
}

@Composable
private fun AboutStep(
    draft: OnboardingDraft,
    onDraftChange: ((OnboardingDraft) -> OnboardingDraft) -> Unit,
) {
    LaunchedEffect(Unit) {
        if (draft.ageYears.isBlank() || draft.heightCm.isBlank() || draft.currentWeightKg.isBlank()) {
            onDraftChange {
                it.copy(
                    ageYears = it.ageYears.ifBlank { "30" },
                    heightCm = it.heightCm.ifBlank { "170" },
                    currentWeightKg = it.currentWeightKg.ifBlank { "70" },
                    sex = it.sex.ifBlank { "female" },
                )
            }
        }
    }
    FoodAIPrivacyBadge(text = "Твои данные в безопасности и не передаются третьим лицам")
    Text("Пол", style = FoodAITypography.titleMedium)
    Row(horizontalArrangement = Arrangement.spacedBy(FoodAIDimens.Space12)) {
        FoodAISelectableOption(
            label = "Мужской",
            selected = draft.sex == "male",
            onClick = { onDraftChange { it.copy(sex = "male") } },
            modifier = Modifier.weight(1f),
        )
        FoodAISelectableOption(
            label = "Женский",
            selected = draft.sex == "female" || draft.sex.isBlank(),
            onClick = { onDraftChange { it.copy(sex = "female") } },
            modifier = Modifier.weight(1f),
        )
    }
    val age = draft.ageYears.toIntOrNull() ?: 30
    val height = draft.heightCm.toDoubleOrNull()?.roundToInt() ?: 170
    val weight = draft.currentWeightKg.toDoubleOrNull()?.roundToInt() ?: 70
    FoodAIStepper(
        label = "Возраст",
        value = age.toString(),
        unit = "года",
        onDecrement = { onDraftChange { it.copy(ageYears = (age - 1).coerceAtLeast(14).toString()) } },
        onIncrement = { onDraftChange { it.copy(ageYears = (age + 1).coerceAtMost(100).toString()) } },
    )
    FoodAIStepper(
        label = "Рост",
        value = height.toString(),
        unit = "см",
        onDecrement = { onDraftChange { it.copy(heightCm = (height - 1).coerceAtLeast(120).toString()) } },
        onIncrement = { onDraftChange { it.copy(heightCm = (height + 1).coerceAtMost(230).toString()) } },
    )
    FoodAIStepper(
        label = "Текущий вес",
        value = weight.toString(),
        unit = "кг",
        onDecrement = { onDraftChange { it.copy(currentWeightKg = (weight - 1).coerceAtLeast(35).toString()) } },
        onIncrement = { onDraftChange { it.copy(currentWeightKg = (weight + 1).coerceAtMost(250).toString()) } },
    )
    val bmi = remember(height, weight) {
        if (height > 0) weight / (height / 100.0).pow(2) else 0.0
    }
    if (bmi > 0) {
        FoodAIMetricCard(
            title = "Индекс массы тела (ИМТ)",
            value = String.format("%.1f", bmi),
            subtitle = bmiLabel(bmi),
        )
    }
}

private fun bmiLabel(bmi: Double): String = when {
    bmi < 18.5 -> "недостаточный вес"
    bmi < 25.0 -> "нормальный вес"
    bmi < 30.0 -> "избыточный вес"
    else -> "ожирение"
}

@Composable
private fun GoalDetailsStep(
    draft: OnboardingDraft,
    onDraftChange: ((OnboardingDraft) -> OnboardingDraft) -> Unit,
) {
    val current = draft.currentWeightKg.toDoubleOrNull() ?: 70.0
    val target = draft.targetWeightKg.replace(',', '.').toDoubleOrNull()
        ?: when (draft.goalType) {
            "lose_weight" -> (current - 5).coerceAtLeast(40.0)
            "gain_weight" -> current + 5
            else -> current
        }
    val delta = target - current
    val weekly = draft.desiredWeeklyChangeKg.toDoubleOrNull() ?: 0.4
    val weeks = if (kotlin.math.abs(weekly) > 0.01) {
        (kotlin.math.abs(delta) / weekly).coerceAtLeast(1.0).roundToInt()
    } else {
        0
    }

    if (draft.goalType == "maintain_weight") {
        Text(
            "Для поддержания веса скорость изменений = 0. Можно сразу перейти далее.",
            style = FoodAITypography.bodyMedium,
            color = FoodAIColors.TextSecondary,
        )
        FoodAIMetricCard(
            title = "Текущий вес",
            value = "${current.roundToInt()} кг",
            subtitle = "Цель — сохранить форму",
        )
    } else {
        Row(horizontalArrangement = Arrangement.spacedBy(FoodAIDimens.Space12)) {
            FoodAIMetricCard(
                title = "Сейчас",
                value = "${current.roundToInt()} кг",
                modifier = Modifier.weight(1f),
            )
            FoodAIMetricCard(
                title = "Цель",
                value = "${target.roundToInt()} кг",
                modifier = Modifier.weight(1f),
            )
        }
        val diffLabel = if (delta < 0) "−${(-delta).roundToInt()} кг" else "+${delta.roundToInt()} кг"
        FoodAIMetricCard(
            title = "Разница",
            value = diffLabel,
            subtitle = if (weeks > 0) "Ориентировочно $weeks нед." else null,
        )
        FoodAIStepper(
            label = "Целевой вес",
            value = target.roundToInt().toString(),
            unit = "кг",
            onDecrement = {
                onDraftChange {
                    it.copy(targetWeightKg = (target.roundToInt() - 1).coerceAtLeast(35).toString())
                }
            },
            onIncrement = {
                onDraftChange {
                    it.copy(targetWeightKg = (target.roundToInt() + 1).coerceAtMost(250).toString())
                }
            },
        )
        Text("Скорость изменений", style = FoodAITypography.titleMedium)
        Row(horizontalArrangement = Arrangement.spacedBy(FoodAIDimens.Space8)) {
            listOf(0.3, 0.4, 0.5).forEach { rate ->
                FoodAISelectableOption(
                    label = "$rate кг/нед",
                    selected = kotlin.math.abs(weekly - rate) < 0.05,
                    onClick = {
                        onDraftChange { it.copy(desiredWeeklyChangeKg = rate.toString()) }
                    },
                    modifier = Modifier.weight(1f),
                )
            }
        }
        LaunchedEffect(draft.targetWeightKg, draft.goalType) {
            if (draft.targetWeightKg.isBlank()) {
                onDraftChange { it.copy(targetWeightKg = target.roundToInt().toString()) }
            }
        }
    }
    FoodAIInfoCard(text = DISCLAIMER)
}

@Composable
private fun ActivityStep(
    draft: OnboardingDraft,
    onDraftChange: ((OnboardingDraft) -> OnboardingDraft) -> Unit,
) {
    val options = listOf(
        Triple("sedentary", "Минимальная", "Практически не двигаюсь. Сидячая работа, мало активности.") to Icons.Outlined.Chair,
        Triple("light", "Низкая", "Лёгкая активность. Небольшие прогулки, редкие тренировки.") to Icons.AutoMirrored.Outlined.DirectionsWalk,
        Triple("moderate", "Средняя", "Регулярные прогулки, 1–3 тренировки в неделю.") to Icons.Outlined.AccessibilityNew,
        Triple("high", "Высокая", "3–5 тренировок в неделю. Активный образ жизни.") to Icons.Outlined.FitnessCenter,
        Triple("very_high", "Очень высокая", "Интенсивные тренировки почти каждый день.") to Icons.Outlined.LocalFireDepartment,
    )
    options.forEach { (meta, icon) ->
        val (value, title, subtitle) = meta
        FoodAISelectableCard(
            title = title,
            subtitle = subtitle,
            selected = draft.activityLevel == value,
            onClick = { onDraftChange { it.copy(activityLevel = value) } },
            leading = {
                Icon(icon, contentDescription = null, tint = FoodAIColors.Primary, modifier = Modifier.size(32.dp))
            },
        )
    }
    FoodAIInfoCard(text = "Не переживай, при необходимости ты всегда сможешь изменить уровень активности в настройках.")
}

@Composable
private fun BudgetStep(
    draft: OnboardingDraft,
    onDraftChange: ((OnboardingDraft) -> OnboardingDraft) -> Unit,
) {
    val displayMonthly = remember(draft.groceryBudgetWeekly) {
        val weekly = draft.groceryBudgetWeekly.toFloatOrNull() ?: 2000f
        (weekly * 4f).coerceIn(2000f, 20000f)
    }
    var slider by remember(displayMonthly) { mutableStateOf(displayMonthly) }

    Text("Примерный бюджет в месяц", style = FoodAITypography.labelMedium)
    Text(
        "${slider.toInt()} ₽",
        style = FoodAITypography.headlineMedium,
    )
    androidx.compose.material3.Slider(
        value = slider,
        onValueChange = {
            slider = it
            onDraftChange { d -> d.copy(groceryBudgetWeekly = (it / 4f).toInt().toString()) }
        },
        valueRange = 2000f..20000f,
        colors = androidx.compose.material3.SliderDefaults.colors(
            thumbColor = FoodAIColors.Primary,
            activeTrackColor = FoodAIColors.Primary,
            inactiveTrackColor = FoodAIColors.Divider,
        ),
    )
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text("2 000 ₽ · Эконом", style = FoodAITypography.labelSmall)
        Text("20 000 ₽ · Без ограничений", style = FoodAITypography.labelSmall)
    }
    Row(horizontalArrangement = Arrangement.spacedBy(FoodAIDimens.Space8)) {
        BudgetTier("Эконом", "2 000 – 5 000 ₽", "Простые и доступные рецепты", slider < 5000f, Modifier.weight(1f)) {
            slider = 3500f
            onDraftChange { it.copy(groceryBudgetWeekly = "875") }
        }
        BudgetTier("Средний", "5 000 – 15 000 ₽", "Оптимальный баланс", slider in 5000f..15000f, Modifier.weight(1f)) {
            slider = 8000f
            onDraftChange { it.copy(groceryBudgetWeekly = "2000") }
        }
        BudgetTier("Без лимита", "от 15 000 ₽", "Максимум разнообразия", slider > 15000f, Modifier.weight(1f)) {
            slider = 18000f
            onDraftChange { it.copy(groceryBudgetWeekly = "4500") }
        }
    }
    FoodAIInfoCard(text = "Мы учитываем местные цены. Рецепты и список покупок адаптируются под регион.")
    Text("Где ты обычно покупаешь продукты?", style = FoodAITypography.titleMedium)
    Text("Можно выбрать несколько вариантов", style = FoodAITypography.bodySmall)
    val stores = listOf("Пятёрочка", "Магнит", "Лента", "Перекрёсток", "ВкусВилл", "Рынок")
    val selectedStores = draft.splitCsv(draft.preferredStores).toSet()
    stores.chunked(3).forEach { row ->
        Row(horizontalArrangement = Arrangement.spacedBy(FoodAIDimens.Space8)) {
            row.forEach { store ->
                val on = selectedStores.contains(store)
                FoodAISelectableOption(
                    label = store,
                    selected = on,
                    onClick = {
                        val next = selectedStores.toMutableSet()
                        if (on) next.remove(store) else next.add(store)
                        onDraftChange { it.copy(preferredStores = next.joinToString(", ")) }
                    },
                    modifier = Modifier.weight(1f),
                )
            }
            repeat(3 - row.size) { Spacer(Modifier.weight(1f)) }
        }
    }
    Row(verticalAlignment = Alignment.CenterVertically) {
        androidx.compose.material3.Checkbox(
            checked = draft.considerDiscounts,
            onCheckedChange = { onDraftChange { d -> d.copy(considerDiscounts = it) } },
            colors = androidx.compose.material3.CheckboxDefaults.colors(checkedColor = FoodAIColors.Primary),
        )
        Column {
            Text(
                "Учитывать ориентировочные цены",
                style = FoodAITypography.titleSmall,
            )
            Text(
                "Цены в каталоге приблизительные. Отдельных данных о магазинных акциях нет — переключатель влияет только на то, показывать ли стоимость в плане.",
                style = FoodAITypography.bodySmall,
            )
        }
    }
}

@Composable
private fun BudgetTier(
    title: String,
    range: String,
    subtitle: String,
    selected: Boolean,
    modifier: Modifier = Modifier,
    onClick: () -> Unit,
) {
    FoodAISelectableCard(
        title = title,
        subtitle = "$range\n$subtitle",
        selected = selected,
        onClick = onClick,
        modifier = modifier,
    )
}

@Composable
private fun CookTimeStep(
    draft: OnboardingDraft,
    onDraftChange: ((OnboardingDraft) -> OnboardingDraft) -> Unit,
) {
    val options = listOf(
        Triple(15, "15 минут", "Максимально быстро. Простые рецепты."),
        Triple(30, "30 минут", "Оптимальный вариант на каждый день."),
        Triple(60, "60 минут", "Больше разнообразия и интересных блюд."),
        Triple(0, "Неважно", "Готовлю с удовольствием. Без ограничений по времени."),
    )
    val current = draft.maxCookTimeMinutes.toIntOrNull() ?: 30
    options.chunked(2).forEach { row ->
        Row(horizontalArrangement = Arrangement.spacedBy(FoodAIDimens.Space8)) {
            row.forEach { (minutes, title, subtitle) ->
                val selected = if (minutes == 0) current == 0 || current >= 90 else current == minutes
                FoodAISelectableCard(
                    title = title,
                    subtitle = subtitle,
                    selected = selected,
                    onClick = {
                        onDraftChange {
                            it.copy(maxCookTimeMinutes = if (minutes == 0) "120" else minutes.toString())
                        }
                    },
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }
    FoodAIInfoCard(text = "Мы учтём твоё время. В плане будут только рецепты, которые реально впишутся в твой день.")
}

@Composable
private fun PantryStep(
    draft: OnboardingDraft,
    onDraftChange: ((OnboardingDraft) -> OnboardingDraft) -> Unit,
) {
    var query by remember { mutableStateOf("") }
    var category by remember { mutableStateOf("Все") }
    val selected = remember(draft.pantryText) {
        draft.pantryText.lines().map { it.trim() }.filter { it.isNotEmpty() }.map {
            it.split(Regex("\\s+")).first()
        }.toMutableSet()
    }
    FoodAISearchField(
        value = query,
        onValueChange = { query = it },
        placeholder = "Найти продукт (например, курица, рис, помидоры)",
    )
    val chips = listOf("Все", "Овощи", "Фрукты", "Мясо", "Крупы", "Молочка")
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(FoodAIDimens.Space8),
    ) {
        chips.take(4).forEach { chip ->
            FoodAISelectableOption(
                label = chip,
                selected = category == chip,
                onClick = { category = chip },
                modifier = Modifier,
            )
        }
    }
    val items = PantryCatalog.all.filter {
        (category == "Все" || it.category == category) &&
            (query.isBlank() || it.name.contains(query, ignoreCase = true))
    }
    items.chunked(4).forEach { row ->
        Row(horizontalArrangement = Arrangement.spacedBy(FoodAIDimens.Space8)) {
            row.forEach { item ->
                val on = selected.contains(item.name)
                FoodAIFoodTile(
                    emoji = item.emoji,
                    label = item.name,
                    selected = on,
                    onClick = {
                        val next = selected.toMutableSet()
                        if (on) next.remove(item.name) else next.add(item.name)
                        onDraftChange {
                            it.copy(pantryText = next.joinToString("\n") { name -> "$name 1 piece" })
                        }
                    },
                    modifier = Modifier.weight(1f),
                )
            }
            repeat(4 - row.size) { Spacer(Modifier.weight(1f)) }
        }
    }
    FoodAIInfoCard(text = "Чем больше продуктов отметишь, тем точнее и экономнее будет план.")
}

@Composable
private fun GeneratingStep() {
    var done by remember { mutableStateOf(0) }
    LaunchedEffect(Unit) {
        repeat(4) {
            kotlinx.coroutines.delay(700)
            done = it + 1
        }
    }
    val steps = listOf(
        "Анализируем твои цели" to "Вес, активность, предпочтения",
        "Подбираем рецепты" to "Учитываем твои продукты и бюджет",
        "Составляем план питания" to "Сбалансированный и разнообразный",
        "Добавляем рекомендации" to "Почти готово…",
    )
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(160.dp)
            .clip(FoodAIShapes.CardLarge)
            .background(FoodAIColors.PrimarySoft),
        contentAlignment = Alignment.Center,
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text("🤖", style = FoodAITypography.displayMedium)
            Text(
                "Создаём твой персональный план",
                style = FoodAITypography.titleMedium,
                color = FoodAIColors.PrimaryDark,
            )
        }
    }
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(FoodAIShapes.CardLarge)
            .background(FoodAIColors.Surface)
            .padding(FoodAIDimens.Space16),
        verticalArrangement = Arrangement.spacedBy(FoodAIDimens.Space16),
    ) {
        steps.forEachIndexed { index, (title, subtitle) ->
            val complete = index < done
            val loading = index == done
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(FoodAIDimens.Space12),
            ) {
                FoodAIStatusDot(complete = complete, loading = loading)
                Column {
                    Text(title, style = FoodAITypography.titleMedium)
                    Text(subtitle, style = FoodAITypography.bodySmall)
                }
            }
        }
    }
    FoodAIInfoCard(text = "Это займёт всего несколько секунд. Спасибо за доверие!")
}

@Composable
private fun MealsStep(
    draft: OnboardingDraft,
    onDraftChange: ((OnboardingDraft) -> OnboardingDraft) -> Unit,
) {
    Text("Количество приёмов пищи", style = FoodAITypography.titleMedium)
    Text("Сколько раз в день тебе удобно есть?", style = FoodAITypography.bodySmall)
    Row(horizontalArrangement = Arrangement.spacedBy(FoodAIDimens.Space8)) {
        listOf("2", "3", "4", "5").forEach { value ->
            FoodAISelectableOption(
                label = "$value раза",
                selected = draft.mealsPerDay == value,
                onClick = { onDraftChange { it.copy(mealsPerDay = value) } },
                modifier = Modifier.weight(1f),
            )
        }
    }
    val snacksOn = (draft.mealsPerDay.toIntOrNull() ?: 3) >= 4
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = FoodAIDimens.Space8),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text("Перекусы", style = FoodAITypography.titleMedium)
            Text("Включить перекусы в план?", style = FoodAITypography.bodySmall)
        }
        Switch(
            checked = snacksOn,
            onCheckedChange = { enabled ->
                onDraftChange {
                    it.copy(mealsPerDay = if (enabled) "4" else "3")
                }
            },
            colors = SwitchDefaults.colors(
                checkedTrackColor = FoodAIColors.Primary,
                checkedThumbColor = FoodAIColors.Surface,
            ),
        )
    }
    FoodAIInfoCard(text = "Время приёмов пищи всегда можно изменить в настройках")
}

@Composable
private fun FoodsStep(
    draft: OnboardingDraft,
    onDraftChange: ((OnboardingDraft) -> OnboardingDraft) -> Unit,
) {
    var query by remember { mutableStateOf("") }
    val selected = remember(draft.likedFoods) {
        draft.splitCsv(draft.likedFoods).toMutableSet()
    }
    FoodAISearchField(
        value = query,
        onValueChange = { query = it },
        placeholder = "Найти продукт (например, курица, рис, брокколи)",
    )
    FoodCatalog.categories.forEach { category ->
        val items = category.items.filter {
            query.isBlank() || it.name.contains(query, ignoreCase = true)
        }
        if (items.isEmpty()) return@forEach
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text("${category.emoji}  ${category.title}", style = FoodAITypography.titleMedium)
            androidx.compose.material3.TextButton(
                onClick = {
                    val next = selected.toMutableSet()
                    next.addAll(category.items.map { it.name })
                    onDraftChange { it.copy(likedFoods = next.joinToString(", ")) }
                },
            ) {
                Text("Выбрать всё", color = FoodAIColors.Primary)
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(FoodAIDimens.Space8)) {
            items.take(5).forEach { item ->
                val isSelected = selected.contains(item.name)
                FoodAIFoodTile(
                    emoji = item.emoji,
                    label = item.name,
                    selected = isSelected,
                    onClick = {
                        val next = selected.toMutableSet()
                        if (isSelected) next.remove(item.name) else next.add(item.name)
                        onDraftChange { it.copy(likedFoods = next.joinToString(", ")) }
                    },
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }
    FoodAIInput(
        value = draft.dislikedFoods,
        onValueChange = { onDraftChange { d -> d.copy(dislikedFoods = it) } },
        label = "Нелюбимые продукты",
    )
    FoodAIInput(
        value = draft.allergies,
        onValueChange = { onDraftChange { d -> d.copy(allergies = it) } },
        label = "Аллергии",
    )
    FoodAIInfoCard(text = "Чем больше ты выберешь любимых продуктов, тем разнообразнее и вкуснее будет твой план питания.")
}

private data class FoodItem(val name: String, val emoji: String, val category: String = "")
private data class FoodCategory(val title: String, val emoji: String, val items: List<FoodItem>)

private object FoodCatalog {
    val categories = listOf(
        FoodCategory(
            "Мясо", "🥩",
            listOf(
                FoodItem("Курица", "🍗"),
                FoodItem("Говядина", "🥩"),
                FoodItem("Индейка", "🦃"),
                FoodItem("Свинина", "🥓"),
                FoodItem("Баранина", "🍖"),
            ),
        ),
        FoodCategory(
            "Гарниры", "🍲",
            listOf(
                FoodItem("Рис", "🍚"),
                FoodItem("Гречка", "🥣"),
                FoodItem("Картофель", "🥔"),
                FoodItem("Макароны", "🍝"),
                FoodItem("Киноа", "🌾"),
            ),
        ),
        FoodCategory(
            "Овощи", "🌿",
            listOf(
                FoodItem("Помидоры", "🍅"),
                FoodItem("Огурцы", "🥒"),
                FoodItem("Брокколи", "🥦"),
                FoodItem("Перец", "🫑"),
                FoodItem("Морковь", "🥕"),
            ),
        ),
        FoodCategory(
            "Фрукты", "🍎",
            listOf(
                FoodItem("Яблоки", "🍎"),
                FoodItem("Бананы", "🍌"),
                FoodItem("Ягоды", "🫐"),
                FoodItem("Апельсины", "🍊"),
                FoodItem("Виноград", "🍇"),
            ),
        ),
    )
}

private object PantryCatalog {
    val all = listOf(
        FoodItem("Курица", "🍗", "Мясо"),
        FoodItem("Говядина", "🥩", "Мясо"),
        FoodItem("Яйца", "🥚", "Мясо"),
        FoodItem("Рыба", "🐟", "Мясо"),
        FoodItem("Помидоры", "🍅", "Овощи"),
        FoodItem("Огурцы", "🥒", "Овощи"),
        FoodItem("Перец", "🫑", "Овощи"),
        FoodItem("Лук", "🧅", "Овощи"),
        FoodItem("Чеснок", "🧄", "Овощи"),
        FoodItem("Картофель", "🥔", "Крупы"),
        FoodItem("Рис", "🍚", "Крупы"),
        FoodItem("Гречка", "🥣", "Крупы"),
        FoodItem("Макароны", "🍝", "Крупы"),
        FoodItem("Молоко", "🥛", "Молочка"),
        FoodItem("Сыр", "🧀", "Молочка"),
        FoodItem("Йогурт", "🫙", "Молочка"),
        FoodItem("Яблоки", "🍎", "Фрукты"),
        FoodItem("Бананы", "🍌", "Фрукты"),
    )
}
