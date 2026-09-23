package com.foodai.app.feature.plan

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.foodai.app.core.auth.AuthRepository
import com.foodai.app.core.auth.toUiMessage
import com.foodai.app.core.mealplan.MealPlanRepository
import com.foodai.app.core.metrics.DailyMetrics
import com.foodai.app.core.metrics.DailyMetricsStore
import com.foodai.app.core.network.ApiException
import com.foodai.app.core.network.MealPlanDto
import com.foodai.app.core.network.MealPlanItemDto
import com.foodai.app.core.network.ProfileResponse
import com.foodai.app.core.profile.ProfileRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch
import java.time.LocalDate
import javax.inject.Inject

data class TodayUiState(
    val loading: Boolean = true,
    val refreshing: Boolean = false,
    val generating: Boolean = false,
    val plan: MealPlanDto? = null,
    val profile: ProfileResponse? = null,
    val metrics: DailyMetrics = DailyMetrics(),
    val nutritionLogs: List<com.foodai.app.core.network.NutritionLogDto> = emptyList(),
    val error: String? = null,
    val missingPlan: Boolean = false,
    val actionError: String? = null,
    val infoMessage: String? = null,
)

@HiltViewModel
class TodayViewModel @Inject constructor(
    private val mealPlans: MealPlanRepository,
    private val profiles: ProfileRepository,
    private val auth: AuthRepository,
    private val metricsStore: DailyMetricsStore,
    private val nutritionApi: com.foodai.app.core.network.NutritionApi,
) : ViewModel() {
    private val _state = MutableStateFlow(TodayUiState())
    val state: StateFlow<TodayUiState> = _state.asStateFlow()
    private var stepsJob: Job? = null

    init {
        refresh()
        observeSteps()
    }

    private fun userId(): String = auth.currentUser()?.id ?: "anon"

    private fun observeSteps() {
        stepsJob?.cancel()
        val uid = userId()
        val snapshot = metricsStore.metrics(uid)
        _state.value = _state.value.copy(metrics = _state.value.metrics.copy(
            steps = snapshot.steps,
            stepsAvailable = snapshot.stepsAvailable,
            stepsPermissionNeeded = snapshot.stepsPermissionNeeded,
            waterMl = snapshot.waterMl,
            waterGoalMl = snapshot.waterGoalMl,
            stepsGoal = snapshot.stepsGoal,
        ))
        if (!snapshot.stepsAvailable) return
        stepsJob = viewModelScope.launch {
            metricsStore.observeSteps(uid).collectLatest { steps ->
                _state.value = _state.value.copy(
                    metrics = _state.value.metrics.copy(
                        steps = steps,
                        stepsAvailable = true,
                        stepsPermissionNeeded = false,
                    ),
                )
            }
        }
    }

    /** Call after ACTIVITY_RECOGNITION dialog — sensor flow only starts when granted. */
    fun onStepsPermissionResult(granted: Boolean) {
        _state.value = _state.value.copy(metrics = metricsStore.metrics(userId()))
        if (granted) observeSteps()
    }

    fun refresh() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = _state.value.plan == null, error = null, missingPlan = false)
            try {
                val plan = mealPlans.today(LocalDate.now())
                val profile = runCatching { profiles.getProfile() }.getOrNull()
                val metrics = metricsStore.metrics(userId())
                val logs = runCatching {
                    nutritionApi.listLogs(LocalDate.now().toString())
                }.getOrDefault(emptyList())
                _state.value = TodayUiState(
                    loading = false,
                    plan = plan,
                    profile = profile,
                    metrics = metrics,
                    nutritionLogs = logs,
                )
                observeSteps()
            } catch (error: ApiException) {
                val missing = error.code == "meal_plan_not_found" || error.httpStatus == 404
                _state.value = _state.value.copy(
                    loading = false,
                    metrics = metricsStore.metrics(userId()),
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

    fun addWater(deltaMl: Int = 250) {
        val metrics = metricsStore.addWater(userId(), deltaMl)
        _state.value = _state.value.copy(metrics = metrics)
    }

    fun addManualSnack(description: String, calories: Int) {
        viewModelScope.launch {
            try {
                nutritionApi.createLog(
                    com.foodai.app.core.network.NutritionLogCreateRequest(
                        loggedOn = LocalDate.now().toString(),
                        mealType = "snack",
                        source = "manual",
                        description = description,
                        caloriesKcal = calories,
                        proteinG = 0.0,
                        fatG = 0.0,
                        carbohydrateG = 0.0,
                    ),
                )
                refresh()
            } catch (error: ApiException) {
                _state.value = _state.value.copy(actionError = error.toUiMessage())
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
    val weekDates: List<String> = emptyList(),
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
                val dates = datesBetween(plan.startDate, plan.endDate)
                val selected = when {
                    dates.contains(_state.value.selectedDate) -> _state.value.selectedDate
                    dates.contains(LocalDate.now().toString()) -> LocalDate.now().toString()
                    else -> dates.firstOrNull().orEmpty()
                }
                _state.value = WeekUiState(
                    loading = false,
                    plan = plan,
                    profile = profile,
                    selectedDate = selected,
                    weekDates = dates,
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

    private fun datesBetween(start: String, end: String): List<String> {
        return runCatching {
            val from = LocalDate.parse(start)
            val to = LocalDate.parse(end)
            generateSequence(from) { it.plusDays(1) }
                .takeWhile { !it.isAfter(to) }
                .map { it.toString() }
                .toList()
        }.getOrDefault(emptyList())
    }
}
