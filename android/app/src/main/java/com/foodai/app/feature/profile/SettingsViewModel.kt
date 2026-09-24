package com.foodai.app.feature.profile

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.foodai.app.core.ai.AiRecommendationRepository
import com.foodai.app.core.network.EntitlementStatusDto
import com.foodai.app.core.profile.ProfileRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class SettingsViewModel @Inject constructor(
    private val ai: AiRecommendationRepository,
    private val profiles: ProfileRepository,
) : ViewModel() {
    private val _entitlements = MutableStateFlow<EntitlementStatusDto?>(null)
    val entitlements: StateFlow<EntitlementStatusDto?> = _entitlements.asStateFlow()

    private val _pantryNames = MutableStateFlow<List<String>>(emptyList())
    val pantryNames: StateFlow<List<String>> = _pantryNames.asStateFlow()

    init {
        reload()
    }

    fun reload() {
        viewModelScope.launch {
            _entitlements.value = runCatching { ai.entitlements() }.getOrNull()
            val profile = runCatching { profiles.refreshProfile() }.getOrNull()
            _pantryNames.value = profile?.availableProducts.orEmpty().map { it.name }
        }
    }
}
