package com.foodai.app.feature.chat

import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
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
import com.foodai.app.core.ai.AiRecommendationRepository
import com.foodai.app.core.ai.aiPayload
import com.foodai.app.core.auth.toUiMessage
import com.foodai.app.core.chat.ChatRepository
import com.foodai.app.core.mealplan.MealPlanRepository
import com.foodai.app.core.network.ApiException
import com.foodai.app.core.network.ChatMessageDto
import com.foodai.app.core.network.ProfileUpdateRequest
import com.foodai.app.core.network.SuggestedActionDto
import com.foodai.app.core.profile.ProfileRepository
import com.foodai.app.core.ui.ErrorPane
import com.foodai.app.core.ui.LoadingPane
import com.foodai.app.core.ui.theme.FoodAIColors
import com.foodai.app.core.ui.theme.FoodAIDimens
import com.foodai.app.core.ui.theme.FoodAIShapes
import com.foodai.app.core.ui.theme.FoodAITypography
import com.foodai.app.feature.ai.AiPreviewSheet
import com.foodai.app.feature.ai.AiPreviewState
import com.foodai.app.feature.ai.RememberDislikeDialog
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonPrimitive
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
    val aiPreview: AiPreviewState = AiPreviewState.Idle,
    val pendingDislike: String? = null,
)

private val quickChips = listOf(
    "food_suggestion" to "Что съесть",
    "replace_meal_item" to "Заменить",
    "make_cheaper" to "Дешевле",
    "pantry_cook" to "Из продуктов",
    "more_protein" to "Больше белка",
    "make_faster" to "Быстрее",
)

