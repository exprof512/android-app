package com.foodai.app.core.network

import kotlinx.serialization.EncodeDefault
import kotlinx.serialization.ExperimentalSerializationApi
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class ApiErrorEnvelope(
    val error: ApiErrorBody? = null,
)

@Serializable
data class ApiErrorBody(
    val code: String? = null,
    val message: String? = null,
    val detail: String? = null,
    val details: List<ApiErrorDetail> = emptyList(),
    @SerialName("request_id") val requestId: String? = null,
)

@Serializable
data class ApiErrorDetail(
    val field: String? = null,
    val reason: String? = null,
)

sealed class ApiException(
    message: String,
    val code: String? = null,
    val httpStatus: Int? = null,
    val details: List<ApiErrorDetail> = emptyList(),
) : Exception(message) {
    class Unauthorized(
        message: String = "Требуется вход",
        code: String? = "invalid_token",
    ) : ApiException(message, code, 401)

    class Forbidden(
        message: String,
        code: String? = null,
    ) : ApiException(message, code, 403)

    class Conflict(
        message: String,
        code: String? = null,
    ) : ApiException(message, code, 409)

    class Validation(
        message: String,
        code: String? = "validation_error",
        details: List<ApiErrorDetail> = emptyList(),
    ) : ApiException(message, code, 422, details)

    class Network(
        message: String = "Нет соединения с сервером",
    ) : ApiException(message)

    class Unexpected(
        message: String,
        httpStatus: Int? = null,
        code: String? = null,
    ) : ApiException(message, code, httpStatus)
}

@Serializable
data class TokenPairResponse(
    @SerialName("access_token") val accessToken: String,
    @SerialName("refresh_token") val refreshToken: String,
    @SerialName("token_type") val tokenType: String = "bearer",
    @SerialName("expires_in") val expiresIn: Int,
    val user: UserSummaryDto,
)

@Serializable
data class UserSummaryDto(
    val id: String,
    val email: String,
    val tier: String = "free",
)

@Serializable
data class LoginRequest(
    val email: String,
    val password: String,
)

@Serializable
data class RegisterRequest(
    val email: String,
    val password: String,
    val locale: String = "ru-RU",
    @SerialName("accepted_terms_at") val acceptedTermsAt: String? = null,
)

@Serializable
data class RefreshRequest(
    @SerialName("refresh_token") val refreshToken: String,
)

@Serializable
data class LogoutRequest(
    @SerialName("refresh_token") val refreshToken: String,
)

@OptIn(ExperimentalSerializationApi::class)
@Serializable
data class PantryItemDto(
    val name: String,
    val quantity: Double,
    // Must encode always: kotlinx omits Kotlin defaults when encodeDefaults=false.
    @EncodeDefault
    val unit: String = "piece",
    @SerialName("expires_on") val expiresOn: String? = null,
)

@Serializable
data class ProfileUpdateRequest(
    val sex: String,
    @SerialName("age_years") val ageYears: Int,
    @SerialName("height_cm") val heightCm: Double,
    @SerialName("current_weight_kg") val currentWeightKg: Double,
    @SerialName("activity_level") val activityLevel: String,
    @SerialName("goal_type") val goalType: String,
    @SerialName("meals_per_day") val mealsPerDay: Int,
    @SerialName("target_weight_kg") val targetWeightKg: Double? = null,
    @SerialName("desired_weekly_change_kg") val desiredWeeklyChangeKg: Double? = null,
    @SerialName("daily_calorie_mode") val dailyCalorieMode: String = "auto",
    @SerialName("daily_calorie_value") val dailyCalorieValue: Int? = null,
    @SerialName("grocery_budget_weekly") val groceryBudgetWeekly: Double? = null,
    val currency: String = "RUB",
    @SerialName("max_cook_time_minutes") val maxCookTimeMinutes: Int? = null,
    @SerialName("household_size") val householdSize: Int = 1,
    val timezone: String? = "Europe/Moscow",
    @SerialName("liked_foods") val likedFoods: List<String> = emptyList(),
    @SerialName("disliked_foods") val dislikedFoods: List<String> = emptyList(),
    @SerialName("excluded_foods") val excludedFoods: List<String> = emptyList(),
    val allergies: List<String> = emptyList(),
    @SerialName("available_products") val availableProducts: List<PantryItemDto> = emptyList(),
)

