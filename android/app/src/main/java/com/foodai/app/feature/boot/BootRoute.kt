package com.foodai.app.feature.boot

import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import com.foodai.app.core.auth.AuthRepository
import com.foodai.app.core.network.isComplete
import com.foodai.app.core.profile.ProfileRepository
import com.foodai.app.core.ui.ErrorPane
import com.foodai.app.core.ui.LoadingPane
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

sealed interface BootDestination {
    data object Loading : BootDestination
    data object Onboarding : BootDestination
    data object Main : BootDestination
    data class Error(val message: String) : BootDestination
}

@HiltViewModel
class BootViewModel @Inject constructor(
    private val authRepository: AuthRepository,
    private val profileRepository: ProfileRepository,
) : ViewModel() {
    private val _destination = MutableStateFlow<BootDestination>(BootDestination.Loading)
    val destination: StateFlow<BootDestination> = _destination.asStateFlow()

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _destination.value = BootDestination.Loading
            if (!authRepository.hasSession()) {
                _destination.value = BootDestination.Error("Нет сессии")
                return@launch
            }
            if (authRepository.pendingOnboarding()) {
                _destination.value = BootDestination.Onboarding
                return@launch
            }
            try {
                val profile = profileRepository.getProfile()
                _destination.value = if (profile.isComplete()) {
                    BootDestination.Main
                } else {
                    BootDestination.Onboarding
                }
            } catch (error: Exception) {
                _destination.value = BootDestination.Error(error.message ?: "Ошибка профиля")
            }
        }
    }
}

@Composable
fun BootRoute(
    onOnboarding: () -> Unit,
    onMain: () -> Unit,
    onSignedOut: () -> Unit,
    viewModel: BootViewModel = hiltViewModel(),
) {
    val destination by viewModel.destination.collectAsStateWithLifecycle()
    LaunchedEffect(destination) {
        when (destination) {
            BootDestination.Onboarding -> onOnboarding()
            BootDestination.Main -> onMain()
            else -> Unit
        }
    }
    when (val dest = destination) {
        BootDestination.Loading -> LoadingPane("Готовим приложение…")
        is BootDestination.Error -> ErrorPane(
            message = dest.message,
            onRetry = {
                if (dest.message == "Нет сессии") onSignedOut() else viewModel.refresh()
            },
        )
        BootDestination.Onboarding, BootDestination.Main -> LoadingPane("Переход…")
    }
}
