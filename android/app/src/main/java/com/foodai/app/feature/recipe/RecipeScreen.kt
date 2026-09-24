package com.foodai.app.feature.recipe

import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
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
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.outlined.FavoriteBorder
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import com.foodai.app.core.ai.AiRecommendationRepository
import com.foodai.app.core.ai.aiPayload
import com.foodai.app.core.auth.toUiMessage
import com.foodai.app.core.mealplan.MealPlanRepository
import com.foodai.app.core.network.ApiException
import com.foodai.app.core.network.DishCardDto
import com.foodai.app.core.network.RecipeImageDto
import com.foodai.app.core.ui.ErrorPane
import com.foodai.app.core.ui.LoadingPane
import com.foodai.app.core.ui.RecipeImagePane
import com.foodai.app.core.ui.components.FoodAIOutlinedButton
import com.foodai.app.core.ui.components.FoodAIPrimaryButton
import com.foodai.app.core.ui.theme.FoodAIColors
import com.foodai.app.core.ui.theme.FoodAIDimens
import com.foodai.app.core.ui.theme.FoodAITypography
import com.foodai.app.feature.ai.AiPreviewSheet
import com.foodai.app.feature.ai.AiPreviewState
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import javax.inject.Inject

data class RecipeUiState(
    val loading: Boolean = true,
    val recipe: DishCardDto? = null,
    val image: RecipeImageDto? = null,
    val error: String? = null,
    val actionError: String? = null,
    val infoMessage: String? = null,
    val replaced: Boolean = false,
    val aiPreview: AiPreviewState = AiPreviewState.Idle,
    val substituteIngredient: String? = null,
)

