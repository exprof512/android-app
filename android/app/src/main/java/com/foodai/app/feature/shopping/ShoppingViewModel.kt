package com.foodai.app.feature.shopping

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.foodai.app.core.auth.toUiMessage
import com.foodai.app.core.mealplan.MealPlanRepository
import com.foodai.app.core.network.ApiException
import com.foodai.app.core.network.ShoppingListDto
import com.foodai.app.core.network.ShoppingListItemDto
import com.foodai.app.core.shopping.ShoppingRepository
import com.foodai.app.core.sync.AppStateBus
import com.foodai.app.core.sync.DomainEvent
import com.foodai.app.core.sync.SelectedDateStore
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ShoppingUiState(
    val loading: Boolean = true,
    val regenerating: Boolean = false,
    val list: ShoppingListDto? = null,
    val mealPlanId: String? = null,
    val excludePantry: Boolean = true,
    val lastUpdatedEpochMs: Long = 0L,
    val error: String? = null,
    val actionError: String? = null,
)

@HiltViewModel
class ShoppingViewModel @Inject constructor(
    private val shopping: ShoppingRepository,
    private val mealPlans: MealPlanRepository,
    private val bus: AppStateBus,
    private val selectedDate: SelectedDateStore,
) : ViewModel() {
    private val _state = MutableStateFlow(ShoppingUiState())
    val state: StateFlow<ShoppingUiState> = _state.asStateFlow()

    init {
        refresh()
        viewModelScope.launch {
            bus.events.collectLatest { event ->
                when (event) {
                    is DomainEvent.PlanChanged,
                    is DomainEvent.ShoppingChanged,
                    -> refresh()
                    else -> Unit
                }
            }
        }
    }

    fun refresh() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = _state.value.list == null, error = null, actionError = null)
            try {
                val plan = mealPlans.week(selectedDate.date.value)
                val list = runCatching { shopping.current(plan.id) }.getOrNull()
                    ?: shopping.generate(plan.id, excludeAvailableProducts = _state.value.excludePantry)
                _state.value = ShoppingUiState(
                    loading = false,
                    list = list,
                    mealPlanId = plan.id,
                    excludePantry = _state.value.excludePantry,
                    lastUpdatedEpochMs = System.currentTimeMillis(),
                )
            } catch (error: ApiException) {
                if (error.code == "meal_plan_not_found" || error.code == "shopping_list_not_found") {
                    _state.value = _state.value.copy(
                        loading = false,
                        list = null,
                        error = "Сначала сгенерируйте план питания — список покупок строится из него.",
                    )
                } else {
                    _state.value = _state.value.copy(
                        loading = false,
                        error = error.toUiMessage(),
                    )
                }
            } catch (error: Exception) {
                _state.value = _state.value.copy(
                    loading = false,
                    error = error.message ?: "Не удалось загрузить список покупок",
                )
            }
        }
    }

    fun setExcludePantry(value: Boolean) {
        _state.value = _state.value.copy(excludePantry = value)
    }

    fun regenerate() {
        val mealPlanId = _state.value.mealPlanId ?: return
        viewModelScope.launch {
            _state.value = _state.value.copy(regenerating = true, actionError = null)
            try {
                val list = shopping.generate(
                    mealPlanId = mealPlanId,
                    excludeAvailableProducts = _state.value.excludePantry,
                )
                _state.value = _state.value.copy(
                    regenerating = false,
                    list = list,
                    error = null,
                    lastUpdatedEpochMs = System.currentTimeMillis(),
                )
                bus.emit(DomainEvent.ShoppingChanged(mealPlanId))
            } catch (error: ApiException) {
                _state.value = _state.value.copy(
                    regenerating = false,
                    actionError = error.toUiMessage(),
                )
            }
        }
    }

    fun clearCompleted() {
        val listId = _state.value.list?.id ?: return
        viewModelScope.launch {
            try {
                val list = shopping.clearCompleted(listId)
                _state.value = _state.value.copy(list = list, actionError = null)
            } catch (error: ApiException) {
                _state.value = _state.value.copy(actionError = error.toUiMessage())
            }
        }
    }

    fun toggleItem(item: ShoppingListItemDto) {
        viewModelScope.launch {
            try {
                shopping.completeItem(item.id, completed = !item.isCompleted)
                val list = _state.value.list ?: return@launch
                _state.value = _state.value.copy(
                    list = list.copy(
                        items = list.items.map {
                            if (it.id == item.id) it.copy(isCompleted = !item.isCompleted) else it
                        },
                    ),
                )
            } catch (error: ApiException) {
                _state.value = _state.value.copy(actionError = error.toUiMessage())
            }
        }
    }
}