@Serializable
data class TargetPreviewRequest(
    val sex: String,
    @SerialName("age_years") val ageYears: Int,
    @SerialName("height_cm") val heightCm: Double,
    @SerialName("current_weight_kg") val currentWeightKg: Double,
    @SerialName("activity_level") val activityLevel: String,
    @SerialName("goal_type") val goalType: String,
    @SerialName("target_weight_kg") val targetWeightKg: Double? = null,
    @SerialName("desired_weekly_change_kg") val desiredWeeklyChangeKg: Double? = null,
    @SerialName("daily_calorie_mode") val dailyCalorieMode: String = "auto",
    @SerialName("daily_calorie_value") val dailyCalorieValue: Int? = null,
)

@Serializable
data class MacroTargetsDto(
    val protein: Int,
    val fat: Int,
    val carbohydrate: Int,
)

@Serializable
data class TargetPreviewResponse(
    @SerialName("bmr_kcal") val bmrKcal: Int,
    @SerialName("tdee_kcal") val tdeeKcal: Int,
    @SerialName("recommended_calorie_target_kcal") val recommendedCalorieTargetKcal: Int,
    @SerialName("applied_safety_floor_kcal") val appliedSafetyFloorKcal: Int,
    @SerialName("macro_targets_g") val macroTargetsG: MacroTargetsDto,
    val warnings: List<String> = emptyList(),
)

@Serializable
data class ProfileFieldsDto(
    val sex: String? = null,
    @SerialName("age_years") val ageYears: Int? = null,
    @SerialName("height_cm") val heightCm: Double? = null,
    @SerialName("current_weight_kg") val currentWeightKg: Double? = null,
    @SerialName("activity_level") val activityLevel: String? = null,
    @SerialName("meals_per_day") val mealsPerDay: Int? = null,
    @SerialName("daily_calorie_mode") val dailyCalorieMode: String? = null,
    @SerialName("daily_calorie_value") val dailyCalorieValue: Int? = null,
    @SerialName("grocery_budget_weekly") val groceryBudgetWeekly: Double? = null,
    val currency: String? = null,
    @SerialName("max_cook_time_minutes") val maxCookTimeMinutes: Int? = null,
    @SerialName("household_size") val householdSize: Int? = null,
    val timezone: String? = null,
)

@Serializable
data class GoalViewDto(
    val id: String,
    @SerialName("goal_type") val goalType: String,
    val status: String,
    @SerialName("start_weight_kg") val startWeightKg: Double? = null,
    @SerialName("target_weight_kg") val targetWeightKg: Double? = null,
    @SerialName("desired_weekly_change_kg") val desiredWeeklyChangeKg: Double? = null,
    @SerialName("calorie_target_kcal") val calorieTargetKcal: Int,
    @SerialName("macro_targets_g") val macroTargetsG: MacroTargetsDto,
    @SerialName("bmr_kcal") val bmrKcal: Int,
    @SerialName("tdee_kcal") val tdeeKcal: Int,
    @SerialName("safety_floor_kcal") val safetyFloorKcal: Int,
    @SerialName("started_at") val startedAt: String? = null,
)

@Serializable
data class PreferencesDto(
    @SerialName("liked_foods") val likedFoods: List<String> = emptyList(),
    @SerialName("disliked_foods") val dislikedFoods: List<String> = emptyList(),
)

@Serializable
data class RestrictionsDto(
    @SerialName("excluded_foods") val excludedFoods: List<String> = emptyList(),
    val allergies: List<String> = emptyList(),
)

