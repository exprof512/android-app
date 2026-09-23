package com.foodai.app.core.profile

import com.foodai.app.core.mealplan.MealPlanRepository
import com.foodai.app.core.network.ApiErrorParser
import com.foodai.app.core.network.MealPlanDto
import com.foodai.app.core.network.ProfileApi
import com.foodai.app.core.network.ProfileResponse
import com.foodai.app.core.network.ProfileUpdateRequest
import com.foodai.app.core.network.TargetPreviewRequest
import com.foodai.app.core.network.TargetPreviewResponse
import com.foodai.app.core.sync.AppStateBus
import com.foodai.app.core.sync.DomainEvent
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ProfileRepository @Inject constructor(
    private val profileApi: ProfileApi,
    private val mealPlans: MealPlanRepository,
    private val bus: AppStateBus,
) {
    private val _profile = MutableStateFlow<ProfileResponse?>(null)
    val profile: StateFlow<ProfileResponse?> = _profile.asStateFlow()

    suspend fun getProfile(force: Boolean = false): ProfileResponse {
        if (!force) {
            _profile.value?.let { return it }
        }
        val loaded = wrap { profileApi.getProfile() }
        _profile.value = loaded
        return loaded
    }

    suspend fun refreshProfile(): ProfileResponse = getProfile(force = true)

    suspend fun updateProfile(body: ProfileUpdateRequest): ProfileResponse {
        val updated = wrap { profileApi.updateProfile(body) }
        _profile.value = updated
        bus.emit(DomainEvent.ProfileChanged("update"))
        return updated
    }

    suspend fun previewTarget(body: TargetPreviewRequest): TargetPreviewResponse =
        wrap { profileApi.calculateTarget(body) }

    suspend fun generateFirstPlan(days: Int = 7, force: Boolean = false): MealPlanDto =
        mealPlans.generate(days = days, force = force)

    suspend fun ensurePlan(days: Int = 7): MealPlanDto =
        try {
            mealPlans.today()
        } catch (error: Throwable) {
            val parsed = ApiErrorParser.fromThrowable(error)
            if (parsed.code == "meal_plan_not_found" || parsed.httpStatus == 404) {
                generateFirstPlan(days)
            } else {
                throw parsed
            }
        }

    suspend fun regeneratePlan(days: Int = 7): MealPlanDto =
        generateFirstPlan(days = days, force = true)

    fun invalidateLocal() {
        _profile.value = null
    }

    private suspend fun <T> wrap(block: suspend () -> T): T =
        try {
            block()
        } catch (error: Throwable) {
            throw ApiErrorParser.fromThrowable(error)
        }
}
