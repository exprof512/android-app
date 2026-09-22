package com.foodai.app.core.profile

import com.foodai.app.core.network.ApiErrorParser
import com.foodai.app.core.network.MealPlanApi
import com.foodai.app.core.network.MealPlanDto
import com.foodai.app.core.network.MealPlanGenerateRequest
import com.foodai.app.core.network.ProfileApi
import com.foodai.app.core.network.ProfileResponse
import com.foodai.app.core.network.ProfileUpdateRequest
import com.foodai.app.core.network.TargetPreviewRequest
import com.foodai.app.core.network.TargetPreviewResponse
import java.time.LocalDate
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ProfileRepository @Inject constructor(
    private val profileApi: ProfileApi,
    private val mealPlanApi: MealPlanApi,
) {
    suspend fun getProfile(): ProfileResponse = wrap { profileApi.getProfile() }

    suspend fun updateProfile(body: ProfileUpdateRequest): ProfileResponse =
        wrap { profileApi.updateProfile(body) }

    suspend fun previewTarget(body: TargetPreviewRequest): TargetPreviewResponse =
        wrap { profileApi.calculateTarget(body) }

    suspend fun generateFirstPlan(days: Int = 7): MealPlanDto =
        wrap {
            mealPlanApi.generate(
                MealPlanGenerateRequest(
                    startDate = LocalDate.now().toString(),
                    days = days,
                ),
            )
        }

    /** Generate a plan when the user has none (e.g. after profile edit). */
    suspend fun ensurePlan(days: Int = 7): MealPlanDto =
        try {
            wrap { mealPlanApi.today(LocalDate.now().toString()) }
        } catch (error: Throwable) {
            val parsed = ApiErrorParser.fromThrowable(error)
            if (parsed.code == "meal_plan_not_found" || parsed.httpStatus == 404) {
                generateFirstPlan(days)
            } else {
                throw parsed
            }
        }

    private suspend fun <T> wrap(block: suspend () -> T): T =
        try {
            block()
        } catch (error: Throwable) {
            throw ApiErrorParser.fromThrowable(error)
        }
}