@Serializable
data class ProfileResponse(
    val profile: ProfileFieldsDto,
    val goal: GoalViewDto? = null,
    val preferences: PreferencesDto = PreferencesDto(),
    val restrictions: RestrictionsDto = RestrictionsDto(),
    @SerialName("available_products") val availableProducts: List<PantryItemDto> = emptyList(),
    val warnings: List<String> = emptyList(),
)

fun ProfileResponse.isComplete(): Boolean =
    profile.sex != null &&
        profile.ageYears != null &&
        profile.heightCm != null &&
        profile.currentWeightKg != null &&
        profile.activityLevel != null &&
        profile.mealsPerDay != null &&
        goal != null

@Serializable
data class MealPlanGenerateRequest(
    @SerialName("start_date") val startDate: String,
    val days: Int = 7,
    val notes: String? = null,
)

@Serializable
data class RecipeImageDto(
    val id: String? = null,
    @SerialName("recipe_id") val recipeId: String? = null,
    val status: String = "pending",
    val url: String? = null,
    @SerialName("thumbnail_url") val thumbnailUrl: String? = null,
    @SerialName("retry_allowed") val retryAllowed: Boolean = false,
)

@Serializable
data class DailyTargetsDto(
    @SerialName("calories_kcal") val caloriesKcal: Int,
    @SerialName("protein_g") val proteinG: Double,
    @SerialName("fat_g") val fatG: Double,
    @SerialName("carbohydrate_g") val carbohydrateG: Double,
)

@Serializable
data class MealPlanRecipeSummaryDto(
    val id: String,
    val name: String,
    @SerialName("calories_kcal") val caloriesKcal: Int,
    @SerialName("cook_time_minutes") val cookTimeMinutes: Int = 0,
    val image: RecipeImageDto = RecipeImageDto(),
)

@Serializable
data class MealPlanItemDto(
    val id: String,
    val date: String,
    @SerialName("meal_type") val mealType: String,
    val servings: Double = 1.0,
    @SerialName("sort_order") val sortOrder: Int = 0,
    val status: String = "planned",
    @SerialName("is_completed") val isCompleted: Boolean = false,
    val nutrition: DailyTargetsDto? = null,
    @SerialName("estimated_cost_amount") val estimatedCostAmount: Double? = null,
    val recipe: MealPlanRecipeSummaryDto,
)

@Serializable
data class MealPlanDto(
    val id: String,
    @SerialName("start_date") val startDate: String,
    @SerialName("end_date") val endDate: String,
    val status: String,
    @SerialName("daily_targets") val dailyTargets: DailyTargetsDto,
    val items: List<MealPlanItemDto> = emptyList(),
    val warnings: List<String> = emptyList(),
    val reused: Boolean = false,
)

/** @deprecated alias kept for generateFirstPlan return type clarity */
typealias MealPlanSummaryResponse = MealPlanDto

@Serializable
data class DishCardNutritionDto(
    @SerialName("calories_kcal") val caloriesKcal: Int,
    @SerialName("protein_g") val proteinG: Double,
    @SerialName("fat_g") val fatG: Double,
    @SerialName("carbohydrate_g") val carbohydrateG: Double,
)

@Serializable
data class DishCardCostDto(
    val amount: Double,
    val currency: String,
)

@Serializable
data class DishCardIngredientDto(
    val name: String,
    val grams: Double,
    val quantity: Double,
    val unit: String,
    val cost: Double? = null,
)

@Serializable
data class DishCardDto(
    val id: String,
    val name: String,
    val description: String? = null,
    @SerialName("cooking_method") val cookingMethod: String,
    @SerialName("cook_time_minutes") val cookTimeMinutes: Int,
    val servings: Int,
    val status: String,
    @SerialName("nutrition_per_serving") val nutritionPerServing: DishCardNutritionDto,
    @SerialName("estimated_cost_per_serving") val estimatedCostPerServing: DishCardCostDto,
    val ingredients: List<DishCardIngredientDto> = emptyList(),
    val steps: List<String> = emptyList(),
    @SerialName("is_favorite") val isFavorite: Boolean = false,
)
