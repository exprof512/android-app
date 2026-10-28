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

    class RateLimited(
        message: String,
        code: String? = "usage_limit_exceeded",
    ) : ApiException(message, code, 429)

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
data class ConsentDto(
    @SerialName("terms_version") val termsVersion: String? = null,
    @SerialName("privacy_version") val privacyVersion: String? = null,
    @SerialName("accepted_terms_at") val acceptedTermsAt: String? = null,
    @SerialName("terms_url") val termsUrl: String? = null,
    @SerialName("privacy_url") val privacyUrl: String? = null,
)

@Serializable
data class CurrentUserDto(
    val id: String,
    val email: String,
    val tier: String = "free",
    val locale: String = "ru-RU",
    @SerialName("is_active") val isActive: Boolean = true,
    val role: String = "user",
    @SerialName("email_verified") val emailVerified: Boolean = false,
    @SerialName("email_verified_at") val emailVerifiedAt: String? = null,
    @SerialName("accepted_terms_at") val acceptedTermsAt: String? = null,
    @SerialName("terms_version") val termsVersion: String? = null,
    @SerialName("privacy_version") val privacyVersion: String? = null,
    val consent: ConsentDto? = null,
    @SerialName("created_at") val createdAt: String? = null,
)

@Serializable
data class GenericMessageDto(val message: String)

@Serializable
data class EmailOnlyRequest(val email: String)

@Serializable
data class TokenMessageRequest(val token: String)

@Serializable
data class ResetPasswordRequest(
    val token: String,
    @SerialName("new_password") val newPassword: String,
)

@Serializable
data class DeleteAccountRequest(val confirmation: String = "DELETE")

@Serializable
data class SessionDto(
    val id: String,
    @SerialName("created_at") val createdAt: String,
    @SerialName("last_used_at") val lastUsedAt: String? = null,
    @SerialName("expires_at") val expiresAt: String,
    @SerialName("device_label") val deviceLabel: String? = null,
    val platform: String? = null,
    @SerialName("app_version") val appVersion: String? = null,
    @SerialName("is_current") val isCurrent: Boolean = false,
)

@Serializable
data class AnalyticsEventDto(
    @SerialName("event_name") val eventName: String,
    @SerialName("event_version") val eventVersion: Int = 1,
    val platform: String? = "android",
    @SerialName("app_version") val appVersion: String? = null,
    val properties: Map<String, String> = emptyMap(),
)

@Serializable
data class AnalyticsBatchRequest(val events: List<AnalyticsEventDto>)

@Serializable
data class AnalyticsAcceptedDto(val accepted: Int)

@Serializable
data class NutritionLogDto(
    val id: String,
    @SerialName("logged_on") val loggedOn: String,
    @SerialName("meal_type") val mealType: String,
    val description: String,
    @SerialName("calories_kcal") val caloriesKcal: Int,
    @SerialName("protein_g") val proteinG: Double,
    @SerialName("fat_g") val fatG: Double,
    @SerialName("carbohydrate_g") val carbohydrateG: Double,
    val servings: Double = 1.0,
    val source: String,
    @SerialName("recipe_id") val recipeId: String? = null,
    @SerialName("meal_plan_item_id") val mealPlanItemId: String? = null,
    @SerialName("ingredient_id") val ingredientId: String? = null,
    @SerialName("quantity_g") val quantityG: Double? = null,
    val unit: String? = null,
    val notes: String? = null,
)

@Serializable
data class NutritionLogCreateRequest(
    @SerialName("logged_on") val loggedOn: String,
    @SerialName("meal_type") val mealType: String,
    val source: String,
    val description: String? = null,
    @SerialName("calories_kcal") val caloriesKcal: Int? = null,
    @SerialName("protein_g") val proteinG: Double? = null,
    @SerialName("fat_g") val fatG: Double? = null,
    @SerialName("carbohydrate_g") val carbohydrateG: Double? = null,
    val servings: Double = 1.0,
    @SerialName("recipe_id") val recipeId: String? = null,
    @SerialName("meal_plan_item_id") val mealPlanItemId: String? = null,
    @SerialName("ingredient_id") val ingredientId: String? = null,
    @SerialName("quantity_g") val quantityG: Double? = null,
    val unit: String? = null,
    val notes: String? = null,
)

