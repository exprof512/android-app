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
import com.foodai.app.core.network.NutritionApi
import com.foodai.app.core.network.NutritionLogCreateRequest
import com.foodai.app.core.network.NutritionLogDto
import com.foodai.app.core.network.ProfileResponse
import com.foodai.app.core.profile.ProfileRepository
import com.foodai.app.core.sync.AppStateBus
import com.foodai.app.core.sync.DomainEvent
import com.foodai.app.core.sync.SelectedDateStore
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
    val nutritionLogs: List<NutritionLogDto> = emptyList(),
    val selectedDate: String = LocalDate.now().toString(),
    val lastUpdatedEpochMs: Long = 0L,
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
    private val nutritionApi: NutritionApi,
    private val bus: AppStateBus,
    private val selectedDate: SelectedDateStore,
) : ViewModel() {
    private val _state = MutableStateFlow(TodayUiState())
    val state: StateFlow<TodayUiState> = _state.asStateFlow()
    private var stepsJob: Job? = null

    init {
        viewModelScope.launch {
            selectedDate.date.collectLatest { date ->
                _state.value = _state.value.copy(selectedDate = date.toString())
                refresh(date)
            }
        }
        viewModelScope.launch {
            bus.events.collectLatest { event ->
                when (event) {
                    is DomainEvent.PlanChanged,
                    is DomainEvent.WeightChanged,
                    is DomainEvent.ProfileChanged,
                    is DomainEvent.NutritionLogChanged,
                    -> refresh(selectedDate.date.value)
                    else -> Unit
                }
            }
        }
        observeSteps()
    }

    private fun userId(): String = auth.currentUser()?.id ?: "anon"

    private fun observeSteps() {
        stepsJob?.cancel()
        val uid = userId()
        val snapshot = metricsStore.metrics(uid)
        _state.value = _state.value.copy(
            metrics = _state.value.metrics.copy(
                steps = snapshot.steps,
                stepsAvailable = snapshot.stepsAvailable,
                stepsPermissionNeeded = snapshot.stepsPermissionNeeded,
                waterMl = snapshot.waterMl,
                waterGoalMl = snapshot.waterGoalMl,
                stepsGoal = snapshot.stepsGoal,
            ),
        )
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

    fun onStepsPermissionResult(granted: Boolean) {
        _state.value = _state.value.copy(metrics = metricsStore.metrics(userId()))
        if (granted) observeSteps()
    }

    fun refresh(date: LocalDate = selectedDate.date.value) {
        viewModelScope.launch {
            val keepData = _state.value.plan != null
            _state.value = _state.value.copy(
                loading = !keepData,
                refreshing = keepData,
                error = null,
                missingPlan = false,
            )
            try {
                val plan = mealPlans.today(date)
                val profile = runCatching { profiles.refreshProfile() }.getOrNull()
                val metrics = metricsStore.metrics(userId())
                val logs = runCatching {
                    nutritionApi.listLogs(date.toString())
                }.getOrDefault(emptyList())
                _state.value = TodayUiState(
                    loading = false,
                    refreshing = false,
                    plan = plan,
                    profile = profile,
                    metrics = metrics,
                    nutritionLogs = logs,
                    selectedDate = date.toString(),
                    lastUpdatedEpochMs = System.currentTimeMillis(),
                )
                observeSteps()
            } catch (error: ApiException) {
                val missing = error.code == "meal_plan_not_found" || error.httpStatus == 404
                _state.value = _state.value.copy(
                    loading = false,
                    refreshing = false,
                    metrics = metricsStore.metrics(userId()),
                    error = if (missing) {
                        "План на этот день отсутствует."
                    } else {
                        error.toUiMessage()
                    },
                    missingPlan = missing,
                )
            } catch (error: Exception) {
                _state.value = _state.value.copy(
                    loading = false,
                    refreshing = false,
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
                    NutritionLogCreateRequest(
                        loggedOn = selectedDate.date.value.toString(),
                        mealType = "snack",
                        source = "manual",
                        description = description,
                        caloriesKcal = calories,
                        proteinG = 0.0,
                        fatG = 0.0,
                        carbohydrateG = 0.0,
                    ),
                )
                bus.emit(DomainEvent.NutritionLogChanged(selectedDate.date.value))
                refresh()
            } catch (error: ApiException) {
                _state.value = _state.value.copy(actionError = error.toUiMessage())
            }
        }
    }

    fun generatePlan() {
        viewModelScope.launch {
            _state.value = _state.value.copy(generating = true, error = null, actionError = null)
            try {
                mealPlans.generate(days = 7, force = true)
                refresh()
            } catch (error: ApiException) {
                _state.value = _state.value.copy(
                    generating = false,
                    error = error.toUiMessage(),
                    missingPlan = error.code == "meal_plan_not_found" || error.httpStatus == 404 ||
                        error.httpStatus == 429,
                )
            }
        }
    }

    fun rebuildPlan() {
        viewModelScope.launch {
            _state.value = _state.value.copy(generating = true, actionError = null, infoMessage = null)
            try {
                mealPlans.regenerate(days = 7)
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
    val refreshing: Boolean = false,
    val plan: MealPlanDto? = null,
    val profile: ProfileResponse? = null,
    val selectedDate: String = LocalDate.now().toString(),
    val weekDates: List<String> = emptyList(),
    val dayStatuses: Map<String, String> = emptyMap(),
    val lastUpdatedEpochMs: Long = 0L,
    val error: String? = null,
    val missingPlan: Boolean = false,
    val actionError: String? = null,
    val infoMessage: String? = null,
)

@HiltViewModel
class WeekViewModel @Inject constructor(
    private val mealPlans: MealPlanRepository,
    private val profiles: ProfileRepository,
    private val bus: AppStateBus,
    private val selectedDate: SelectedDateStore,
) : ViewModel() {
    private val _state = MutableStateFlow(WeekUiState())
    val state: StateFlow<WeekUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            selectedDate.date.collectLatest { date ->
                _state.value = _state.value.copy(selectedDate = date.toString())
            }
        }
        refresh()
        viewModelScope.launch {
            bus.events.collectLatest { event ->
                when (event) {
                    is DomainEvent.PlanChanged,
                    is DomainEvent.ProfileChanged,
                    -> refresh()
                    is DomainEvent.SelectedDateChanged -> {
                        _state.value = _state.value.copy(selectedDate = event.date.toString())
                    }
                    else -> Unit
                }
            }
        }
    }

    fun refresh() {
        viewModelScope.launch {
            val keep = _state.value.plan != null
            _state.value = _state.value.copy(
                loading = !keep,
                refreshing = keep,
                error = null,
                missingPlan = false,
            )
            try {
                val plan = mealPlans.week(selectedDate.date.value)
                val profile = runCatching { profiles.refreshProfile() }.getOrNull()
                val dates = datesBetween(plan.startDate, plan.endDate)
                val statuses = dates.associateWith { date ->
                    val items = plan.items.filter { it.date == date }
                    when {
                        items.isEmpty() -> "missing"
                        else -> "planned"
                    }
                }
                val selected = when {
                    dates.contains(selectedDate.date.value.toString()) -> selectedDate.date.value.toString()
                    dates.contains(LocalDate.now().toString()) -> LocalDate.now().toString()
                    else -> dates.firstOrNull().orEmpty()
                }
                if (selected.isNotBlank()) {
                    selectedDate.select(LocalDate.parse(selected))
                }
                _state.value = WeekUiState(
                    loading = false,
                    refreshing = false,
                    plan = plan,
                    profile = profile,
                    selectedDate = selected,
                    weekDates = dates,
                    dayStatuses = statuses,
                    lastUpdatedEpochMs = System.currentTimeMillis(),
                )
            } catch (error: ApiException) {
                val missing = error.code == "meal_plan_not_found" || error.httpStatus == 404
                _state.value = _state.value.copy(
                    loading = false,
                    refreshing = false,
                    error = if (missing) "План на неделю отсутствует." else error.toUiMessage(),
                    missingPlan = missing,
                )
            } catch (error: Exception) {
                _state.value = _state.value.copy(
                    loading = false,
                    refreshing = false,
                    error = error.message ?: "Не удалось загрузить неделю",
                )
            }
        }
    }

    fun generatePlan() {
        viewModelScope.launch {
            _state.value = _state.value.copy(generating = true, error = null, actionError = null)
            try {
                mealPlans.generate(days = 7, force = true)
                refresh()
            } catch (error: ApiException) {
                _state.value = _state.value.copy(
                    generating = false,
                    error = error.toUiMessage(),
                    missingPlan = error.httpStatus == 404 || error.httpStatus == 429,
                )
            }
        }
    }

    fun rebuildPlan() {
        viewModelScope.launch {
            _state.value = _state.value.copy(generating = true, actionError = null, infoMessage = null)
            try {
                mealPlans.regenerate(days = 7)
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
        runCatching { selectedDate.select(LocalDate.parse(date)) }
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
