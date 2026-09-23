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

    fun load(userId: String?): OnboardingDraft {
        if (userId.isNullOrBlank()) return OnboardingDraft()
        val raw = prefs.getString(key(userId), null) ?: return OnboardingDraft()
        return runCatching { json.decodeFromString(OnboardingDraft.serializer(), raw) }
            .getOrDefault(OnboardingDraft())
    }

    fun save(userId: String?, draft: OnboardingDraft) {
        if (userId.isNullOrBlank()) return
        prefs.edit()
            .putString(key(userId), json.encodeToString(OnboardingDraft.serializer(), draft))
            .commit()
    }

    fun clear(userId: String?) {
        if (userId.isNullOrBlank()) return
        prefs.edit().remove(key(userId)).commit()
    }

    /** Drop every account's draft — used before login/register so UI state cannot leak. */
    fun clearAll() {
        // commit(): apply() can race with the next account's hydrate and leak the questionnaire.
        prefs.edit().clear().commit()
    }

    private fun key(userId: String) = "draft_json:$userId"

    companion object {
        private const val PREFS = "foodai_onboarding_draft"
    }
}
