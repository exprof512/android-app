package com.foodai.app.feature.auth

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.foodai.app.core.ui.theme.FoodAiTokens

@Composable
fun AuthRoute(
    onSignedIn: () -> Unit,
    viewModel: AuthViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    LaunchedEffect(state.signedIn, state.successMessage) {
        if (!state.signedIn) return@LaunchedEffect
        if (state.successMessage != null) {
            kotlinx.coroutines.delay(1_200)
        }
        onSignedIn()
    }
    AuthScreen(
        state = state,
        onEmailChange = viewModel::onEmailChange,
        onPasswordChange = viewModel::onPasswordChange,
        onResetTokenChange = viewModel::onResetTokenChange,
        onToggleMode = viewModel::toggleMode,
        onForgot = viewModel::openForgot,
        onBackToLogin = viewModel::backToLogin,
        onSubmit = viewModel::submit,
    )
}

@Composable
fun AuthScreen(
    state: AuthUiState,
    onEmailChange: (String) -> Unit,
    onPasswordChange: (String) -> Unit,
    onResetTokenChange: (String) -> Unit = {},
    onToggleMode: () -> Unit,
    onForgot: () -> Unit = {},
    onBackToLogin: () -> Unit = {},
    onSubmit: () -> Unit,
) {
    val title = when {
        state.isForgotMode -> "Сброс пароля"
        state.isResetMode -> "Новый пароль"
        state.isRegisterMode -> "Создайте аккаунт, чтобы продолжить"
        else -> "Войдите, чтобы открыть план питания"
    }
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(FoodAiTokens.SpaceLg.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            text = "FoodAI",
            style = MaterialTheme.typography.displayLarge,
            color = MaterialTheme.colorScheme.primary,
        )
        Spacer(Modifier.height(FoodAiTokens.SpaceSm.dp))
        Text(
            text = title,
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Spacer(Modifier.height(FoodAiTokens.SpaceXl.dp))
        if (!state.isResetMode) {
            OutlinedTextField(
                value = state.email,
                onValueChange = onEmailChange,
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Email") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
                enabled = !state.isLoading,
            )
            Spacer(Modifier.height(FoodAiTokens.SpaceMd.dp))
        }
        if (state.isResetMode) {
            OutlinedTextField(
                value = state.resetToken,
                onValueChange = onResetTokenChange,
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Токен из письма") },
                singleLine = true,
                enabled = !state.isLoading,
            )
            Spacer(Modifier.height(FoodAiTokens.SpaceMd.dp))
        }
        if (!state.isForgotMode) {
            OutlinedTextField(
                value = state.password,
                onValueChange = onPasswordChange,
                modifier = Modifier.fillMaxWidth(),
                label = { Text(if (state.isResetMode) "Новый пароль" else "Пароль") },
                singleLine = true,
                visualTransformation = PasswordVisualTransformation(),
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
                enabled = !state.isLoading,
            )
        }
        if (state.error != null) {
            Spacer(Modifier.height(FoodAiTokens.SpaceMd.dp))
            Text(
                text = state.error,
                color = MaterialTheme.colorScheme.error,
                style = MaterialTheme.typography.bodyMedium,
            )
        }
        if (state.successMessage != null) {
            Spacer(Modifier.height(FoodAiTokens.SpaceMd.dp))
            Text(
                text = state.successMessage,
                color = FoodAiTokens.Forest,
                style = MaterialTheme.typography.bodyMedium,
            )
        }
        Spacer(Modifier.height(FoodAiTokens.SpaceLg.dp))
        Button(
            onClick = onSubmit,
            modifier = Modifier.fillMaxWidth(),
            enabled = !state.isLoading,
        ) {
            if (state.isLoading) {
                CircularProgressIndicator(
                    modifier = Modifier.height(20.dp),
                    strokeWidth = 2.dp,
                    color = MaterialTheme.colorScheme.onPrimary,
                )
            } else {
                Text(
                    when {
                        state.isForgotMode -> "Отправить инструкции"
                        state.isResetMode -> "Сохранить пароль"
                        state.isRegisterMode -> "Зарегистрироваться"
                        else -> "Войти"
                    },
                )
            }
        }
        if (!state.isForgotMode && !state.isResetMode && !state.isRegisterMode) {
            TextButton(onClick = onForgot, enabled = !state.isLoading) {
                Text("Забыли пароль?")
            }
        }
        if (state.isForgotMode || state.isResetMode) {
            TextButton(onClick = onBackToLogin, enabled = !state.isLoading) {
                Text("Назад ко входу")
            }
        } else {
            TextButton(onClick = onToggleMode, enabled = !state.isLoading) {
                Text(
                    if (state.isRegisterMode) {
                        "Уже есть аккаунт? Войти"
                    } else {
                        "Нет аккаунта? Регистрация"
                    },
                )
            }
        }
    }
}
