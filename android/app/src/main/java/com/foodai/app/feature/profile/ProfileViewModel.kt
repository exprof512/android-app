package com.foodai.app.feature.profile

import android.net.Uri
import androidx.lifecycle.ViewModel
import com.foodai.app.core.auth.AuthRepository
import com.foodai.app.core.metrics.DailyMetricsStore
import com.foodai.app.core.profile.LocalUserProfile
import com.foodai.app.core.profile.UserProfileStore
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import javax.inject.Inject
import kotlin.math.abs

@HiltViewModel
class ProfileViewModel @Inject constructor(
    private val auth: AuthRepository,
    private val userProfileStore: UserProfileStore,
    private val metricsStore: DailyMetricsStore,
) : ViewModel() {
    val localProfile: StateFlow<LocalUserProfile> = userProfileStore.profile

    private val _waterLitersLabel = MutableStateFlow("0.0 л")
    val waterLitersLabel: StateFlow<String> = _waterLitersLabel.asStateFlow()

    init {
        reload()
    }

    fun reload() {
        userProfileStore.load(userId())
        refreshWater()
    }

    fun setDisplayName(name: String) {
        userProfileStore.setDisplayName(userId(), name)
    }

    fun setBio(bio: String) {
        userProfileStore.setBio(userId(), bio)
    }

    fun setAvatar(uri: Uri): Boolean = userProfileStore.setAvatarFromUri(userId(), uri)

    fun clearAvatar() {
        userProfileStore.clearAvatar(userId())
    }

    fun displayNameOrFallback(email: String): String {
        val local = userProfileStore.profile.value.displayName
        if (local.isNotBlank()) return local
        return email.substringBefore("@").replaceFirstChar { it.uppercase() }
    }

    /**
     * Progress toward target weight from current weight.
     * Uses start→target span when available; otherwise 0.
     */
    fun weightProgress(currentKg: Double?, startKg: Double?, targetKg: Double?): Float {
        if (currentKg == null || targetKg == null) return 0f
        val start = startKg ?: currentKg
        val span = abs(targetKg - start)
        if (span < 0.01) return if (abs(currentKg - targetKg) < 0.01) 1f else 0f
        val done = abs(currentKg - start)
        return (done / span).toFloat().coerceIn(0f, 1f)
    }

    private fun refreshWater() {
        val liters = metricsStore.metrics(userId()).waterMl / 1000f
        _waterLitersLabel.value = String.format("%.1f л", liters)
    }

    private fun userId(): String = auth.currentUser()?.id ?: "anon"
}
