package com.foodai.app.feature.chat

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import com.foodai.app.core.auth.toUiMessage
import com.foodai.app.core.chat.ChatRepository
import com.foodai.app.core.network.ApiException
import com.foodai.app.core.network.ChatMessageDto
import com.foodai.app.core.ui.ErrorPane
import com.foodai.app.core.ui.LoadingPane
import com.foodai.app.core.ui.theme.FoodAiTokens
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ChatUiState(
    val loading: Boolean = true,
    val sending: Boolean = false,
    val conversationId: String? = null,
    val messages: List<ChatMessageDto> = emptyList(),
    val draft: String = "",
    val disclaimer: String = "",
    val error: String? = null,
    val actionError: String? = null,
)

@HiltViewModel
class ChatViewModel @Inject constructor(
    savedStateHandle: SavedStateHandle,
    private val chat: ChatRepository,
) : ViewModel() {
    private val recipeId: String? = savedStateHandle["recipeId"]

    private val _state = MutableStateFlow(ChatUiState())
    val state: StateFlow<ChatUiState> = _state.asStateFlow()

    init {
        start()
    }

    fun start() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null)
            try {
                val conversation = chat.start(recipeId = recipeId)
                _state.value = ChatUiState(
                    loading = false,
                    conversationId = conversation.id,
                    messages = conversation.messages,
                    disclaimer = conversation.disclaimer,
                )
            } catch (error: ApiException) {
                _state.value = _state.value.copy(loading = false, error = error.toUiMessage())
            }
        }
    }

    fun onDraft(value: String) {
        _state.value = _state.value.copy(draft = value)
    }

    fun send() {
        val conversationId = _state.value.conversationId ?: return
        val text = _state.value.draft.trim()
        if (text.isEmpty()) return
        viewModelScope.launch {
            _state.value = _state.value.copy(sending = true, actionError = null, draft = "")
            try {
                val response = chat.send(conversationId, text)
                _state.value = _state.value.copy(
                    sending = false,
                    messages = _state.value.messages + response.userMessage + response.assistantMessage,
                    disclaimer = response.disclaimer.ifBlank { _state.value.disclaimer },
                )
            } catch (error: ApiException) {
                _state.value = _state.value.copy(sending = false, actionError = error.toUiMessage())
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatRoute(
    onBack: () -> Unit,
    viewModel: ChatViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Ask AI") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Назад")
                    }
                },
            )
        },
    ) { padding ->
        when {
            state.loading -> LoadingPane(modifier = Modifier.padding(padding))
            state.error != null -> ErrorPane(
                message = state.error ?: "Ошибка",
                onRetry = viewModel::start,
                modifier = Modifier.padding(padding),
            )
            else -> ChatScreen(
                state = state,
                onDraft = viewModel::onDraft,
                onSend = viewModel::send,
                modifier = Modifier.padding(padding),
            )
        }
    }
}

@Composable
fun ChatScreen(
    state: ChatUiState,
    onDraft: (String) -> Unit,
    onSend: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(FoodAiTokens.SpaceMd.dp),
        verticalArrangement = Arrangement.spacedBy(FoodAiTokens.SpaceSm.dp),
    ) {
        LazyColumn(
            modifier = Modifier.weight(1f).fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            items(state.messages, key = { it.id }) { message ->
                val isUser = message.role == "user"
                Text(
                    if (isUser) "Вы" else "FoodAI",
                    style = MaterialTheme.typography.labelLarge,
                    color = MaterialTheme.colorScheme.primary,
                )
                Text(message.content)
                message.suggestedActions.forEach { action ->
                    Text(
                        "→ ${action.label}",
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }
        if (state.actionError != null) {
            Text(state.actionError, color = MaterialTheme.colorScheme.error)
        }
        if (state.disclaimer.isNotBlank()) {
            Text(
                state.disclaimer,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            OutlinedTextField(
                value = state.draft,
                onValueChange = onDraft,
                modifier = Modifier.weight(1f),
                label = { Text("Вопрос") },
                enabled = !state.sending,
            )
            Button(onClick = onSend, enabled = !state.sending && state.draft.isNotBlank()) {
                Text(if (state.sending) "…" else "Отправить")
            }
        }
    }
}
