package com.foodai.app.feature.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.foodai.app.core.analytics.AnalyticsTracker
import com.foodai.app.core.auth.AuthRepository
import com.foodai.app.core.auth.toUiMessage
import com.foodai.app.core.network.ApiException
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class AuthUiState(
    val email: String = "",
    val password: String = "",
    val resetToken: String = "",
    val isRegisterMode: Boolean = false,
    val isForgotMode: Boolean = false,
    val isResetMode: Boolean = false,
    val isLoading: Boolean = false,
    val error: String? = null,
    val successMessage: String? = null,
    val signedIn: Boolean = false,
)

@HiltViewModel
class AuthViewModel @Inject constructor(
    private val authRepository: AuthRepository,
    private val analytics: AnalyticsTracker,
) : ViewModel() {
    private val _state = MutableStateFlow(AuthUiState(signedIn = authRepository.hasSession()))
    val state: StateFlow<AuthUiState> = _state.asStateFlow()

    fun onEmailChange(value: String) = _state.update { it.copy(email = value, error = null) }

    fun onPasswordChange(value: String) = _state.update { it.copy(password = value, error = null) }

    fun onResetTokenChange(value: String) = _state.update { it.copy(resetToken = value, error = null) }

    fun toggleMode() = _state.update {
        it.copy(
            isRegisterMode = !it.isRegisterMode,
            isForgotMode = false,
            isResetMode = false,
            error = null,
            successMessage = null,
        )
    }

    fun openForgot() = _state.update {
        it.copy(isForgotMode = true, isResetMode = false, error = null, successMessage = null)
    }

    fun openReset() = _state.update {
        it.copy(isResetMode = true, isForgotMode = false, error = null, successMessage = null)
    }

    fun backToLogin() = _state.update {
        it.copy(isForgotMode = false, isResetMode = false, isRegisterMode = false, error = null)
    }

    fun submit() {
        val snapshot = _state.value
        when {
            snapshot.isForgotMode -> forgot()
            snapshot.isResetMode -> reset()
            else -> loginOrRegister()
        }
    }

    private fun forgot() {
        val email = _state.value.email
        if (email.isBlank()) {
            _state.update { it.copy(error = "Укажите email") }
            return
        }
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true, error = null) }
            try {
                val msg = authRepository.forgotPassword(email)
                _state.update {
                    it.copy(
                        isLoading = false,
                        successMessage = msg.message,
                        isForgotMode = false,
                        isResetMode = true,
                    )
                }
            } catch (error: ApiException) {
                _state.update { it.copy(isLoading = false, error = error.toUiMessage()) }
            }
        }
    }

    private fun reset() {
        val snapshot = _state.value
        if (snapshot.resetToken.isBlank() || snapshot.password.length < 8) {
            _state.update { it.copy(error = "Токен и новый пароль (от 8 символов) обязательны") }
            return
        }
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true, error = null) }
            try {
                val msg = authRepository.resetPassword(snapshot.resetToken, snapshot.password)
                _state.update {
                    it.copy(
                        isLoading = false,
                        successMessage = msg.message,
                        isResetMode = false,
                        password = "",
                        resetToken = "",
                    )
                }
            } catch (error: ApiException) {
                _state.update { it.copy(isLoading = false, error = error.toUiMessage()) }
            }
        }
    }

    private fun loginOrRegister() {
        val snapshot = _state.value
        if (snapshot.email.isBlank() || snapshot.password.length < 8) {
            _state.update { it.copy(error = "Email и пароль (от 8 символов) обязательны") }
            return
        }
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true, error = null, successMessage = null) }
            try {
                if (snapshot.isRegisterMode) {
                    analytics.track("registration_started")
                    authRepository.register(snapshot.email, snapshot.password)
                    analytics.track("registration_completed")
                    _state.update {
                        it.copy(
                            isLoading = false,
                            signedIn = true,
                            password = "",
                            successMessage = "Регистрация прошла успешно. Заполните анкету.",
                        )
                    }
                } else {
                    authRepository.login(snapshot.email, snapshot.password)
                    analytics.track("login_completed")
                    _state.update { it.copy(isLoading = false, signedIn = true, password = "") }
                }
            } catch (error: ApiException) {
                _state.update { it.copy(isLoading = false, error = error.toUiMessage()) }
            }
        }
    }
}