@HiltViewModel
class ChatViewModel @Inject constructor(
    savedStateHandle: SavedStateHandle,
    private val chat: ChatRepository,
    private val mealPlans: MealPlanRepository,
    private val ai: AiRecommendationRepository,
    private val profiles: ProfileRepository,
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
            "open_shopping_list" -> {
                _state.value = _state.value.copy(
                    infoMessage = "Откройте вкладку Shopping, чтобы увидеть список покупок.",
                )
            }
            "food_suggestion" -> requestRecommendations(intent = "food_suggestion")
            "pantry_cook" -> requestRecommendations(intent = "pantry_cook")
            "adapt_day" -> requestAdaptDay()
            "make_cheaper" -> requestVariantOrRecommend("budget", "Сделай дешевле")
            "make_faster" -> requestVariantOrRecommend("quick", "Сделай быстрее")
            "more_protein" -> requestVariantOrRecommend("high_protein", "Больше белка")
            "replace_meal_item" -> replaceMeal()
            "remember_dislike" -> {
                val name = payloadString(action, "name")
                    ?: payloadString(action, "food_name")
                    ?: action.label.removePrefix("Не люблю ").ifBlank { null }
                if (name.isNullOrBlank()) {
                    send(prefilled = "Запомни, что мне это не нравится.")
                } else {
                    _state.value = _state.value.copy(pendingDislike = name)
                }
            }
            else -> send(prefilled = action.label)
        }
    }

    fun onQuickChip(type: String) {
        onSuggestedAction(SuggestedActionDto(type = type, label = type))
    }

    fun dismissAi() {
        _state.value = _state.value.copy(aiPreview = AiPreviewState.Idle)
    }

    fun dismissDislike() {
        _state.value = _state.value.copy(pendingDislike = null)
    }

    fun confirmDislike() {
        val name = _state.value.pendingDislike ?: return
        viewModelScope.launch {
            _state.value = _state.value.copy(pendingDislike = null, sending = true, actionError = null)
            try {
                val profile = profiles.refreshProfile()
                val p = profile.profile
                if (p.sex != null && p.ageYears != null && p.heightCm != null &&
                    p.currentWeightKg != null && p.activityLevel != null &&
                    p.mealsPerDay != null && profile.goal != null
                ) {
                    val disliked = (profile.preferences.dislikedFoods + name)
                        .map { it.trim() }
                        .filter { it.isNotEmpty() }
                        .distinct()
                    profiles.updateProfile(
                        ProfileUpdateRequest(
                            sex = p.sex,
                            ageYears = p.ageYears,
                            heightCm = p.heightCm,
                            currentWeightKg = p.currentWeightKg,
                            activityLevel = p.activityLevel,
                            goalType = profile.goal.goalType,
                            mealsPerDay = p.mealsPerDay,
                            targetWeightKg = profile.goal.targetWeightKg,
                            desiredWeeklyChangeKg = profile.goal.desiredWeeklyChangeKg,
                            dailyCalorieMode = p.dailyCalorieMode ?: "auto",
                            dailyCalorieValue = p.dailyCalorieValue,
                            groceryBudgetWeekly = p.groceryBudgetWeekly,
                            currency = p.currency ?: "RUB",
                            maxCookTimeMinutes = p.maxCookTimeMinutes,
                            householdSize = p.householdSize ?: 1,
                            timezone = p.timezone,
                            likedFoods = profile.preferences.likedFoods,
                            dislikedFoods = disliked,
                            excludedFoods = profile.restrictions.excludedFoods,
                            allergies = profile.restrictions.allergies,
                            availableProducts = profile.availableProducts,
                        ),
                    )
                } else {
                    // Fallback: two-step AI apply when profile incomplete for PUT.
                    val preview = ai.recommend(intent = "food_suggestion")
                    ai.apply(
                        recommendationId = preview.recommendationId,
                        actionType = "remember_dislike",
                        payload = aiPayload("name" to name),
                    )
                }
                _state.value = _state.value.copy(
                    sending = false,
                    infoMessage = "Запомнили: не любите «$name»",
                )
            } catch (error: ApiException) {
                _state.value = _state.value.copy(
                    sending = false,
                    actionError = error.toUiMessage(),
                )
            }
        }
    }

    fun selectAiCandidate(index: Int) {
        val preview = _state.value.aiPreview as? AiPreviewState.Recommendations ?: return
        _state.value = _state.value.copy(aiPreview = preview.copy(selectedIndex = index))
    }

    fun confirmAiRecommendation() {
        val preview = _state.value.aiPreview as? AiPreviewState.Recommendations ?: return
        val candidate = preview.candidates.getOrNull(preview.selectedIndex) ?: return
        val id = candidate.recipeId ?: return
        viewModelScope.launch {
            _state.value = _state.value.copy(aiPreview = preview.copy(applying = true))
            try {
                ai.apply(
                    recommendationId = preview.recommendationId,
                    actionType = "create_nutrition_log",
                    payload = aiPayload("recipe_id" to id, "meal_type" to "snack"),
                )
                _state.value = _state.value.copy(
                    aiPreview = AiPreviewState.Idle,
                    infoMessage = "Добавлено: ${candidate.name}",
                )
            } catch (error: ApiException) {
                _state.value = _state.value.copy(
                    aiPreview = preview.copy(applying = false),
                    actionError = error.toUiMessage(),
                )
            }
        }
    }

    fun confirmAdaptDay() {
        val preview = _state.value.aiPreview as? AiPreviewState.AdaptDay ?: return
        viewModelScope.launch {
            _state.value = _state.value.copy(aiPreview = preview.copy(applying = true))
            try {
                val plan = runCatching { mealPlans.today() }.getOrNull()
                val day = preview.preview.onDate
                if (plan != null) {
                    for (slot in preview.preview.replacements) {
                        val recipeId = slot.candidate?.recipeId ?: continue
                        val item = plan.items.firstOrNull {
                            it.date.take(10) == day.take(10) &&
                                it.mealType == slot.mealType &&
                                !it.isCompleted
                        } ?: continue
                        ai.apply(
                            recommendationId = preview.preview.recommendationId,
                            actionType = "replace_meal_item",
                            payload = aiPayload(
                                "meal_plan_item_id" to item.id,
                                "recipe_id" to recipeId,
                            ),
                        )
                    }
                }
                _state.value = _state.value.copy(
                    aiPreview = AiPreviewState.Idle,
                    infoMessage = "День адаптирован",
                )
            } catch (error: ApiException) {
                _state.value = _state.value.copy(
                    aiPreview = preview.copy(applying = false),
                    actionError = error.toUiMessage(),
                )
            }
        }
    }

    fun confirmVariant() {
        val preview = _state.value.aiPreview as? AiPreviewState.Variant ?: return
        val candidate = preview.preview.candidate ?: return
        val newId = candidate.recipeId ?: return
        viewModelScope.launch {
            _state.value = _state.value.copy(aiPreview = preview.copy(applying = true))
            try {
                val localItem = preview.mealPlanItemId ?: itemId
                if (localItem != null) {
                    ai.apply(
                        recommendationId = preview.preview.recommendationId,
                        actionType = "replace_meal_item",
                        payload = aiPayload(
                            "meal_plan_item_id" to localItem,
                            "recipe_id" to newId,
                        ),
                    )
                } else {
                    ai.apply(
                        recommendationId = preview.preview.recommendationId,
                        actionType = "create_nutrition_log",
                        payload = aiPayload("recipe_id" to newId, "meal_type" to "snack"),
                    )
                }
                _state.value = _state.value.copy(
                    aiPreview = AiPreviewState.Idle,
                    infoMessage = "Вариант применён: ${candidate.name}",
                )
            } catch (error: ApiException) {
                _state.value = _state.value.copy(
                    aiPreview = preview.copy(applying = false),
                    actionError = error.toUiMessage(),
                )
            }
        }
    }

    private fun requestRecommendations(intent: String) {
        viewModelScope.launch {
            _state.value = _state.value.copy(aiPreview = AiPreviewState.Loading, actionError = null)
            try {
                val out = ai.recommend(intent = intent)
                if (out.candidates.isEmpty()) {
                    _state.value = _state.value.copy(
                        aiPreview = AiPreviewState.Empty("Нет подходящих вариантов."),
                    )
                    return@launch
                }
                _state.value = _state.value.copy(
                    aiPreview = AiPreviewState.Recommendations(
                        recommendationId = out.recommendationId,
                        candidates = out.candidates,
                        warnings = out.warnings,
                        title = if (intent == "pantry_cook") "Из продуктов" else "Что съесть",
                    ),
                )
            } catch (error: ApiException) {
                _state.value = _state.value.copy(
                    aiPreview = AiPreviewState.Error(error.toUiMessage()),
                )
            }
        }
    }

    private fun requestAdaptDay() {
        viewModelScope.launch {
            _state.value = _state.value.copy(aiPreview = AiPreviewState.Loading, actionError = null)
            try {
                val out = ai.adaptDay()
                if (out.replacements.isEmpty()) {
                    _state.value = _state.value.copy(
                        aiPreview = AiPreviewState.Empty(
                            out.warnings.firstOrNull() ?: "Нечего адаптировать.",
                        ),
                    )
                    return@launch
                }
                _state.value = _state.value.copy(aiPreview = AiPreviewState.AdaptDay(out))
            } catch (error: ApiException) {
                _state.value = _state.value.copy(
                    aiPreview = AiPreviewState.Error(error.toUiMessage()),
                )
            }
        }
    }

    private fun requestVariantOrRecommend(variant: String, prompt: String) {
        val id = recipeId
        if (id.isNullOrBlank()) {
            send(prefilled = prompt)
            return
        }
        viewModelScope.launch {
            _state.value = _state.value.copy(aiPreview = AiPreviewState.Loading, actionError = null)
            try {
                val out = ai.recipeVariant(id, variant)
                if (out.candidate == null) {
                    _state.value = _state.value.copy(
                        aiPreview = AiPreviewState.Empty("Вариант не найден."),
                    )
                    return@launch
                }
                _state.value = _state.value.copy(
                    aiPreview = AiPreviewState.Variant(out, mealPlanItemId = itemId),
                )
            } catch (error: ApiException) {
                _state.value = _state.value.copy(
                    aiPreview = AiPreviewState.Error(error.toUiMessage()),
                )
            }
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

    private fun payloadString(action: SuggestedActionDto, key: String): String? {
        val element = action.payload ?: return null
        return when (element) {
            is JsonObject -> element[key]?.jsonPrimitive?.contentOrNull
            is JsonPrimitive -> if (key == "name") element.contentOrNull else null
            else -> null
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
                onQuickChip = viewModel::onQuickChip,
                onDismissAi = viewModel::dismissAi,
                onSelectAiCandidate = viewModel::selectAiCandidate,
                onConfirmAiRecommendation = viewModel::confirmAiRecommendation,
                onConfirmAdaptDay = viewModel::confirmAdaptDay,
                onConfirmVariant = viewModel::confirmVariant,
                onDismissDislike = viewModel::dismissDislike,
                onConfirmDislike = viewModel::confirmDislike,
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
    onQuickChip: (String) -> Unit = {},
    onDismissAi: () -> Unit = {},
    onSelectAiCandidate: (Int) -> Unit = {},
    onConfirmAiRecommendation: () -> Unit = {},
    onConfirmAdaptDay: () -> Unit = {},
    onConfirmVariant: () -> Unit = {},
    onDismissDislike: () -> Unit = {},
    onConfirmDislike: () -> Unit = {},
    modifier: Modifier = Modifier,
) {
    val listState = rememberLazyListState()
    LaunchedEffect(state.messages.size, state.sending) {
        if (state.messages.isNotEmpty()) {
            listState.animateScrollToItem(state.messages.lastIndex)
        }
    }

    if (state.aiPreview !is AiPreviewState.Idle) {
        AiPreviewSheet(
            state = state.aiPreview,
            onDismiss = onDismissAi,
            onSelectCandidate = onSelectAiCandidate,
            onConfirmRecommendations = onConfirmAiRecommendation,
            onConfirmAdaptDay = onConfirmAdaptDay,
            onConfirmVariant = onConfirmVariant,
        )
    }
    state.pendingDislike?.let { name ->
        RememberDislikeDialog(
            foodName = name,
            onDismiss = onDismissDislike,
            onConfirm = onConfirmDislike,
        )
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
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            quickChips.forEach { (type, label) ->
                FilterChip(
                    selected = false,
                    onClick = { onQuickChip(type) },
                    enabled = !state.sending,
                    label = { Text(label) },
                )
            }
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
