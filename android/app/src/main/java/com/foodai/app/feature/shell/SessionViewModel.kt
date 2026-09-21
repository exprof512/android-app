package com.foodai.app.feature.shell

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.foodai.app.core.auth.AuthRepository
import com.foodai.app.core.network.ProfileResponse
import com.foodai.app.core.network.UserSummaryDto
import com.foodai.app.core.profile.ProfileRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class SessionUiState(
    val user: UserSummaryDto? = null,
    val profile: ProfileResponse? = null,
    val loading: Boolean = true,
    val error: String? = null,
)

@HiltViewModel
class SessionViewModel @Inject constructor(
    private val authRepository: AuthRepository,
    private val profileRepository: ProfileRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(SessionUiState(user = authRepository.currentUser()))
    val state: StateFlow<SessionUiState> = _state.asStateFlow()

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null)
            try {
                val me = authRepository.refreshMe()
                val profile = runCatching { profileRepository.getProfile() }.getOrNull()
                _state.value = SessionUiState(user = me, profile = profile, loading = false)
            } catch (error: Exception) {
                _state.value = SessionUiState(
                    user = authRepository.currentUser(),
                    profile = _state.value.profile,
                    loading = false,
                    error = error.message,
                )
            }
        }
    }

    fun logout(onDone: () -> Unit) {
        viewModelScope.launch {
            authRepository.logout()
            onDone()
        }
    }
}
