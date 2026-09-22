package com.foodai.app.core.auth

import com.foodai.app.core.metrics.DailyMetricsStore
import com.foodai.app.feature.onboarding.OnboardingDraftStore
import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Inject
import javax.inject.Singleton

/** Clears onboarding draft / daily metrics so accounts never share local UI state. */
interface LocalSessionCleaner {
    fun clearBeforeNewSession()
    fun clearOnLogout(userId: String?)
}

@Singleton
class DefaultLocalSessionCleaner @Inject constructor(
    private val draftStore: OnboardingDraftStore,
    private val metricsStore: DailyMetricsStore,
) : LocalSessionCleaner {
    override fun clearBeforeNewSession() {
        draftStore.clear()
        metricsStore.clearAll()
    }

    override fun clearOnLogout(userId: String?) {
        draftStore.clear()
        if (userId != null) metricsStore.clearUser(userId) else metricsStore.clearAll()
    }
}

@Module
@InstallIn(SingletonComponent::class)
abstract class LocalSessionCleanerModule {
    @Binds
    @Singleton
    abstract fun bindCleaner(impl: DefaultLocalSessionCleaner): LocalSessionCleaner
}
