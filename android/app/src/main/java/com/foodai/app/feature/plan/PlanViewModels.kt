package com.foodai.app.feature.plan

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.foodai.app.core.auth.toUiMessage
import com.foodai.app.core.mealplan.MealPlanRepository
import com.foodai.app.core.network.ApiException
import com.foodai.app.core.network.MealPlanDto
import com.foodai.app.core.network.MealPlanItemDto
import com.foodai.app.core.network.ProfileResponse
import com.foodai.app.core.profile.ProfileRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.time.LocalDate
import javax.inject.Inject

data class TodayUiState(
    val loading: Boolean = true,
    val refreshing: Boolean = false,
    val generating: Boolean = false,
    val plan: MealPlanDto? = null,
    val profile: ProfileResponse? = null,
    val error: String? = null,
    val missingPlan: Boolean = false,
    val actionError: String? = null,
    val infoMessage: String? = null,
)

@HiltViewModel
class TodayViewModel @Inject constructor(
    private val mealPlans: MealPlanRepository,
    private val profiles: ProfileRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(TodayUiState())
    val state: StateFlow<TodayUiState> = _state.asStateFlow()

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = _state.value.plan == null, error = null, missingPlan = false)
            try {
                val plan = mealPlans.today(LocalDate.now())
                val profile = runCatching { profiles.getProfile() }.getOrNull()
                _state.value = TodayUiState(loading = false, plan = plan, profile = profile)
            } catch (error: ApiException) {
                val missing = error.code == "meal_plan_not_found" || error.httpStatus == 404
                _state.value = _state.value.copy(
                    loading = false,
                    error = if (missing) {
                        "План питания ещё не создан."
                    } else {
                        error.toUiMessage()
                    },
                    missingPlan = missing,
                )
            } catch (error: Exception) {
                _state.value = _state.value.copy(
                    loading = false,
                    error = error.message ?: "Не удалось загрузить план",
                )
            }
        }
    }

    fun generatePlan() {
        viewModelScope.launch {
            _state.value = _state.value.copy(generating = true, error = null, actionError = null, infoMessage = null)
            try {
                profiles.generateFirstPlan(days = 7, force = true)
                refresh()
            } catch (error: ApiException) {
                _state.value = _state.value.copy(
                    generating = false,
                    error = error.toUiMessage(),
                    missingPlan = error.code == "meal_plan_not_found" || error.httpStatus == 404,
                )
            }
        }
    }

    fun rebuildPlan() {
        viewModelScope.launch {
            _state.value = _state.value.copy(generating = true, actionError = null, infoMessage = null)
            try {
                profiles.regeneratePlan(days = 7)
                refresh()
                _state.value = _state.value.copy(infoMessage = "План на неделю пересобран.")
            } catch (error: ApiException) {
                _state.value = _state.value.copy(
                    generating = false,
                    actionError = error.toUiMessage(),
                )
            }
        }
    }

    fun complete(item: MealPlanItemDto) {
        viewModelScope.launch {
            try {
                mealPlans.completeItem(item.id, completed = !item.isCompleted)
                refresh()
            } catch (error: ApiException) {
                _state.value = _state.value.copy(actionError = error.toUiMessage())
            }
        }
    }

    fun replace(item: MealPlanItemDto) {
        viewModelScope.launch {
            _state.value = _state.value.copy(refreshing = true, actionError = null)
            try {
                mealPlans.replaceItem(item.id)
                refresh()
            } catch (error: ApiException) {
                _state.value = _state.value.copy(
                    refreshing = false,
                    actionError = error.toUiMessage(),
                )
            }
        }
    }
}

data class WeekUiState(
    val loading: Boolean = true,
    val generating: Boolean = false,
    val plan: MealPlanDto? = null,
    val profile: ProfileResponse? = null,
    val selectedDate: String = LocalDate.now().toString(),
    val error: String? = null,
    val missingPlan: Boolean = false,
    val actionError: String? = null,
    val infoMessage: String? = null,
)

@HiltViewModel
class WeekViewModel @Inject constructor(
    private val mealPlans: MealPlanRepository,
    private val profiles: ProfileRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(WeekUiState())
    val state: StateFlow<WeekUiState> = _state.asStateFlow()

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null, missingPlan = false)
            try {
                val plan = mealPlans.week(LocalDate.now())
                val profile = runCatching { profiles.getProfile() }.getOrNull()
                _state.value = WeekUiState(
                    loading = false,
                    plan = plan,
                    profile = profile,
                    selectedDate = _state.value.selectedDate.ifBlank { LocalDate.now().toString() },
                )
            } catch (error: ApiException) {
                val missing = error.code == "meal_plan_not_found" || error.httpStatus == 404
                _state.value = _state.value.copy(
                    loading = false,
                    error = if (missing) "План питания ещё не создан." else error.toUiMessage(),
                    missingPlan = missing,
                )
            } catch (error: Exception) {
                _state.value = _state.value.copy(
                    loading = false,
                    error = error.message ?: "Не удалось загрузить неделю",
                )
            }
        }
    }

    fun generatePlan() {
        viewModelScope.launch {
            _state.value = _state.value.copy(generating = true, error = null, actionError = null)
            try {
                profiles.generateFirstPlan(days = 7, force = true)
                refresh()
            } catch (error: ApiException) {
                _state.value = _state.value.copy(
                    generating = false,
                    error = error.toUiMessage(),
                    missingPlan = error.code == "meal_plan_not_found" || error.httpStatus == 404,
                )
            }
        }
    }

    fun rebuildPlan() {
        viewModelScope.launch {
            _state.value = _state.value.copy(generating = true, actionError = null, infoMessage = null)
            try {
                profiles.regeneratePlan(days = 7)
                refresh()
                _state.value = _state.value.copy(infoMessage = "План на неделю пересобран.")
            } catch (error: ApiException) {
                _state.value = _state.value.copy(
                    generating = false,
                    actionError = error.toUiMessage(),
                )
            }
        }
    }

    fun selectDate(date: String) {
        _state.value = _state.value.copy(selectedDate = date)
    }
}
