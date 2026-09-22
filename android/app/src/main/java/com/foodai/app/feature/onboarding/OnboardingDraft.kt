package com.foodai.app.feature.onboarding

import kotlinx.serialization.Serializable
import com.foodai.app.core.network.PantryItemDto
import com.foodai.app.core.network.ProfileResponse
import com.foodai.app.core.network.ProfileUpdateRequest
import com.foodai.app.core.network.TargetPreviewRequest

enum class OnboardingStep(val index: Int, val title: String, val subtitle: String) {
    Goal(0, "Какая у тебя цель?", "Мы подберём оптимальный план питания именно для тебя"),
    AboutYou(1, "Расскажи о себе", "Эти данные помогут точнее рассчитать твой план питания"),
    GoalDetails(2, "Параметры цели", "Укажи целевой вес и комфортную скорость изменений"),
    Activity(3, "Твой уровень активности", "Это поможет правильно рассчитать калорийность и подобрать план питания"),
    Meals(4, "Как тебе удобно питаться?", "Мы подберём оптимальное количество приёмов пищи"),
    Foods(5, "Твои предпочтения", "Выбери продукты, которые ты любишь. Мы будем учитывать их при создании твоего плана питания."),
    Budget(6, "Какой у тебя бюджет на питание?", "Мы подберём рецепты и продукты с учётом твоих финансовых возможностей."),
    CookTime(7, "Сколько времени ты готов готовить?", "Мы подберём рецепты, которые подходят под твой график и образ жизни."),
    Pantry(8, "Какие продукты у тебя есть дома?", "Отметь то, что уже есть — план станет практичнее и дешевле."),
    Loading(9, "AI создает твой персональный план", "Мы анализируем твои ответы и подбираем лучшие рецепты специально для тебя."),
    ;

    companion object {
        val formSteps = entries.filter { it != Loading }
        const val TOTAL = 10
    }
}

/** Matches NutritionEngine DEFAULT_MAX_WEEKLY_WEIGHT_CHANGE_KG. */
const val MAX_SAFE_WEEKLY_CHANGE_KG = 1.0

@Serializable
data class OnboardingDraft(
    val goalType: String = "lose_weight",
    val targetWeightKg: String = "",
    val desiredWeeklyChangeKg: String = "0.4",
    val sex: String = "female",
    val ageYears: String = "",
    val heightCm: String = "",
    val currentWeightKg: String = "",
    val activityLevel: String = "moderate",
    val mealsPerDay: String = "3",
    val dailyCalorieMode: String = "auto",
    val dailyCalorieValue: String = "",
    val likedFoods: String = "",
    val dislikedFoods: String = "",
    val excludedFoods: String = "",
    val allergies: String = "",
    val groceryBudgetWeekly: String = "8000",
    val currency: String = "RUB",
    val householdSize: String = "1",
    val maxCookTimeMinutes: String = "20",
    val preferredStores: String = "",
    val considerDiscounts: Boolean = true,
    val pantryText: String = "",
    val stepIndex: Int = 0,
)

fun OnboardingDraft.hasMeaningfulInput(): Boolean =
    ageYears.isNotBlank() ||
        heightCm.isNotBlank() ||
        currentWeightKg.isNotBlank() ||
        targetWeightKg.isNotBlank() ||
        likedFoods.isNotBlank() ||
        pantryText.isNotBlank()

fun OnboardingDraft.splitCsv(value: String): List<String> =
    value.split(',', ';', '\n')
        .map { it.trim() }
        .filter { it.isNotEmpty() }

fun OnboardingDraft.toPreviewRequestOrNull(): TargetPreviewRequest? {
    val age = ageYears.toIntOrNull() ?: return null
    val height = heightCm.toDoubleOrNull() ?: return null
    val weight = currentWeightKg.toDoubleOrNull() ?: return null
    return TargetPreviewRequest(
        sex = sex,
        ageYears = age,
        heightCm = height,
        currentWeightKg = weight,
        activityLevel = activityLevel,
        goalType = goalType,
        targetWeightKg = targetWeightKg.toDoubleOrNull(),
        desiredWeeklyChangeKg = desiredWeeklyChangeKg.toDoubleOrNull(),
        dailyCalorieMode = dailyCalorieMode,
        dailyCalorieValue = dailyCalorieValue.toIntOrNull(),
    )
}

