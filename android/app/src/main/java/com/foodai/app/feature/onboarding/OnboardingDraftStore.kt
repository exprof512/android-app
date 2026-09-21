package com.foodai.app.feature.onboarding

import android.content.Context
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class OnboardingDraftStore @Inject constructor(
    @ApplicationContext context: Context,
    private val json: Json,
) {
    private val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun load(): OnboardingDraft {
        val raw = prefs.getString(KEY, null) ?: return OnboardingDraft()
        return runCatching { json.decodeFromString(OnboardingDraft.serializer(), raw) }
            .getOrDefault(OnboardingDraft())
    }

    fun save(draft: OnboardingDraft) {
        prefs.edit().putString(KEY, json.encodeToString(OnboardingDraft.serializer(), draft)).apply()
    }

    fun clear() {
        prefs.edit().remove(KEY).apply()
    }

    companion object {
        private const val PREFS = "foodai_onboarding_draft"
        private const val KEY = "draft_json"
    }
}
