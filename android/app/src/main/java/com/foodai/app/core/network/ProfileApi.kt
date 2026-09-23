package com.foodai.app.core.network

import okhttp3.ResponseBody
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Path
import retrofit2.http.Query

interface ProfileApi {
    @GET("profile")
    suspend fun getProfile(): ProfileResponse

    @PUT("profile")
    suspend fun updateProfile(@Body body: ProfileUpdateRequest): ProfileResponse

    @POST("profile/calculate-target")
    suspend fun calculateTarget(@Body body: TargetPreviewRequest): TargetPreviewResponse
}

interface MealPlanApi {
    @POST("meal-plans/generate")
    suspend fun generate(@Body body: MealPlanGenerateRequest): MealPlanDto

    @GET("meal-plans/today")
    suspend fun today(@Query("date") date: String? = null): MealPlanDto

    @GET("meal-plans/week")
    suspend fun week(@Query("start_date") startDate: String? = null): MealPlanDto

    @POST("meal-plan-items/{itemId}/replace")
    suspend fun replaceItem(
        @Path("itemId") itemId: String,
        @Body body: MealPlanReplaceRequest = MealPlanReplaceRequest(),
        @Header("Idempotency-Key") idempotencyKey: String? = null,
    ): MealPlanDto

    @POST("meal-plan-items/{itemId}/complete")
    suspend fun completeItem(
        @Path("itemId") itemId: String,
        @Query("completed") completed: Boolean = true,
    ): MealPlanItemDto

    @POST("meal-plan-items/{itemId}/skip")
    suspend fun skipItem(
        @Path("itemId") itemId: String,
        @Query("skipped") skipped: Boolean = true,
    ): MealPlanItemDto
}

interface RecipeApi {
    @GET("recipes/favorites")
    suspend fun listFavorites(): List<DishCardDto>

    @GET("recipes/search")
    suspend fun search(
        @Query("q") query: String? = null,
        @Query("max_kcal") maxKcal: Int? = null,
        @Query("min_protein_g") minProteinG: Double? = null,
        @Query("max_cook_time") maxCookTime: Int? = null,
        @Query("max_cost") maxCost: Double? = null,
    ): List<DishCardDto>

    @GET("recipes/{recipeId}")
    suspend fun getRecipe(@Path("recipeId") recipeId: String): DishCardDto

    @GET("recipes/{recipeId}/image")
    suspend fun getImage(@Path("recipeId") recipeId: String): RecipeImageDto

    @POST("recipes/{recipeId}/favorite")
    suspend fun addFavorite(@Path("recipeId") recipeId: String)

    @DELETE("recipes/{recipeId}/favorite")
    suspend fun removeFavorite(@Path("recipeId") recipeId: String)
}

interface ShoppingApi {
    @POST("shopping-lists/generate")
    suspend fun generate(@Body body: ShoppingGenerateRequest): ShoppingListDto

    @GET("shopping-lists/current")
    suspend fun current(@Query("meal_plan_id") mealPlanId: String? = null): ShoppingListDto

    @POST("shopping-list-items/{itemId}/complete")
    suspend fun completeItem(
        @Path("itemId") itemId: String,
        @Query("completed") completed: Boolean = true,
    ): ShoppingListItemDto

    @POST("shopping-list-items/clear-completed")
    suspend fun clearCompleted(@Query("list_id") listId: String? = null): ShoppingListDto
}

interface ProgressApi {
    @POST("weight-entries")
    suspend fun createWeightEntry(@Body body: WeightEntryCreateRequest): WeightEntryDto

    @GET("weight-entries")
    suspend fun listWeightEntries(
        @Query("from") from: String? = null,
        @Query("to") to: String? = null,
    ): List<WeightEntryDto>

    @GET("progress/summary")
    suspend fun summary(
        @Query("date") date: String? = null,
        @Query("period") period: Int? = null,
    ): ProgressSummaryDto
}

interface WaterApi {
    @GET("water/today")
    suspend fun today(@Query("date") date: String? = null): WaterTodayDto

    @POST("water")
    suspend fun add(@Body body: WaterEntryCreateRequest): WaterEntryDto

    @DELETE("water/last")
    suspend fun deleteLast(): Response<ResponseBody>
}

interface ChatApi {
    @POST("ai/chat/conversations")
    suspend fun createConversation(@Body body: ConversationCreateRequest): ConversationDto

    @GET("ai/chat/conversations/{conversationId}")
    suspend fun getConversation(@Path("conversationId") conversationId: String): ConversationDto

    @POST("ai/chat/conversations/{conversationId}/messages")
    suspend fun postMessage(
        @Path("conversationId") conversationId: String,
        @Body body: ChatMessageCreateRequest,
    ): ChatMessageResponseDto
}