fun OnboardingDraft.toUpdateRequest(): ProfileUpdateRequest {
    val age = requireNotNull(ageYears.toIntOrNull()) { "age_years" }
    val height = requireNotNull(heightCm.toDoubleOrNull()) { "height_cm" }
    val weight = requireNotNull(currentWeightKg.toDoubleOrNull()) { "current_weight_kg" }
    val meals = requireNotNull(mealsPerDay.toIntOrNull()) { "meals_per_day" }
    return ProfileUpdateRequest(
        sex = sex,
        ageYears = age,
        heightCm = height,
        currentWeightKg = weight,
        activityLevel = activityLevel,
        goalType = goalType,
        mealsPerDay = meals,
        targetWeightKg = targetWeightKg.toDoubleOrNull(),
        desiredWeeklyChangeKg = when (goalType) {
            "maintain_weight" -> 0.0
            else -> desiredWeeklyChangeKg.toDoubleOrNull()
        },
        dailyCalorieMode = dailyCalorieMode,
        dailyCalorieValue = dailyCalorieValue.toIntOrNull(),
        groceryBudgetWeekly = groceryBudgetWeekly.toDoubleOrNull(),
        currency = currency.ifBlank { "RUB" },
        maxCookTimeMinutes = maxCookTimeMinutes.toIntOrNull(),
        householdSize = householdSize.toIntOrNull() ?: 1,
        likedFoods = splitCsv(likedFoods),
        dislikedFoods = splitCsv(dislikedFoods),
        excludedFoods = splitCsv(excludedFoods),
        allergies = splitCsv(allergies),
        availableProducts = parsePantry(pantryText),
    )
}

fun ProfileResponse.toOnboardingDraft(stepIndex: Int = 0): OnboardingDraft {
    val goalType = goal?.goalType ?: "lose_weight"
    val pantryLines = availableProducts.joinToString("\n") { item ->
        "${item.name} ${item.quantity} ${item.unit}"
    }
    return OnboardingDraft(
        goalType = goalType,
        targetWeightKg = goal?.targetWeightKg?.toString().orEmpty(),
        desiredWeeklyChangeKg = goal?.desiredWeeklyChangeKg?.toString()
            ?: if (goalType == "maintain_weight") "0" else "0.4",
        sex = profile.sex ?: "female",
        ageYears = profile.ageYears?.toString().orEmpty(),
        heightCm = profile.heightCm?.toString().orEmpty(),
        currentWeightKg = profile.currentWeightKg?.toString().orEmpty(),
        activityLevel = profile.activityLevel ?: "moderate",
        mealsPerDay = profile.mealsPerDay?.toString() ?: "3",
        dailyCalorieMode = profile.dailyCalorieMode ?: "auto",
        dailyCalorieValue = profile.dailyCalorieValue?.toString().orEmpty(),
        likedFoods = preferences.likedFoods.joinToString(", "),
        dislikedFoods = preferences.dislikedFoods.joinToString(", "),
        excludedFoods = restrictions.excludedFoods.joinToString(", "),
        allergies = restrictions.allergies.joinToString(", "),
        groceryBudgetWeekly = profile.groceryBudgetWeekly?.toString().orEmpty(),
        currency = profile.currency ?: "RUB",
        householdSize = profile.householdSize?.toString() ?: "1",
        maxCookTimeMinutes = profile.maxCookTimeMinutes?.toString() ?: "35",
        pantryText = pantryLines,
        stepIndex = stepIndex,
    )
}

fun normalizePantryUnit(raw: String): String {
    val key = raw.trim().lowercase()
    return when (key) {
        "шт", "штука", "штуки", "pcs", "pc" -> "piece"
        "г", "гр", "грамм", "грамма" -> "g"
        "кг", "килограмм" -> "kg"
        "мл", "миллилитр" -> "ml"
        "л", "литр" -> "l"
        "уп", "упаковка", "пачка" -> "pack"
        "ст.л", "стл", "ложк" -> "tbsp"
        "ч.л", "чл" -> "tsp"
        else -> key
    }
}

