package com.foodai.app.feature.onboarding

import kotlinx.serialization.Serializable
import com.foodai.app.core.network.PantryItemDto
import com.foodai.app.core.network.ProfileUpdateRequest
import com.foodai.app.core.network.TargetPreviewRequest

enum class OnboardingStep(val index: Int, val title: String) {
    Goal(0, "Твоя цель"),
    AboutYou(1, "Расскажи о себе"),
    Eating(2, "Как ты питаешься?"),
    Foods(3, "Что ты любишь?"),
    Budget(4, "Какой бюджет?"),
    CookTime(5, "Сколько времени готовишь?"),
    Pantry(6, "Что есть дома?"),
    Loading(7, "Создаём твой первый план..."),
    ;

    companion object {
        val formSteps = entries.filter { it != Loading }
    }
}

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
    val groceryBudgetWeekly: String = "",
    val currency: String = "RUB",
    val householdSize: String = "1",
    val maxCookTimeMinutes: String = "35",
    val pantryText: String = "",
    val stepIndex: Int = 0,
)

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
        desiredWeeklyChangeKg = desiredWeeklyChangeKg.toDoubleOrNull(),
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

fun parsePantry(raw: String): List<PantryItemDto> =
    raw.lines()
        .map { it.trim() }
        .filter { it.isNotEmpty() }
        .mapNotNull { line ->
            val parts = line.split(Regex("\\s+"))
            when {
                parts.size >= 3 && parts[1].toDoubleOrNull() != null ->
                    PantryItemDto(name = parts[0], quantity = parts[1].toDouble(), unit = parts[2])
                parts.size == 2 && parts[1].toDoubleOrNull() != null ->
                    PantryItemDto(name = parts[0], quantity = parts[1].toDouble(), unit = "piece")
                else -> PantryItemDto(name = line, quantity = 1.0, unit = "piece")
            }
        }

fun OnboardingDraft.validateStep(step: OnboardingStep): String? = when (step) {
    OnboardingStep.Goal -> when {
        goalType.isBlank() -> "Выберите цель"
        goalType != "maintain_weight" &&
            desiredWeeklyChangeKg.toDoubleOrNull() == null -> "Укажите скорость изменения веса"
        else -> null
    }
    OnboardingStep.AboutYou -> when {
        ageYears.toIntOrNull() == null -> "Укажите возраст"
        heightCm.toDoubleOrNull() == null -> "Укажите рост"
        currentWeightKg.toDoubleOrNull() == null -> "Укажите текущий вес"
        else -> null
    }
    OnboardingStep.Eating -> when {
        mealsPerDay.toIntOrNull() == null -> "Укажите число приёмов пищи"
        dailyCalorieMode != "auto" && dailyCalorieValue.toIntOrNull() == null ->
            "Укажите значение калорийности"
        else -> null
    }
    OnboardingStep.Foods, OnboardingStep.Budget, OnboardingStep.CookTime, OnboardingStep.Pantry -> null
    OnboardingStep.Loading -> null
}