@HiltViewModel
class RecipeViewModel @Inject constructor(
    savedStateHandle: SavedStateHandle,
    private val mealPlans: MealPlanRepository,
    private val ai: AiRecommendationRepository,
) : ViewModel() {
    private val recipeId: String = checkNotNull(savedStateHandle["recipeId"])
    private val itemId: String? = savedStateHandle["itemId"]

    private val _state = MutableStateFlow(RecipeUiState())
    val state: StateFlow<RecipeUiState> = _state.asStateFlow()

    fun planItemId(): String? = itemId

    init {
        refresh()
        pollImage()
    }

    fun refresh() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null)
            try {
                val recipe = mealPlans.recipe(recipeId)
                val image = runCatching { mealPlans.recipeImage(recipeId) }.getOrNull()
                _state.value = _state.value.copy(
                    loading = false,
                    recipe = recipe,
                    image = image,
                    error = null,
                )
            } catch (error: ApiException) {
                _state.value = _state.value.copy(loading = false, error = error.toUiMessage())
            } catch (error: Exception) {
                _state.value = _state.value.copy(
                    loading = false,
                    error = error.message ?: "Не удалось загрузить рецепт",
                )
            }
        }
    }

    private fun pollImage() {
        viewModelScope.launch {
            while (isActive) {
                val current = _state.value.image?.status
                if (current == "ready" || current == "failed") break
                delay(4_000)
                val image = runCatching { mealPlans.recipeImage(recipeId) }.getOrNull() ?: continue
                _state.value = _state.value.copy(image = image)
                if (image.status == "ready" || image.status == "failed") break
            }
        }
    }

    fun toggleFavorite() {
        val recipe = _state.value.recipe ?: return
        viewModelScope.launch {
            try {
                mealPlans.setFavorite(recipe.id, !recipe.isFavorite)
                _state.value = _state.value.copy(
                    recipe = recipe.copy(isFavorite = !recipe.isFavorite),
                )
            } catch (error: ApiException) {
                _state.value = _state.value.copy(actionError = error.toUiMessage())
            }
        }
    }

    fun complete() {
        val id = itemId ?: return
        viewModelScope.launch {
            try {
                mealPlans.completeItem(id, completed = true)
                refresh()
            } catch (error: ApiException) {
                _state.value = _state.value.copy(actionError = error.toUiMessage())
            }
        }
    }

    fun replace() {
        val id = itemId ?: return
        viewModelScope.launch {
            try {
                mealPlans.replaceItem(id)
                _state.value = _state.value.copy(replaced = true)
            } catch (error: ApiException) {
                _state.value = _state.value.copy(actionError = error.toUiMessage())
            }
        }
    }

    fun dismissAi() {
        _state.value = _state.value.copy(aiPreview = AiPreviewState.Idle, substituteIngredient = null)
    }

    fun requestVariant(variant: String) {
        viewModelScope.launch {
            _state.value = _state.value.copy(aiPreview = AiPreviewState.Loading, actionError = null)
            try {
                val out = ai.recipeVariant(recipeId, variant)
                if (out.candidate == null) {
                    _state.value = _state.value.copy(
                        aiPreview = AiPreviewState.Empty(
                            out.warnings.firstOrNull() ?: "Вариант не найден.",
                        ),
                    )
                    return@launch
                }
                _state.value = _state.value.copy(
                    aiPreview = AiPreviewState.Variant(
                        preview = out,
                        mealPlanItemId = itemId,
                    ),
                )
            } catch (error: ApiException) {
                _state.value = _state.value.copy(
                    aiPreview = AiPreviewState.Error(error.toUiMessage()),
                )
            }
        }
    }

    fun confirmVariant() {
        val preview = _state.value.aiPreview as? AiPreviewState.Variant ?: return
        val candidate = preview.preview.candidate ?: return
        val newRecipeId = candidate.recipeId ?: return
        viewModelScope.launch {
            _state.value = _state.value.copy(aiPreview = preview.copy(applying = true))
            try {
                val itemIdLocal = preview.mealPlanItemId
                if (itemIdLocal != null) {
                    ai.apply(
                        recommendationId = preview.preview.recommendationId,
                        actionType = "replace_meal_item",
                        payload = aiPayload(
                            "meal_plan_item_id" to itemIdLocal,
                            "recipe_id" to newRecipeId,
                        ),
                    )
                    _state.value = _state.value.copy(
                        aiPreview = AiPreviewState.Idle,
                        replaced = true,
                        infoMessage = "Рецепт заменён в плане",
                    )
                } else {
                    ai.apply(
                        recommendationId = preview.preview.recommendationId,
                        actionType = "create_nutrition_log",
                        payload = aiPayload(
                            "recipe_id" to newRecipeId,
                            "meal_type" to "snack",
                        ),
                    )
                    _state.value = _state.value.copy(
                        aiPreview = AiPreviewState.Idle,
                        infoMessage = "Вариант добавлен в дневник",
                    )
                }
            } catch (error: ApiException) {
                _state.value = _state.value.copy(
                    aiPreview = preview.copy(applying = false),
                    actionError = error.toUiMessage(),
                )
            }
        }
    }

    fun requestSubstitution(ingredientName: String) {
        viewModelScope.launch {
            _state.value = _state.value.copy(
                aiPreview = AiPreviewState.Loading,
                substituteIngredient = ingredientName,
                actionError = null,
            )
            try {
                val out = ai.ingredientSubstitution(recipeId, ingredientName)
                _state.value = _state.value.copy(
                    aiPreview = AiPreviewState.Substitution(out),
                )
            } catch (error: ApiException) {
                _state.value = _state.value.copy(
                    aiPreview = AiPreviewState.Error(error.toUiMessage()),
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RecipeRoute(
    onBack: () -> Unit,
    onAskAi: (recipeId: String, itemId: String?) -> Unit = { _, _ -> },
    viewModel: RecipeViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    LaunchedEffect(state.replaced) {
        if (state.replaced) onBack()
    }
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(state.recipe?.name ?: "Рецепт") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Назад")
                    }
                },
                actions = {
                    IconButton(onClick = viewModel::toggleFavorite) {
                        val fav = state.recipe?.isFavorite == true
                        Icon(
                            if (fav) Icons.Filled.Favorite else Icons.Outlined.FavoriteBorder,
                            contentDescription = "Избранное",
                        )
                    }
                },
            )
        },
    ) { padding ->
        when {
            state.loading -> LoadingPane(modifier = Modifier.padding(padding))
            state.error != null -> ErrorPane(
                message = state.error ?: "Ошибка",
                onRetry = viewModel::refresh,
                modifier = Modifier.padding(padding),
            )
            state.recipe != null -> RecipeScreen(
                state = state,
                onComplete = viewModel::complete,
                onReplace = viewModel::replace,
                onAskAi = {
                    state.recipe?.id?.let { id -> onAskAi(id, viewModel.planItemId()) }
                },
                onVariant = viewModel::requestVariant,
                onSubstitute = viewModel::requestSubstitution,
                onDismissAi = viewModel::dismissAi,
                onConfirmVariant = viewModel::confirmVariant,
                modifier = Modifier.padding(padding),
            )
        }
    }
}

