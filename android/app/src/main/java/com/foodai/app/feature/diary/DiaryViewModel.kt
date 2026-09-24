package com.foodai.app.feature.diary

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.foodai.app.core.auth.toUiMessage
import com.foodai.app.core.network.ApiException
import com.foodai.app.core.network.NutritionApi
import com.foodai.app.core.network.NutritionLogDto
import com.foodai.app.core.sync.AppStateBus
import com.foodai.app.core.sync.DomainEvent
import com.foodai.app.core.sync.SelectedDateStore
import dagger.hilt.android.lifecycle.HiltViewModel
import java.time.LocalDate
import javax.inject.Inject
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
)

@HiltViewModel
class DiaryViewModel @Inject constructor(
    private val nutritionApi: NutritionApi,
    private val bus: AppStateBus,
    private val selectedDate: SelectedDateStore,
) : ViewModel() {
    private val _state = MutableStateFlow(DiaryUiState())
    val state: StateFlow<DiaryUiState> = _state.asStateFlow()

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
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null, date = date.toString())
            try {
                val logs = nutritionApi.listLogs(date.toString())
                _state.value = DiaryUiState(
                    loading = false,
                    date = date.toString(),
                    logs = logs,
                    totalsKcal = logs.sumOf { it.caloriesKcal },
                    proteinG = logs.sumOf { it.proteinG },
                    fatG = logs.sumOf { it.fatG },
                    carbsG = logs.sumOf { it.carbohydrateG },
                )
            } catch (error: ApiException) {
                _state.value = _state.value.copy(
                    loading = false,
                    error = error.toUiMessage(),
                )
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
                refresh()
            } catch (error: ApiException) {
                _state.value = _state.value.copy(error = error.toUiMessage())
            }
        }
    }
}
