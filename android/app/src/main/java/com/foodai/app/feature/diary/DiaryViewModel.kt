package com.foodai.app.feature.diary

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.foodai.app.core.auth.toUiMessage
import com.foodai.app.core.diary.DiaryCacheStore
import com.foodai.app.core.network.ApiErrorParser
import com.foodai.app.core.network.ApiException
import com.foodai.app.core.network.NutritionApi
import com.foodai.app.core.network.NutritionLogDto
import com.foodai.app.core.sync.AppStateBus
import com.foodai.app.core.sync.DomainEvent
import com.foodai.app.core.sync.SelectedDateStore
import dagger.hilt.android.lifecycle.HiltViewModel
import java.time.LocalDate
import javax.inject.Inject
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

data class DiaryUiState(
    val loading: Boolean = true,
    val date: String = LocalDate.now().toString(),
    val logs: List<NutritionLogDto> = emptyList(),
    val totalsKcal: Int = 0,
    val proteinG: Double = 0.0,
    val fatG: Double = 0.0,
    val carbsG: Double = 0.0,
    val error: String? = null,
    val offline: Boolean = false,
)

@HiltViewModel
class DiaryViewModel @Inject constructor(
    private val nutritionApi: NutritionApi,
    private val cache: DiaryCacheStore,
    private val bus: AppStateBus,
    private val selectedDate: SelectedDateStore,
) : ViewModel() {
    private val _state = MutableStateFlow(DiaryUiState())
    val state: StateFlow<DiaryUiState> = _state.asStateFlow()
    private var refreshJob: Job? = null
    private var refreshGeneration = 0L

    init {
        viewModelScope.launch {
            selectedDate.date.collectLatest { date ->
                refresh(date)
            }
        }
        viewModelScope.launch {
            bus.events.collectLatest { event ->
                when (event) {
                    is DomainEvent.NutritionLogChanged,
                    is DomainEvent.PlanChanged,
                    -> refresh()
                    else -> Unit
                }
            }
        }
    }

    fun refresh(date: LocalDate = selectedDate.date.value) {
        refreshJob?.cancel()
        val generation = ++refreshGeneration
        refreshJob = viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null, date = date.toString())
            try {
                val logs = nutritionApi.listLogs(date.toString())
                if (generation != refreshGeneration) return@launch
                cache.save(date.toString(), logs)
                _state.value = DiaryUiState(
                    loading = false,
                    date = date.toString(),
                    logs = logs,
                    totalsKcal = logs.sumOf { it.caloriesKcal },
                    proteinG = logs.sumOf { it.proteinG },
                    fatG = logs.sumOf { it.fatG },
                    carbsG = logs.sumOf { it.carbohydrateG },
                )
            } catch (error: Throwable) {
                if (generation != refreshGeneration) return@launch
                val cached = cache.load(date.toString())
                if (cached != null) {
                    _state.value = DiaryUiState(
                        loading = false,
                        date = date.toString(),
                        logs = cached,
                        totalsKcal = cached.sumOf { it.caloriesKcal },
                        proteinG = cached.sumOf { it.proteinG },
                        fatG = cached.sumOf { it.fatG },
                        carbsG = cached.sumOf { it.carbohydrateG },
                        offline = true,
                    )
                } else {
                    val parsed = ApiErrorParser.fromThrowable(error)
                    _state.value = _state.value.copy(
                        loading = false,
                        error = parsed.toUiMessage(),
                    )
                }
            }
        }
    }

    fun prevDay() {
        selectedDate.select(selectedDate.date.value.minusDays(1))
    }

    fun nextDay() {
        selectedDate.select(selectedDate.date.value.plusDays(1))
    }

    fun deleteLog(id: String) {
        viewModelScope.launch {
            try {
                nutritionApi.deleteLog(id)
                bus.emit(DomainEvent.NutritionLogChanged(selectedDate.date.value))
                bus.emit(DomainEvent.PlanChanged("diary_delete"))
                refresh()
            } catch (error: Throwable) {
                val parsed = ApiErrorParser.fromThrowable(error)
                _state.value = _state.value.copy(error = parsed.toUiMessage())
            }
        }
    }
}
