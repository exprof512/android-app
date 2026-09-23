package com.foodai.app.core.auth

import com.foodai.app.core.metrics.DailyMetricsStore
import com.foodai.app.core.profile.UserProfileStore
import com.foodai.app.feature.onboarding.OnboardingDraftStore
import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Inject
import javax.inject.Singleton

/** Clears onboarding draft / daily metrics / profile so accounts never share local UI state. */
interface LocalSessionCleaner {
    fun clearBeforeNewSession()
    fun clearOnLogout(userId: String?)
}

@Singleton
class DefaultLocalSessionCleaner @Inject constructor(
    private val draftStore: OnboardingDraftStore,
    private val metricsStore: DailyMetricsStore,
    private val userProfileStore: UserProfileStore,
) : LocalSessionCleaner {
    override fun clearBeforeNewSession() {
        draftStore.clearAll()
        metricsStore.clearAll()
        userProfileStore.clearAll()
    }

    override fun clearOnLogout(userId: String?) {
        if (userId != null) {
            draftStore.clear(userId)
            metricsStore.clearUser(userId)
            userProfileStore.clearUser(userId)
        } else {
            draftStore.clearAll()
            metricsStore.clearAll()
            userProfileStore.clearAll()
        }
    }
}

@Module
@InstallIn(SingletonComponent::class)
abstract class LocalSessionCleanerModule {
    @Binds
    @Singleton
    abstract fun bindCleaner(impl: DefaultLocalSessionCleaner): LocalSessionCleaner
}
