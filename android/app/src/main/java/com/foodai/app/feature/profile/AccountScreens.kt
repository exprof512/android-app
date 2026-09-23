package com.foodai.app.feature.profile

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.foodai.app.core.analytics.AnalyticsTracker
import com.foodai.app.core.auth.AuthRepository
import com.foodai.app.core.network.CurrentUserDto
import com.foodai.app.core.network.SessionDto
import com.foodai.app.core.ui.components.FoodAICard
import com.foodai.app.core.ui.components.FoodAIInfoCard
import com.foodai.app.core.ui.components.FoodAIPrimaryButton
import com.foodai.app.core.ui.theme.FoodAIColors
import com.foodai.app.core.ui.theme.FoodAIDimens
import com.foodai.app.core.ui.theme.FoodAITypography
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class AccountViewModel @Inject constructor(
    private val auth: AuthRepository,
    private val analytics: AnalyticsTracker,
) : ViewModel() {
    var account by mutableStateOf<CurrentUserDto?>(null)
        private set
    var sessions by mutableStateOf<List<SessionDto>>(emptyList())
        private set
    var message by mutableStateOf<String?>(null)
        private set
    var busy by mutableStateOf(false)
        private set

    fun load() {
        viewModelScope.launch {
            runCatching {
                account = auth.currentAccount()
                sessions = auth.listSessions()
            }.onFailure { message = it.message }
        }
    }

    fun revoke(id: String) {
        viewModelScope.launch {
            runCatching {
                auth.revokeSession(id)
                sessions = auth.listSessions()
            }.onFailure { message = it.message }
        }
    }

    fun revokeAll() {
        viewModelScope.launch {
            runCatching {
                auth.revokeAllSessions()
                sessions = emptyList()
            }.onFailure { message = it.message }
        }
    }

    fun export(onDone: (String) -> Unit) {
        viewModelScope.launch {
            busy = true
            runCatching {
                analytics.track("data_export_requested")
                val json = auth.exportData().toString()
                onDone(json)
                message = "Экспорт готов (${json.length} символов)"
            }.onFailure { message = it.message }
            busy = false
        }
    }

    fun deleteAccount(onSuccess: () -> Unit) {
        viewModelScope.launch {
            busy = true
            runCatching {
                analytics.track("account_deleted")
                auth.deleteAccount()
                onSuccess()
            }.onFailure {
                message = it.message ?: "Удаление не выполнено. Сессия сохранена."
            }
            busy = false
        }
    }

    fun resendVerification() {
        viewModelScope.launch {
            val email = account?.email ?: return@launch
            runCatching {
                auth.resendVerification(email)
                message = "Если письмо доступно, инструкции отправлены."
            }.onFailure { message = it.message }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AccountRoute(
    onBack: () -> Unit,
    onDeleted: () -> Unit,
    viewModel: AccountViewModel = hiltViewModel(),
) {
    val scope = rememberCoroutineScope()
    var confirmDelete by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) { viewModel.load() }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Аккаунт") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Назад")
                    }
                },
            )
        },
        containerColor = FoodAIColors.Background,
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(FoodAIDimens.ScreenPadding)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(FoodAIDimens.Space12),
        ) {
            val account = viewModel.account
            FoodAICard {
                Text("Email", style = FoodAITypography.titleMedium)
                Text(account?.email ?: "—", style = FoodAITypography.bodyMedium)
                Spacer(Modifier.height(FoodAIDimens.Space8))
                Text(
                    if (account?.emailVerified == true) "Email подтверждён"
                    else "Email не подтверждён",
                    style = FoodAITypography.labelMedium,
                    color = if (account?.emailVerified == true) FoodAIColors.Primary else FoodAIColors.Warning,
                )
                if (account?.emailVerified != true) {
                    TextButton(onClick = viewModel::resendVerification) {
                        Text("Отправить письмо снова", color = FoodAIColors.Primary)
                    }
                }
            }

            val consent = account?.consent
            if (consent != null) {
                FoodAICard {
                    Text("Документы", style = FoodAITypography.titleMedium)
                    LegalLink("Условия использования", consent.termsUrl)
                    LegalLink("Политика конфиденциальности", consent.privacyUrl)
                    Text(
                        "Версии: terms ${consent.termsVersion ?: "—"} · privacy ${consent.privacyVersion ?: "—"}",
                        style = FoodAITypography.bodySmall,
                    )
                }
            }

            FoodAICard {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                ) {
                    Text("Активные сессии", style = FoodAITypography.titleMedium)
                    TextButton(onClick = viewModel::revokeAll) {
                        Text("Выйти везде", color = FoodAIColors.Error)
                    }
                }
                if (viewModel.sessions.isEmpty()) {
                    Text("Нет активных сессий", style = FoodAITypography.bodySmall)
                }
                viewModel.sessions.forEach { session ->
                    Column(Modifier.padding(vertical = FoodAIDimens.Space4)) {
                        Text(
                            listOfNotNull(
                                session.platform,
                                session.deviceLabel,
                                session.appVersion,
                            ).joinToString(" · ").ifBlank { "Устройство" },
                            style = FoodAITypography.titleSmall,
                        )
                        Text(
                            "Создана: ${session.createdAt.take(19)}",
                            style = FoodAITypography.bodySmall,
                        )
                        TextButton(onClick = { viewModel.revoke(session.id) }) {
                            Text("Завершить", color = FoodAIColors.Primary)
                        }
                    }
                }
            }

            FoodAIPrimaryButton(
                label = if (viewModel.busy) "Экспорт…" else "Экспорт моих данных",
                onClick = {
                    viewModel.export { /* JSON kept in message; file share later */ }
                },
                showArrow = false,
                enabled = !viewModel.busy,
            )

            if (!confirmDelete) {
                FoodAIPrimaryButton(
                    label = "Удалить аккаунт",
                    onClick = { confirmDelete = true },
                    showArrow = false,
                )
            } else {
                FoodAIInfoCard(
                    text = "Удаление безвозвратно: планы, прогресс, чат и профиль будут стёрты на сервере. Локальная сессия очистится только после подтверждения сервера.",
                )
                FoodAIPrimaryButton(
                    label = if (viewModel.busy) "Удаляем…" else "Подтвердить удаление",
                    onClick = { viewModel.deleteAccount(onDeleted) },
                    showArrow = false,
                    enabled = !viewModel.busy,
                )
                TextButton(onClick = { confirmDelete = false }) {
                    Text("Отмена", color = FoodAIColors.TextSecondary)
                }
            }

            viewModel.message?.let {
                Text(it, style = FoodAITypography.bodySmall, color = FoodAIColors.Primary)
            }
        }
    }
}

@Composable
private fun LegalLink(label: String, url: String?) {
    val context = LocalContext.current
    TextButton(
        onClick = {
            if (!url.isNullOrBlank()) {
                context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
            }
        },
        enabled = !url.isNullOrBlank(),
    ) {
        Text(label, color = FoodAIColors.Primary)
    }
}
