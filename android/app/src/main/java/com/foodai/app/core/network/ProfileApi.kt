package com.foodai.app.core.network

import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
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
    suspend fun replaceItem(@Path("itemId") itemId: String): MealPlanDto

    @POST("meal-plan-items/{itemId}/complete")
    suspend fun completeItem(
        @Path("itemId") itemId: String,
        @Query("completed") completed: Boolean = true,
    ): MealPlanItemDto
}

interface RecipeApi {
    @GET("recipes/{recipeId}")
    suspend fun getRecipe(@Path("recipeId") recipeId: String): DishCardDto

    @GET("recipes/{recipeId}/image")
    suspend fun getImage(@Path("recipeId") recipeId: String): RecipeImageDto

    @POST("recipes/{recipeId}/favorite")
    suspend fun addFavorite(@Path("recipeId") recipeId: String)

    @DELETE("recipes/{recipeId}/favorite")
    suspend fun removeFavorite(@Path("recipeId") recipeId: String)
}
