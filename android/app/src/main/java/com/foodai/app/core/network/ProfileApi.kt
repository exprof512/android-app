package com.foodai.app.core.network

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.PUT

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
    suspend fun generate(@Body body: MealPlanGenerateRequest): MealPlanSummaryResponse
}
