package com.foodai.app.feature.chat

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import com.foodai.app.core.auth.toUiMessage
import com.foodai.app.core.chat.ChatRepository
import com.foodai.app.core.mealplan.MealPlanRepository
import com.foodai.app.core.network.ApiException
import com.foodai.app.core.network.ChatMessageDto
import com.foodai.app.core.network.SuggestedActionDto
import com.foodai.app.core.ui.ErrorPane
import com.foodai.app.core.ui.LoadingPane
import com.foodai.app.core.ui.theme.FoodAIColors
import com.foodai.app.core.ui.theme.FoodAIDimens
import com.foodai.app.core.ui.theme.FoodAIShapes
import com.foodai.app.core.ui.theme.FoodAITypography
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.util.UUID
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
    val infoMessage: String? = null,
)

@HiltViewModel
class ChatViewModel @Inject constructor(
    savedStateHandle: SavedStateHandle,
    private val chat: ChatRepository,
    private val mealPlans: MealPlanRepository,
) : ViewModel() {
    private val recipeId: String? = savedStateHandle["recipeId"]
    private val itemId: String? = savedStateHandle["itemId"]

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

    fun send(prefilled: String? = null) {
        val conversationId = _state.value.conversationId ?: return
        val text = (prefilled ?: _state.value.draft).trim()
        if (text.isEmpty()) return
        val optimistic = ChatMessageDto(
            id = "local-${UUID.randomUUID()}",
            role = "user",
            content = text,
        )
        viewModelScope.launch {
            _state.value = _state.value.copy(
                sending = true,
                actionError = null,
                draft = if (prefilled == null) "" else _state.value.draft,
                messages = _state.value.messages + optimistic,
            )
            try {
                val response = chat.send(conversationId, text)
                val withoutOptimistic = _state.value.messages.filterNot { it.id == optimistic.id }
                _state.value = _state.value.copy(
                    sending = false,
                    messages = withoutOptimistic + response.userMessage + response.assistantMessage,
                    disclaimer = response.disclaimer.ifBlank { _state.value.disclaimer },
                )
            } catch (error: ApiException) {
                _state.value = _state.value.copy(
                    sending = false,
                    actionError = error.toUiMessage(),
                    messages = _state.value.messages.filterNot { it.id == optimistic.id },
                )
            }
        }
    }

    fun onSuggestedAction(action: SuggestedActionDto) {
        when (action.type) {
            "explain_balance" -> send(
                prefilled = "Объясни баланс калорий и макросов за сегодня относительно моей цели.",
            )
            "replace_meal_item" -> replaceMeal()
            "open_shopping_list" -> {
                _state.value = _state.value.copy(
                    infoMessage = "Откройте вкладку Shopping, чтобы увидеть список покупок.",
                )
            }
            else -> send(prefilled = action.label)
        }
    }

    private fun replaceMeal() {
        val id = itemId
        if (id.isNullOrBlank()) {
            send(prefilled = "Предложи замену текущего блюда в плане.")
            return
        }
        viewModelScope.launch {
            _state.value = _state.value.copy(sending = true, actionError = null, infoMessage = null)
            try {
                mealPlans.replaceItem(id)
                _state.value = _state.value.copy(
                    sending = false,
                    infoMessage = "Блюдо заменено в плане. Вернитесь назад, чтобы увидеть новое.",
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
                title = { Text("AI-помощник") },
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
                onSend = { viewModel.send() },
                onAction = viewModel::onSuggestedAction,
                modifier = Modifier
                    .padding(padding)
                    .imePadding()
                    .navigationBarsPadding(),
            )
        }
    }
}

@Composable
fun ChatScreen(
    state: ChatUiState,
    onDraft: (String) -> Unit,
    onSend: () -> Unit,
    onAction: (SuggestedActionDto) -> Unit,
    modifier: Modifier = Modifier,
) {
    val listState = rememberLazyListState()
    LaunchedEffect(state.messages.size, state.sending) {
        if (state.messages.isNotEmpty()) {
            listState.animateScrollToItem(state.messages.lastIndex)
        }
    }
    Column(
        modifier = modifier
            .fillMaxSize()
            .background(FoodAIColors.Background)
            .padding(FoodAIDimens.ScreenPadding),
        verticalArrangement = Arrangement.spacedBy(FoodAIDimens.Space8),
    ) {
        LazyColumn(
            state = listState,
            modifier = Modifier.weight(1f).fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            items(state.messages, key = { it.id }) { message ->
                ChatBubble(
                    message = message,
                    onAction = onAction,
                    actionsEnabled = !state.sending,
                )
            }
        }
        if (state.actionError != null) {
            Text(state.actionError, color = FoodAIColors.Error)
        }
        if (state.infoMessage != null) {
            Text(state.infoMessage, color = FoodAIColors.Primary)
        }
        if (state.disclaimer.isNotBlank()) {
            Text(
                state.disclaimer,
                style = FoodAITypography.bodySmall,
                color = FoodAIColors.TextSecondary,
            )
        }
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.Bottom,
        ) {
            OutlinedTextField(
                value = state.draft,
                onValueChange = onDraft,
                modifier = Modifier.weight(1f),
                placeholder = { Text("Спроси AI…", color = FoodAIColors.TextMuted) },
                enabled = !state.sending,
                maxLines = 4,
                shape = FoodAIShapes.Input,
            )
            Button(
                onClick = onSend,
                enabled = !state.sending && state.draft.isNotBlank(),
                colors = ButtonDefaults.buttonColors(containerColor = FoodAIColors.Primary),
                shape = FoodAIShapes.Button,
            ) {
                Text(if (state.sending) "…" else "→")
            }
        }
    }
}

@Composable
private fun ChatBubble(
    message: ChatMessageDto,
    onAction: (SuggestedActionDto) -> Unit,
    actionsEnabled: Boolean,
) {
    val isUser = message.role == "user"
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start,
    ) {
        Column(
            modifier = Modifier.widthIn(max = 320.dp),
            horizontalAlignment = if (isUser) Alignment.End else Alignment.Start,
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Text(
                if (isUser) "Вы" else "FoodAI",
                style = FoodAITypography.labelMedium,
                color = FoodAIColors.Primary,
            )
            Box(
                modifier = Modifier
                    .background(
                        color = if (isUser) FoodAIColors.Primary else FoodAIColors.PrimarySoft,
                        shape = RoundedCornerShape(20.dp),
                    )
                    .padding(horizontal = 14.dp, vertical = 12.dp),
            ) {
                Text(
                    message.content,
                    color = if (isUser) FoodAIColors.TextOnPrimary else FoodAIColors.TextPrimary,
                    style = FoodAITypography.bodyMedium,
                )
            }
            message.suggestedActions
                .filter { it.type != "none" && it.label.isNotBlank() }
                .forEach { action ->
                    OutlinedButton(
                        onClick = { onAction(action) },
                        enabled = actionsEnabled,
                        shape = FoodAIShapes.Pill,
                        border = androidx.compose.foundation.BorderStroke(1.dp, FoodAIColors.Primary),
                    ) {
                        Text(action.label, color = FoodAIColors.Primary)
                    }
                }
        }
    }
}
