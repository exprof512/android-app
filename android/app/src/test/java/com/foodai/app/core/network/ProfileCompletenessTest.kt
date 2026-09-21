package com.foodai.app.core.network

import com.google.common.truth.Truth.assertThat
import org.junit.Test

class ProfileCompletenessTest {
    @Test
    fun incompleteWithoutGoal() {
        val response = ProfileResponse(
            profile = ProfileFieldsDto(
                sex = "female",
                ageYears = 30,
                heightCm = 170.0,
                currentWeightKg = 70.0,
                activityLevel = "moderate",
                mealsPerDay = 3,
            ),
            goal = null,
        )
        assertThat(response.isComplete()).isFalse()
    }

    @Test
    fun completeWithGoalAndCoreFields() {
        val response = ProfileResponse(
            profile = ProfileFieldsDto(
                sex = "female",
                ageYears = 30,
                heightCm = 170.0,
                currentWeightKg = 70.0,
                activityLevel = "moderate",
                mealsPerDay = 3,
            ),
            goal = GoalViewDto(
                id = "g1",
                goalType = "lose_weight",
                status = "active",
                calorieTargetKcal = 1800,
                macroTargetsG = MacroTargetsDto(100, 60, 200),
                bmrKcal = 1400,
                tdeeKcal = 2000,
                safetyFloorKcal = 1200,
            ),
        )
        assertThat(response.isComplete()).isTrue()
    }
}
