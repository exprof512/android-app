package com.foodai.app.feature.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
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
    val isRegisterMode: Boolean = false,
    val isLoading: Boolean = false,
    val error: String? = null,
    val successMessage: String? = null,
    val signedIn: Boolean = false,
)

@HiltViewModel
class AuthViewModel @Inject constructor(
    private val authRepository: AuthRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(AuthUiState(signedIn = authRepository.hasSession()))
    val state: StateFlow<AuthUiState> = _state.asStateFlow()

    fun onEmailChange(value: String) = _state.update { it.copy(email = value, error = null) }

    fun onPasswordChange(value: String) = _state.update { it.copy(password = value, error = null) }

    fun toggleMode() = _state.update {
        it.copy(isRegisterMode = !it.isRegisterMode, error = null, successMessage = null)
    }

    fun submit() {
        val snapshot = _state.value
        if (snapshot.email.isBlank() || snapshot.password.length < 8) {
            _state.update { it.copy(error = "Email и пароль (от 8 символов) обязательны") }
            return
        }
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true, error = null, successMessage = null) }
            try {
                if (snapshot.isRegisterMode) {
                    authRepository.register(snapshot.email, snapshot.password)
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
                    _state.update { it.copy(isLoading = false, signedIn = true, password = "") }
                }
            } catch (error: ApiException) {
                _state.update { it.copy(isLoading = false, error = error.toUiMessage()) }
            }
        }
    }
}