@Serializable
data class NutritionLogUpdateRequest(
    val description: String? = null,
    @SerialName("meal_type") val mealType: String? = null,
    @SerialName("calories_kcal") val caloriesKcal: Int? = null,
    @SerialName("protein_g") val proteinG: Double? = null,
    @SerialName("fat_g") val fatG: Double? = null,
    @SerialName("carbohydrate_g") val carbohydrateG: Double? = null,
    val servings: Double? = null,
    @SerialName("quantity_g") val quantityG: Double? = null,
    @SerialName("ingredient_id") val ingredientId: String? = null,
    val notes: String? = null,
)

@Serializable
data class DiaryDayDto(
    val date: String,
    val totals: DiaryTotalsDto,
    val meals: Map<String, List<DiaryMealEntryDto>> = emptyMap(),
)

@Serializable
data class DiaryTotalsDto(
    @SerialName("calories_kcal") val caloriesKcal: Int = 0,
    @SerialName("protein_g") val proteinG: Double = 0.0,
    @SerialName("fat_g") val fatG: Double = 0.0,
    @SerialName("carbohydrate_g") val carbohydrateG: Double = 0.0,
    val entries: Int = 0,
)

@Serializable
data class DiaryMealEntryDto(
    val id: String,
    val description: String,
    @SerialName("calories_kcal") val caloriesKcal: Int,
    @SerialName("protein_g") val proteinG: Double = 0.0,
    @SerialName("fat_g") val fatG: Double = 0.0,
    @SerialName("carbohydrate_g") val carbohydrateG: Double = 0.0,
    @SerialName("quantity_g") val quantityG: Double? = null,
    val source: String,
    @SerialName("created_at") val createdAt: String? = null,
)

@Serializable
data class DiaryHistoryDayDto(
    val date: String,
    @SerialName("calories_kcal") val caloriesKcal: Int,
    @SerialName("protein_g") val proteinG: Double = 0.0,
    @SerialName("fat_g") val fatG: Double = 0.0,
    @SerialName("carbohydrate_g") val carbohydrateG: Double = 0.0,
    val entries: Int = 0,
)

@Serializable
data class FoodSearchHitDto(
    @SerialName("ingredient_id") val ingredientId: String,
    val name: String,
    @SerialName("calories_per_100g") val caloriesPer100g: Double,
    @SerialName("protein_per_100g") val proteinPer100g: Double,
    @SerialName("fat_per_100g") val fatPer100g: Double,
    @SerialName("carbohydrate_per_100g") val carbohydratePer100g: Double,
)

@Serializable
data class RecentFoodDto(
    val description: String,
    @SerialName("ingredient_id") val ingredientId: String? = null,
    @SerialName("quantity_g") val quantityG: Double? = null,
    @SerialName("calories_kcal") val caloriesKcal: Int = 0,
    @SerialName("protein_g") val proteinG: Double = 0.0,
    @SerialName("fat_g") val fatG: Double = 0.0,
    @SerialName("carbohydrate_g") val carbohydrateG: Double = 0.0,
    val source: String = "manual",
)

@Serializable
data class FoodCalculateRequest(
    @SerialName("ingredient_id") val ingredientId: String,
    @SerialName("quantity_g") val quantityG: Double,
)

@Serializable
data class FoodCalculateDto(
    @SerialName("ingredient_id") val ingredientId: String,
    val name: String,
    @SerialName("quantity_g") val quantityG: Double,
    @SerialName("calories_kcal") val caloriesKcal: Int,
    @SerialName("protein_g") val proteinG: Double,
    @SerialName("fat_g") val fatG: Double,
    @SerialName("carbohydrate_g") val carbohydrateG: Double,
)

@Serializable
data class PhotoAnalyzeDto(
    val items: List<PhotoItemDto> = emptyList(),
    @SerialName("overall_confidence") val overallConfidence: Double = 0.0,
    @SerialName("estimated_total_kcal") val estimatedTotalKcal: Int? = null,
    val warnings: List<String> = emptyList(),
    val model: String? = null,
    @SerialName("needs_manual_review") val needsManualReview: Boolean = false,
)

@Serializable
data class PhotoItemDto(
    val name: String,
    @SerialName("estimated_grams") val estimatedGrams: Double? = null,
    val confidence: Double = 0.0,
    val matched: Boolean = false,
    @SerialName("ingredient_id") val ingredientId: String? = null,
    @SerialName("canonical_name") val canonicalName: String? = null,
    @SerialName("calories_kcal") val caloriesKcal: Int? = null,
    @SerialName("protein_g") val proteinG: Double? = null,
    @SerialName("fat_g") val fatG: Double? = null,
    @SerialName("carbohydrate_g") val carbohydrateG: Double? = null,
    @SerialName("low_confidence") val lowConfidence: Boolean = false,
    val notes: String? = null,
)

