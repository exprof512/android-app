package com.foodai.app.feature.plan

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.foodai.app.core.analytics.AnalyticsTracker
import com.foodai.app.core.ai.AiRecommendationRepository
import com.foodai.app.core.ai.aiPayload
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
import com.foodai.app.core.network.WaterTodayDto
import com.foodai.app.core.profile.ProfileRepository
import com.foodai.app.core.progress.ProgressRepository
import com.foodai.app.core.sync.AppStateBus
import com.foodai.app.core.sync.DomainEvent
import com.foodai.app.core.sync.SelectedDateStore
import com.foodai.app.core.water.WaterRepository
import com.foodai.app.feature.ai.AiPreviewState
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
    val water: WaterTodayDto? = null,
    val nutritionLogs: List<NutritionLogDto> = emptyList(),
    val selectedDate: String = LocalDate.now().toString(),
    val lastUpdatedEpochMs: Long = 0L,
    val error: String? = null,
    val offlineCached: Boolean = false,
    val missingPlan: Boolean = false,
    val actionError: String? = null,
    val infoMessage: String? = null,
    val aiPreview: AiPreviewState = AiPreviewState.Idle,
)

@HiltViewModel
class TodayViewModel @Inject constructor(
    private val mealPlans: MealPlanRepository,
    private val profiles: ProfileRepository,
    private val auth: AuthRepository,
    private val metricsStore: DailyMetricsStore,
    private val nutritionApi: NutritionApi,
    private val waterRepo: WaterRepository,
    private val progress: ProgressRepository,
    private val analytics: AnalyticsTracker,
    private val bus: AppStateBus,
    private val selectedDate: SelectedDateStore,
    private val ai: AiRecommendationRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(TodayUiState())
    val state: StateFlow<TodayUiState> = _state.asStateFlow()
    private var stepsJob: Job? = null
    private var openedTracked = false

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
                    is DomainEvent.WaterChanged,
                    -> refresh(selectedDate.date.value)
                    else -> Unit
                }
            }
        }
    }

    private fun userId(): String = auth.currentUser()?.id ?: "anon"

    private fun observeSteps() {
        stepsJob?.cancel()
        val uid = userId()
        val snapshot = metricsStore.metrics(uid)
        val waterMl = _state.value.water?.totalMl ?: snapshot.waterMl
        val waterGoal = _state.value.water?.goalMl ?: snapshot.waterGoalMl
        _state.value = _state.value.copy(
            metrics = _state.value.metrics.copy(
                steps = snapshot.steps,
                stepsAvailable = snapshot.stepsAvailable,
                stepsPermissionNeeded = snapshot.stepsPermissionNeeded,
                waterMl = waterMl,
                waterGoalMl = waterGoal,
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
        _state.value = _state.value.copy(
            metrics = metricsStore.metrics(userId()).copy(
                waterMl = _state.value.water?.totalMl
                    ?: metricsStore.metrics(userId()).waterMl,
                waterGoalMl = _state.value.water?.goalMl
                    ?: metricsStore.metrics(userId()).waterGoalMl,
            ),
        )
        if (granted) observeSteps()
    }

    fun refresh(date: LocalDate = selectedDate.date.value) {
        viewModelScope.launch {
            val keepData = _state.value.plan != null
            _state.value = _state.value.copy(
                loading = !keepData,
                refreshing = keepData,
                error = null,
                offlineCached = false,
                missingPlan = false,
            )
            try {
                val plan = mealPlans.today(date)
                val profile = runCatching { profiles.refreshProfile() }.getOrNull()
                val water = runCatching { waterRepo.today(date) }.getOrNull()
                if (water != null) {
                    metricsStore.setWater(userId(), water.totalMl)
                }
                val metrics = metricsStore.metrics(userId()).let { m ->
                    m.copy(
                        waterMl = water?.totalMl ?: m.waterMl,
                        waterGoalMl = water?.goalMl ?: m.waterGoalMl,
                    )
                }
                val logs = runCatching {
                    nutritionApi.listLogs(date.toString())
                }.getOrDefault(emptyList())
                _state.value = TodayUiState(
                    loading = false,
                    refreshing = false,
                    plan = plan,
                    profile = profile,
                    metrics = metrics,
                    water = water,
                    nutritionLogs = logs,
                    selectedDate = date.toString(),
                    lastUpdatedEpochMs = System.currentTimeMillis(),
                    aiPreview = _state.value.aiPreview,
                    actionError = _state.value.actionError,
                    infoMessage = _state.value.infoMessage,
                )
                observeSteps()
                if (!openedTracked) {
                    openedTracked = true
                    analytics.track("today_opened")
                }
            } catch (error: ApiException) {
                val missing = error.code == "meal_plan_not_found" || error.httpStatus == 404
                val cached = mealPlans.todayPlan.value.plan ?: _state.value.plan
                val isNetwork = error is ApiException.Network ||
                    error.httpStatus == null && !missing
                if (cached != null && !missing) {
                    _state.value = _state.value.copy(
                        loading = false,
                        refreshing = false,
                        plan = cached,
                        offlineCached = true,
                        error = "Нет соединения",
                        metrics = metricsStore.metrics(userId()),
                        missingPlan = false,
                    )
                } else {
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
                        offlineCached = false,
                    )
                }
            } catch (error: Exception) {
                val cached = mealPlans.todayPlan.value.plan ?: _state.value.plan
                if (cached != null) {
                    _state.value = _state.value.copy(
                        loading = false,
                        refreshing = false,
                        plan = cached,
                        offlineCached = true,
                        error = "Нет соединения",
                    )
                } else {
                    _state.value = _state.value.copy(
                        loading = false,
                        refreshing = false,
                        error = error.message ?: "Не удалось загрузить план",
                    )
                }
            }
        }
    }

    fun addWater(deltaMl: Int = 250) {
        viewModelScope.launch {
            try {
                waterRepo.add(deltaMl, userId(), selectedDate.date.value)
                val water = waterRepo.today(selectedDate.date.value)
                metricsStore.setWater(userId(), water.totalMl)
                _state.value = _state.value.copy(
                    water = water,
                    metrics = _state.value.metrics.copy(
                        waterMl = water.totalMl,
                        waterGoalMl = water.goalMl,
                    ),
                    actionError = null,
                )
                analytics.track("water_added", mapOf("amount_ml" to deltaMl.toString()))
            } catch (error: ApiException) {
                // Optimistic offline mirror fallback.
                val metrics = metricsStore.addWater(userId(), deltaMl)
                _state.value = _state.value.copy(
                    metrics = metrics,
                    actionError = error.toUiMessage(),
                )
            }
        }
    }

    fun undoWater() {
        viewModelScope.launch {
            try {
                waterRepo.undoLast(userId(), selectedDate.date.value)
                val water = runCatching { waterRepo.today(selectedDate.date.value) }.getOrNull()
                if (water != null) {
                    metricsStore.setWater(userId(), water.totalMl)
                    _state.value = _state.value.copy(
                        water = water,
                        metrics = _state.value.metrics.copy(
                            waterMl = water.totalMl,
                            waterGoalMl = water.goalMl,
                        ),
                    )
                }
            } catch (error: ApiException) {
                _state.value = _state.value.copy(actionError = error.toUiMessage())
            }
        }
    }

    fun addFood(
        description: String,
        calories: Int,
        proteinG: Double = 0.0,
        fatG: Double = 0.0,
        carbsG: Double = 0.0,
        mealType: String = "snack",
    ) {
        viewModelScope.launch {
            try {
                nutritionApi.createLog(
                    NutritionLogCreateRequest(
                        loggedOn = selectedDate.date.value.toString(),
                        mealType = mealType,
                        source = "manual",
                        description = description,
                        caloriesKcal = calories,
                        proteinG = proteinG,
                        fatG = fatG,
                        carbohydrateG = carbsG,
                    ),
                )
                analytics.track("food_added")
                bus.emit(DomainEvent.NutritionLogChanged(selectedDate.date.value))
                refresh()
            } catch (error: ApiException) {
                _state.value = _state.value.copy(actionError = error.toUiMessage())
            }
        }
    }

    fun deleteFood(logId: String) {
        viewModelScope.launch {
            try {
                nutritionApi.deleteLog(logId)
                analytics.track("food_deleted")
                bus.emit(DomainEvent.NutritionLogChanged(selectedDate.date.value))
                refresh()
            } catch (error: ApiException) {
                _state.value = _state.value.copy(actionError = error.toUiMessage())
            }
        }
    }

    fun addWeight(weightKg: Double) {
        viewModelScope.launch {
            try {
                progress.addWeight(weightKg)
                analytics.track("weight_added")
                _state.value = _state.value.copy(infoMessage = "Вес сохранён")
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
                val completing = item.status != "completed" && !item.isCompleted
                mealPlans.completeItem(item.id, completed = completing)
                if (completing) {
                    analytics.track("meal_completed", mapOf("meal_type" to item.mealType))
                }
            } catch (error: ApiException) {
                _state.value = _state.value.copy(actionError = error.toUiMessage())
            }
        }
    }

    fun skip(item: MealPlanItemDto) {
        viewModelScope.launch {
            try {
                val skipping = item.status != "skipped"
                mealPlans.skipItem(item.id, skipped = skipping)
                if (skipping) {
                    analytics.track("meal_skipped", mapOf("meal_type" to item.mealType))
                }
            } catch (error: ApiException) {
                _state.value = _state.value.copy(actionError = error.toUiMessage())
            }
        }
    }

    fun replace(item: MealPlanItemDto, reason: String = "user_requested") {
        viewModelScope.launch {
            _state.value = _state.value.copy(refreshing = true, actionError = null)
            try {
                analytics.track("replacement_started", mapOf("reason" to reason))
                mealPlans.replaceItem(item.id, reason = reason)
                analytics.track("replacement_completed", mapOf("reason" to reason))
            } catch (error: ApiException) {
                analytics.track("replacement_failed", mapOf("reason" to reason))
                _state.value = _state.value.copy(
                    refreshing = false,
                    actionError = error.toUiMessage(),
                )
            }
        }
    }

    fun clearMessages() {
        _state.value = _state.value.copy(actionError = null, infoMessage = null)
    }

    fun dismissAiPreview() {
        _state.value = _state.value.copy(aiPreview = AiPreviewState.Idle)
    }

    fun requestWhatToEat(intent: String? = null) {
        viewModelScope.launch {
            analytics.track(
                "ai_recommendation_requested",
                mapOf("intent" to (intent ?: "food_suggestion")),
            )
            _state.value = _state.value.copy(aiPreview = AiPreviewState.Loading, actionError = null)
            try {
                val nextMealType = _state.value.plan?.dayProgress?.nextMealType
                val out = ai.recommend(
                    intent = intent,
                    mealType = nextMealType,
                    date = selectedDate.date.value,
                )
                if (out.candidates.isEmpty()) {
                    _state.value = _state.value.copy(
                        aiPreview = AiPreviewState.Empty(
                            out.warnings.firstOrNull()
                                ?: "Не удалось подобрать варианты. Попробуйте позже.",
                        ),
                    )
                    return@launch
                }
                analytics.track(
                    "ai_recommendation_shown",
                    mapOf("count" to out.candidates.size.toString()),
                )
                val title = when (intent) {
                    "pantry_cook", "pantry" -> "Из продуктов"
                    else -> "Что мне съесть?"
                }
                _state.value = _state.value.copy(
                    aiPreview = AiPreviewState.Recommendations(
                        recommendationId = out.recommendationId,
                        candidates = out.candidates,
                        warnings = out.warnings,
                        title = title,
                    ),
                )
            } catch (error: ApiException) {
                _state.value = _state.value.copy(
                    aiPreview = AiPreviewState.Error(error.toUiMessage()),
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
        val recipeId = candidate.recipeId ?: return
        viewModelScope.launch {
            analytics.track(
                "ai_recommendation_selected",
                mapOf("recipe_id" to recipeId, "index" to preview.selectedIndex.toString()),
            )
            _state.value = _state.value.copy(aiPreview = preview.copy(applying = true))
            try {
                val mealType = _state.value.plan?.dayProgress?.nextMealType ?: "snack"
                ai.apply(
                    recommendationId = preview.recommendationId,
                    actionType = "create_nutrition_log",
                    payload = aiPayload(
                        "recipe_id" to recipeId,
                        "meal_type" to mealType,
                        "date" to selectedDate.date.value.toString(),
                    ),
                )
                _state.value = _state.value.copy(
                    aiPreview = AiPreviewState.Idle,
                    infoMessage = "Добавлено: ${candidate.name}",
                )
                refresh()
            } catch (error: ApiException) {
                _state.value = _state.value.copy(
                    aiPreview = preview.copy(applying = false),
                    actionError = error.toUiMessage(),
                )
            }
        }
    }

    fun requestAdaptDay() {
        viewModelScope.launch {
            analytics.track("ai_day_adaptation_requested")
            _state.value = _state.value.copy(aiPreview = AiPreviewState.Loading, actionError = null)
            try {
                val out = ai.adaptDay(selectedDate.date.value)
                if (out.replacements.isEmpty()) {
                    _state.value = _state.value.copy(
                        aiPreview = AiPreviewState.Empty(
                            out.warnings.firstOrNull()
                                ?: "Нет незавершённых приёмов для адаптации.",
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

    fun confirmAdaptDay() {
        val preview = _state.value.aiPreview as? AiPreviewState.AdaptDay ?: return
        val plan = _state.value.plan ?: return
        val day = selectedDate.date.value.toString()
        viewModelScope.launch {
            _state.value = _state.value.copy(aiPreview = preview.copy(applying = true))
            try {
                for (slot in preview.preview.replacements) {
                    val recipeId = slot.candidate?.recipeId ?: continue
                    val item = plan.items.firstOrNull {
                        it.date.take(10) == day &&
                            it.mealType == slot.mealType &&
                            !it.isCompleted &&
                            it.status != "skipped"
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
                analytics.track("ai_day_adaptation_applied")
                _state.value = _state.value.copy(
                    aiPreview = AiPreviewState.Idle,
                    infoMessage = "Остаток дня адаптирован",
                )
                refresh()
            } catch (error: ApiException) {
                _state.value = _state.value.copy(
                    aiPreview = preview.copy(applying = false),
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
                val summaryDays = plan.weekSummary?.days.orEmpty()
                val dates = if (summaryDays.isNotEmpty()) {
                    summaryDays.map { it.date }
                } else {
                    datesBetween(plan.startDate, plan.endDate)
                }
                val statuses = if (summaryDays.isNotEmpty()) {
                    summaryDays.associate { it.date to it.status }
                } else {
                    dates.associateWith { date ->
                        val items = plan.items.filter { it.date == date }
                        when {
                            items.isEmpty() -> "missing"
                            else -> "planned"
                        }
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
