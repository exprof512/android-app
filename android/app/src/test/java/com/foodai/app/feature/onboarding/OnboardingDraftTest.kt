package com.foodai.app.feature.onboarding

import com.google.common.truth.Truth.assertThat
import org.junit.Test

class OnboardingDraftTest {
    @Test
    fun mapsUpdateRequestFromDraft() {
        val draft = OnboardingDraft(
            goalType = "lose_weight",
            targetWeightKg = "64",
            desiredWeeklyChangeKg = "0.4",
            sex = "female",
            ageYears = "31",
            heightCm = "168",
            currentWeightKg = "72.4",
            activityLevel = "moderate",
            mealsPerDay = "4",
            likedFoods = "гречка, лосось",
            pantryText = "яйца 10 piece\nрис 2 kg",
        )
        val body = draft.toUpdateRequest()
        assertThat(body.sex).isEqualTo("female")
        assertThat(body.mealsPerDay).isEqualTo(4)
        assertThat(body.likedFoods).containsExactly("гречка", "лосось")
        assertThat(body.availableProducts).hasSize(2)
        assertThat(body.availableProducts[0].name).isEqualTo("яйца")
        assertThat(body.availableProducts[1].unit).isEqualTo("kg")
    }

    @Test
    fun validatesRequiredAboutFields() {
        val draft = OnboardingDraft(ageYears = "", heightCm = "170", currentWeightKg = "70")
        assertThat(draft.validateStep(OnboardingStep.AboutYou)).contains("возраст")
    }
}