@Serializable
data class PhotoConfirmRequest(
    @SerialName("logged_on") val loggedOn: String,
    @SerialName("meal_type") val mealType: String = "snack",
    val items: List<PhotoConfirmItemDto>,
)

@Serializable
data class PhotoConfirmItemDto(
    @SerialName("ingredient_id") val ingredientId: String? = null,
    val description: String,
    @SerialName("quantity_g") val quantityG: Double,
    @SerialName("meal_type") val mealType: String = "snack",
    val notes: String? = null,
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
    val force: Boolean = false,
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
data class MacroProgressDto(
    @SerialName("consumed_g") val consumedG: Double = 0.0,
    @SerialName("target_g") val targetG: Double = 0.0,
    @SerialName("remaining_g") val remainingG: Double = 0.0,
)

@Serializable
data class DayProgressDto(
    @SerialName("consumed_kcal") val consumedKcal: Int = 0,
    @SerialName("target_kcal") val targetKcal: Int = 0,
    @SerialName("remaining_kcal") val remainingKcal: Int = 0,
    @SerialName("over_target_kcal") val overTargetKcal: Int = 0,
    @SerialName("planned_remaining_kcal") val plannedRemainingKcal: Int = 0,
    @SerialName("from_plan_kcal") val fromPlanKcal: Int = 0,
    @SerialName("from_diary_kcal") val fromDiaryKcal: Int = 0,
    val protein: MacroProgressDto = MacroProgressDto(),
    val fat: MacroProgressDto = MacroProgressDto(),
    val carbs: MacroProgressDto = MacroProgressDto(),
    @SerialName("completed_meals") val completedMeals: Int = 0,
    @SerialName("planned_meals") val plannedMeals: Int = 0,
    @SerialName("skipped_meals") val skippedMeals: Int = 0,
    @SerialName("next_meal_item_id") val nextMealItemId: String? = null,
    @SerialName("next_meal_type") val nextMealType: String? = null,
    val suggestions: List<String> = emptyList(),
    @SerialName("daily_estimated_cost_amount") val dailyEstimatedCostAmount: Double? = null,
)

@Serializable
data class WeekDayDto(
    val date: String,
    val status: String = "missing",
    @SerialName("calories_kcal") val caloriesKcal: Int = 0,
    @SerialName("protein_g") val proteinG: Double = 0.0,
    @SerialName("completed_meals") val completedMeals: Int = 0,
    @SerialName("planned_meals") val plannedMeals: Int = 0,
    @SerialName("estimated_cost_amount") val estimatedCostAmount: Double? = null,
)

@Serializable
data class WeekSummaryDto(
    val days: List<WeekDayDto> = emptyList(),
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
    @SerialName("day_progress") val dayProgress: DayProgressDto? = null,
    @SerialName("week_summary") val weekSummary: WeekSummaryDto? = null,
)

@Serializable
data class MealPlanReplaceRequest(
    @SerialName("replace_reason") val replaceReason: String = "user_requested",
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

@Serializable
data class ShoppingGenerateRequest(
    @SerialName("meal_plan_id") val mealPlanId: String,
    @SerialName("from_date") val fromDate: String? = null,
    @SerialName("to_date") val toDate: String? = null,
    @SerialName("exclude_available_products") val excludeAvailableProducts: Boolean = true,
)

@Serializable
data class ShoppingListItemDto(
    val id: String,
    @SerialName("display_name") val displayName: String,
    @SerialName("quantity_value") val quantityValue: Double,
    val unit: String,
    @SerialName("is_completed") val isCompleted: Boolean = false,
    @SerialName("source_recipe_count") val sourceRecipeCount: Int = 1,
    @SerialName("ingredient_id") val ingredientId: String? = null,
    val category: String = "other",
    @SerialName("estimated_cost_amount") val estimatedCostAmount: Double? = null,
)

@Serializable
data class ShoppingListDto(
    val id: String,
    @SerialName("meal_plan_id") val mealPlanId: String,
    @SerialName("from_date") val fromDate: String,
    @SerialName("to_date") val toDate: String,
    val status: String,
    val items: List<ShoppingListItemDto> = emptyList(),
    val warnings: List<String> = emptyList(),
    @SerialName("estimated_total_amount") val estimatedTotalAmount: Double? = null,
    val currency: String = "RUB",
    val stale: Boolean = false,
    @SerialName("plan_fingerprint") val planFingerprint: String? = null,
)

@Serializable
data class WeightEntryCreateRequest(
    @SerialName("measured_at") val measuredAt: String,
    @SerialName("weight_kg") val weightKg: Double,
    val note: String? = null,
)

@Serializable
data class WeightEntryDto(
    val id: String,
    @SerialName("measured_at") val measuredAt: String,
    @SerialName("weight_kg") val weightKg: Double,
    val note: String? = null,
)

@Serializable
data class DailyNutritionBalanceDto(
    val date: String,
    @SerialName("target_calories_kcal") val targetCaloriesKcal: Int? = null,
    @SerialName("consumed_calories_kcal") val consumedCaloriesKcal: Int = 0,
    @SerialName("planned_calories_kcal") val plannedCaloriesKcal: Int = 0,
    @SerialName("protein_g") val proteinG: Double = 0.0,
    @SerialName("fat_g") val fatG: Double = 0.0,
    @SerialName("carbohydrate_g") val carbohydrateG: Double = 0.0,
    @SerialName("completed_meals") val completedMeals: Int = 0,
    @SerialName("planned_meals") val plannedMeals: Int = 0,
)

@Serializable
data class ProgressSeriesPointDto(
    val date: String,
    @SerialName("consumed_kcal") val consumedKcal: Int = 0,
    @SerialName("protein_g") val proteinG: Double = 0.0,
    @SerialName("completed_meals") val completedMeals: Int = 0,
    @SerialName("weight_kg") val weightKg: Double? = null,
)

@Serializable
data class ProgressSummaryDto(
    @SerialName("current_weight_kg") val currentWeightKg: Double? = null,
    @SerialName("start_weight_kg") val startWeightKg: Double? = null,
    @SerialName("target_weight_kg") val targetWeightKg: Double? = null,
    @SerialName("goal_type") val goalType: String? = null,
    @SerialName("weight_delta_kg") val weightDeltaKg: Double? = null,
    @SerialName("progress_percent") val progressPercent: Double? = null,
    @SerialName("trend_7d_kg") val trend7dKg: Double? = null,
    @SerialName("calorie_target_kcal") val calorieTargetKcal: Int? = null,
    val today: DailyNutritionBalanceDto? = null,
    @SerialName("recent_entries") val recentEntries: List<WeightEntryDto> = emptyList(),
    val series: List<ProgressSeriesPointDto> = emptyList(),
    @SerialName("period_days") val periodDays: Int? = null,
    val disclaimer: String = "",
    val warnings: List<String> = emptyList(),
)

@Serializable
data class StreakDto(
    @SerialName("current_days") val currentDays: Int = 0,
    @SerialName("best_days") val bestDays: Int = 0,
    @SerialName("last_active_date") val lastActiveDate: String? = null,
)

@Serializable
data class WaterEntryCreateRequest(
    @SerialName("amount_ml") val amountMl: Int,
    @SerialName("recorded_on") val recordedOn: String? = null,
)

@Serializable
data class WaterEntryDto(
    val id: String,
    @SerialName("recorded_on") val recordedOn: String,
    @SerialName("amount_ml") val amountMl: Int,
    @SerialName("created_at") val createdAt: String? = null,
)

@Serializable
data class WaterTodayDto(
    val date: String,
    @SerialName("total_ml") val totalMl: Int = 0,
    @SerialName("goal_ml") val goalMl: Int = 2000,
    val entries: List<WaterEntryDto> = emptyList(),
)

@Serializable
data class ConversationCreateRequest(
    val title: String? = null,
    @SerialName("context_plan_id") val contextPlanId: String? = null,
    @SerialName("context_recipe_id") val contextRecipeId: String? = null,
)

@Serializable
data class ChatMessageCreateRequest(
    val content: String,
)

@Serializable
data class SuggestedActionDto(
    val type: String,
    val label: String,
    val payload: kotlinx.serialization.json.JsonElement? = null,
)

@Serializable
data class ChatMessageDto(
    val id: String,
    val role: String,
    val content: String,
    @SerialName("suggested_actions") val suggestedActions: List<SuggestedActionDto> = emptyList(),
    @SerialName("created_at") val createdAt: String? = null,
)

@Serializable
data class ConversationDto(
    val id: String,
    val title: String? = null,
    val status: String = "active",
    @SerialName("context_plan_id") val contextPlanId: String? = null,
    @SerialName("context_recipe_id") val contextRecipeId: String? = null,
    val messages: List<ChatMessageDto> = emptyList(),
    val warnings: List<String> = emptyList(),
    val disclaimer: String = "",
)

@Serializable
data class ChatMessageResponseDto(
    @SerialName("conversation_id") val conversationId: String,
    @SerialName("user_message") val userMessage: ChatMessageDto,
    @SerialName("assistant_message") val assistantMessage: ChatMessageDto,
    val warnings: List<String> = emptyList(),
    val disclaimer: String = "",
)

// --- Phase 20 Adaptive AI ---

@Serializable
data class AiRecommendRequest(
    val intent: String? = null,
    @SerialName("meal_type") val mealType: String? = null,
    val date: String? = null,
)

@Serializable
data class AiAdaptDayRequest(
    val date: String? = null,
)

@Serializable
data class AiSubstitutionRequest(
    @SerialName("recipe_id") val recipeId: String,
    @SerialName("ingredient_name") val ingredientName: String,
)

@Serializable
data class AiVariantRequest(
    @SerialName("recipe_id") val recipeId: String,
    val variant: String,
)

@Serializable
data class AiApplyRequest(
    @SerialName("action_type") val actionType: String,
    val payload: Map<String, kotlinx.serialization.json.JsonElement> = emptyMap(),
)

@Serializable
data class AiExecuteRequest(
    @SerialName("action_type") val actionType: String,
    val payload: Map<String, kotlinx.serialization.json.JsonElement> = emptyMap(),
    @SerialName("recommendation_id") val recommendationId: String? = null,
)

@Serializable
data class RecommendationCandidateDto(
    val name: String,
    val reason: String? = null,
    val tags: List<String> = emptyList(),
    @SerialName("cook_time_minutes") val cookTimeMinutes: Int = 0,
    val servings: Int = 1,
    @SerialName("calories_kcal") val caloriesKcal: Int = 0,
    @SerialName("protein_g") val proteinG: Double = 0.0,
    @SerialName("fat_g") val fatG: Double = 0.0,
    @SerialName("carbohydrate_g") val carbohydrateG: Double = 0.0,
    @SerialName("estimated_cost_amount") val estimatedCostAmount: Double? = null,
    val currency: String = "RUB",
    @SerialName("recipe_id") val recipeId: String? = null,
    val warnings: List<String> = emptyList(),
)

@Serializable
data class RecommendationsDto(
    @SerialName("recommendation_id") val recommendationId: String,
    val operation: String = "food_suggestion",
    val candidates: List<RecommendationCandidateDto> = emptyList(),
    val warnings: List<String> = emptyList(),
    @SerialName("rejected_error_codes") val rejectedErrorCodes: List<String> = emptyList(),
)

@Serializable
data class AdaptDayReplacementDto(
    @SerialName("meal_type") val mealType: String,
    val reason: String? = null,
    val candidate: RecommendationCandidateDto? = null,
)

@Serializable
data class AdaptDayDto(
    @SerialName("recommendation_id") val recommendationId: String,
    @SerialName("on_date") val onDate: String,
    val replacements: List<AdaptDayReplacementDto> = emptyList(),
    val warnings: List<String> = emptyList(),
    val rationale: String? = null,
    val note: String? = null,
)

@Serializable
data class SubstitutionAlternativeDto(
    val name: String,
    val quantity: Double = 1.0,
    val unit: String = "g",
    val reason: String? = null,
)

@Serializable
data class SubstitutionDto(
    @SerialName("recommendation_id") val recommendationId: String,
    @SerialName("original_name") val originalName: String,
    val alternatives: List<SubstitutionAlternativeDto> = emptyList(),
    val warnings: List<String> = emptyList(),
)

@Serializable
data class VariantDto(
    @SerialName("recommendation_id") val recommendationId: String,
    val variant: String,
    val candidate: RecommendationCandidateDto? = null,
    @SerialName("changes_summary") val changesSummary: String? = null,
    val warnings: List<String> = emptyList(),
)

@Serializable
data class ActionExecuteDto(
    @SerialName("action_type") val actionType: String,
    val status: String,
    @SerialName("recommendation_id") val recommendationId: String? = null,
    val result: Map<String, kotlinx.serialization.json.JsonElement> = emptyMap(),
)

@Serializable
data class FeatureUsageDto(
    val feature: String,
    @SerialName("limit_value") val limitValue: Int? = null,
    @SerialName("used_value") val usedValue: Int = 0,
    val remaining: Int? = null,
)

@Serializable
data class EntitlementStatusDto(
    val tier: String = "free",
    val features: List<FeatureUsageDto> = emptyList(),
    @SerialName("premium_only") val premiumOnly: List<String> = emptyList(),
)

fun EntitlementStatusDto.aiRecommendationRemaining(): Int? =
    features.firstOrNull { it.feature == "ai_recommendation" }?.remaining