@Composable
fun RecipeScreen(
    state: RecipeUiState,
    onComplete: () -> Unit,
    onReplace: () -> Unit,
    onAskAi: () -> Unit = {},
    onVariant: (String) -> Unit = {},
    onSubstitute: (String) -> Unit = {},
    onDismissAi: () -> Unit = {},
    onConfirmVariant: () -> Unit = {},
    modifier: Modifier = Modifier,
) {
    val recipe = state.recipe ?: return

    if (state.aiPreview !is AiPreviewState.Idle) {
        AiPreviewSheet(
            state = state.aiPreview,
            onDismiss = onDismissAi,
            onConfirmVariant = onConfirmVariant,
        )
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(FoodAIColors.Background)
            .verticalScroll(rememberScrollState())
            .padding(FoodAIDimens.ScreenPadding),
        verticalArrangement = Arrangement.spacedBy(FoodAIDimens.Space16),
    ) {
        RecipeImagePane(
            image = state.image,
            contentDescription = recipe.name,
            useFull = true,
        )
        Text(recipe.name, style = FoodAITypography.headlineMedium)
        val n = recipe.nutritionPerServing
        Text(
            "${n.caloriesKcal} ккал · Б ${n.proteinG} / Ж ${n.fatG} / У ${n.carbohydrateG}",
            style = FoodAITypography.titleMedium,
        )
        Text(
            "${recipe.cookTimeMinutes} мин · ${recipe.estimatedCostPerServing.amount} ${recipe.estimatedCostPerServing.currency}",
            style = FoodAITypography.bodyMedium,
            color = FoodAIColors.TextSecondary,
        )
        if (state.actionError != null) {
            Text(state.actionError, color = FoodAIColors.Error)
        }
        if (state.infoMessage != null) {
            Text(state.infoMessage, color = FoodAIColors.Primary)
        }
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(FoodAIDimens.Space8),
        ) {
            FoodAIOutlinedButton(
                label = "Заменить",
                onClick = onReplace,
                modifier = Modifier.weight(1f),
            )
            FoodAIPrimaryButton(
                label = "Съедено",
                onClick = onComplete,
                showArrow = false,
                modifier = Modifier.weight(1f),
            )
        }
        FoodAIOutlinedButton(label = "Спросить AI", onClick = onAskAi)

        Text("Быстрые варианты", style = FoodAITypography.titleMedium)
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(FoodAIDimens.Space8),
        ) {
            listOf(
                "high_protein" to "Больше белка",
                "budget" to "Дешевле",
                "quick" to "Быстрее",
                "pantry" to "Из продуктов",
            ).forEach { (variant, label) ->
                FilterChip(
                    selected = false,
                    onClick = { onVariant(variant) },
                    label = { Text(label) },
                )
            }
        }

        Text("Ингредиенты", style = FoodAITypography.titleLarge)
        recipe.ingredients.forEach { ing ->
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text("• ${ing.name} — ${ing.grams} г", style = FoodAITypography.bodyMedium)
                androidx.compose.material3.TextButton(
                    onClick = { onSubstitute(ing.name) },
                ) {
                    Text("Заменить", color = FoodAIColors.Primary)
                }
            }
        }
        Spacer(Modifier.height(FoodAIDimens.Space8))
        Text("Шаги", style = FoodAITypography.titleLarge)
        recipe.steps.forEachIndexed { index, step ->
            Text("${index + 1}. $step", style = FoodAITypography.bodyMedium)
        }
        Spacer(Modifier.height(FoodAIDimens.Space24))
    }
}
