package com.foodai.app.feature.recipe

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import com.foodai.app.core.auth.toUiMessage
import com.foodai.app.core.mealplan.MealPlanRepository
import com.foodai.app.core.network.ApiException
import com.foodai.app.core.network.DishCardDto
import com.foodai.app.core.ui.LoadingPane
import com.foodai.app.core.ui.components.FoodAIEmptyState
import com.foodai.app.core.ui.components.FoodAISearchField
import com.foodai.app.core.ui.theme.FoodAIColors
import com.foodai.app.core.ui.theme.FoodAIDimens
import com.foodai.app.core.ui.theme.FoodAITypography
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class FavoritesUiState(
    val loading: Boolean = true,
    val items: List<DishCardDto> = emptyList(),
    val error: String? = null,
)

data class SearchUiState(
    val query: String = "",
    val loading: Boolean = false,
    val items: List<DishCardDto> = emptyList(),
    val error: String? = null,
)

@HiltViewModel
class FavoritesViewModel @Inject constructor(
    private val mealPlans: MealPlanRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(FavoritesUiState())
    val state: StateFlow<FavoritesUiState> = _state.asStateFlow()

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null)
            try {
                val items = mealPlans.listFavorites()
                _state.value = FavoritesUiState(loading = false, items = items)
            } catch (error: ApiException) {
                _state.value = FavoritesUiState(loading = false, error = error.toUiMessage())
            } catch (error: Exception) {
                _state.value = FavoritesUiState(
                    loading = false,
                    error = error.message ?: "Не удалось загрузить избранное",
                )
            }
        }
    }
}

@HiltViewModel
class RecipeSearchViewModel @Inject constructor(
    private val mealPlans: MealPlanRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(SearchUiState())
    val state: StateFlow<SearchUiState> = _state.asStateFlow()
    private var searchJob: Job? = null

    fun onQuery(query: String) {
        _state.value = _state.value.copy(query = query)
        searchJob?.cancel()
        if (query.isBlank()) {
            _state.value = _state.value.copy(items = emptyList(), loading = false, error = null)
            return
        }
        searchJob = viewModelScope.launch {
            delay(350)
            _state.value = _state.value.copy(loading = true, error = null)
            try {
                val items = mealPlans.searchRecipes(query.trim())
                _state.value = _state.value.copy(loading = false, items = items)
            } catch (error: ApiException) {
                _state.value = _state.value.copy(loading = false, error = error.toUiMessage())
            } catch (error: Exception) {
                _state.value = _state.value.copy(
                    loading = false,
                    error = error.message ?: "Ошибка поиска",
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FavoritesRoute(
    onBack: () -> Unit,
    onOpenRecipe: (String) -> Unit,
    viewModel: FavoritesViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Избранное") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Назад")
                    }
                },
            )
        },
        containerColor = FoodAIColors.Background,
    ) { padding ->
        when {
            state.loading -> LoadingPane("Загружаем избранное…")
            state.error != null && state.items.isEmpty() -> Column(
                modifier = Modifier.padding(padding).padding(FoodAIDimens.ScreenPadding),
            ) {
                Text(state.error ?: "Ошибка", color = FoodAIColors.Error)
            }
            state.items.isEmpty() -> Column(
                modifier = Modifier.padding(padding).padding(FoodAIDimens.ScreenPadding),
            ) {
                FoodAIEmptyState(
                    title = "Пока пусто",
                    subtitle = "Добавляй рецепты в избранное с карточки блюда.",
                )
            }
            else -> LazyColumn(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .background(FoodAIColors.Background),
                contentPadding = PaddingValues(FoodAIDimens.ScreenPadding),
                verticalArrangement = Arrangement.spacedBy(FoodAIDimens.Space8),
            ) {
                items(state.items, key = { it.id }) { recipe ->
                    RecipeListRow(recipe = recipe, onClick = { onOpenRecipe(recipe.id) })
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RecipeSearchRoute(
    onBack: () -> Unit,
    onOpenRecipe: (String) -> Unit,
    viewModel: RecipeSearchViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Поиск рецептов") },
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
                .padding(FoodAIDimens.ScreenPadding),
            verticalArrangement = Arrangement.spacedBy(FoodAIDimens.Space12),
        ) {
            FoodAISearchField(
                value = state.query,
                onValueChange = viewModel::onQuery,
                placeholder = "Например: курица, овсянка…",
            )
            when {
                state.loading -> Text("Ищем…", color = FoodAIColors.TextSecondary)
                state.error != null -> Text(state.error ?: "", color = FoodAIColors.Error)
                state.query.isNotBlank() && state.items.isEmpty() -> Text(
                    "Ничего не найдено",
                    color = FoodAIColors.TextSecondary,
                )
                else -> LazyColumn(verticalArrangement = Arrangement.spacedBy(FoodAIDimens.Space8)) {
                    items(state.items, key = { it.id }) { recipe ->
                        RecipeListRow(recipe = recipe, onClick = { onOpenRecipe(recipe.id) })
                    }
                }
            }
        }
    }
}

@Composable
private fun RecipeListRow(recipe: DishCardDto, onClick: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .background(FoodAIColors.Surface)
            .padding(FoodAIDimens.Space12),
    ) {
        Text(recipe.name, style = FoodAITypography.titleMedium)
        Text(
            "${recipe.nutritionPerServing.caloriesKcal} ккал · ${recipe.cookTimeMinutes} мин" +
                " · Б ${recipe.nutritionPerServing.proteinG.toInt()} г",
            style = FoodAITypography.bodySmall,
            color = FoodAIColors.TextSecondary,
        )
        Spacer(Modifier.height(FoodAIDimens.Space4))
    }
}