fun parsePantry(raw: String): List<PantryItemDto> =
    raw.lines()
        .map { it.trim() }
        .filter { it.isNotEmpty() }
        .map { line ->
            val parts = line.split(Regex("\\s+"))
            when {
                parts.size >= 3 && parts[parts.lastIndex - 1].toDoubleOrNull() != null -> {
                    val qty = parts[parts.lastIndex - 1].toDouble()
                    val unit = normalizePantryUnit(parts.last())
                    val name = parts.dropLast(2).joinToString(" ")
                    PantryItemDto(name = name, quantity = qty, unit = unit)
                }
                parts.size >= 2 && parts.last().toDoubleOrNull() != null -> {
                    val qty = parts.last().toDouble()
                    val name = parts.dropLast(1).joinToString(" ")
                    PantryItemDto(name = name, quantity = qty, unit = "piece")
                }
                else -> PantryItemDto(name = line, quantity = 1.0, unit = "piece")
            }
        }

fun OnboardingDraft.validateStep(step: OnboardingStep): String? = when (step) {
    OnboardingStep.Goal -> {
        when {
            goalType.isBlank() -> "Выберите цель"
            else -> null
        }
    }
    OnboardingStep.AboutYou -> when {
        ageYears.toIntOrNull() == null -> "Укажите возраст"
        heightCm.toDoubleOrNull() == null -> "Укажите рост"
        currentWeightKg.toDoubleOrNull() == null -> "Укажите текущий вес"
        else -> null
    }
    OnboardingStep.GoalDetails -> {
        when {
            goalType == "maintain_weight" -> null
            desiredWeeklyChangeKg.toDoubleOrNull() == null ->
                "Укажите скорость изменения веса (до $MAX_SAFE_WEEKLY_CHANGE_KG кг/нед)"
            desiredWeeklyChangeKg.toDouble() > MAX_SAFE_WEEKLY_CHANGE_KG ->
                "Безопасный максимум — $MAX_SAFE_WEEKLY_CHANGE_KG кг в неделю"
            desiredWeeklyChangeKg.toDouble() < 0 -> "Скорость не может быть отрицательной"
            else -> null
        }
    }
    OnboardingStep.Activity -> when {
        activityLevel.isBlank() -> "Выберите уровень активности"
        else -> null
    }
    OnboardingStep.Budget -> null
    OnboardingStep.CookTime -> when {
        maxCookTimeMinutes.toIntOrNull() == null -> "Выберите время готовки"
        else -> null
    }
    OnboardingStep.Meals -> when {
        mealsPerDay.toIntOrNull() == null -> "Укажите число приёмов пищи"
        dailyCalorieMode != "auto" && dailyCalorieValue.toIntOrNull() == null ->
            "Укажите значение калорийности"
        else -> null
    }
    OnboardingStep.Foods, OnboardingStep.Pantry -> null
    OnboardingStep.Loading -> null
}

fun humanizeNutritionError(field: String?, reason: String?): String? = when {
    field == "desired_weekly_change_kg" && reason == "exceeds_safe_weekly_change" ->
        "Слишком быстрое изменение веса. Максимум $MAX_SAFE_WEEKLY_CHANGE_KG кг в неделю."
    field == "desired_weekly_change_kg" && reason == "required" ->
        "Укажите желаемую скорость изменения веса"
    field == "desired_weekly_change_kg" && reason == "must_be_zero_for_maintain_weight" ->
        "При сохранении веса скорость должна быть 0"
    field == "target_weight_kg" && reason == "must_be_below_current_weight" ->
        "Целевой вес должен быть меньше текущего"
    field == "target_weight_kg" && reason == "must_be_above_current_weight" ->
        "Целевой вес должен быть больше текущего"
    field == "target_weight_kg" && reason == "below_safe_bmi" ->
        "Целевой вес слишком низкий для безопасного ИМТ"
    field?.startsWith("available_products") == true && reason == "missing" ->
        "Укажите продукт в формате: яйца 10 piece (или просто «яйца»)"
    else -> null
}
