package com.foodai.app.feature.progress

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.foodai.app.core.auth.toUiMessage
import com.foodai.app.core.network.ApiException
import com.foodai.app.core.network.ProgressSummaryDto
import com.foodai.app.core.progress.ProgressRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ProgressUiState(
    val loading: Boolean = true,
    val saving: Boolean = false,
    val summary: ProgressSummaryDto? = null,
    val period: Int = 7,
    val weightInput: String = "",
    val error: String? = null,
    val actionError: String? = null,
)

@HiltViewModel
class ProgressViewModel @Inject constructor(
    private val progress: ProgressRepository,
    private val bus: com.foodai.app.core.sync.AppStateBus,
) : ViewModel() {
    private val _state = MutableStateFlow(ProgressUiState())
    val state: StateFlow<ProgressUiState> = _state.asStateFlow()

    init {
        refresh()
        viewModelScope.launch {
            bus.events.collectLatest { event ->
                when (event) {
                    is com.foodai.app.core.sync.DomainEvent.WeightChanged,
                    is com.foodai.app.core.sync.DomainEvent.ProfileChanged,
                    is com.foodai.app.core.sync.DomainEvent.PlanChanged,
                    is com.foodai.app.core.sync.DomainEvent.NutritionLogChanged,
                    -> refresh()
                    else -> Unit
                }
            }
        }
    }

    fun setPeriod(period: Int) {
        if (period !in setOf(7, 30, 90)) return
        _state.value = _state.value.copy(period = period)
        refresh()
    }

    private var refreshGeneration = 0

    fun refresh() {
        val generation = ++refreshGeneration
        val period = _state.value.period
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null, actionError = null)
            try {
                val summary = progress.summary(period = period)
                if (generation != refreshGeneration) return@launch
                _state.value = ProgressUiState(
                    loading = false,
                    summary = summary,
                    period = period,
                    weightInput = summary.currentWeightKg?.toString().orEmpty(),
                )
            } catch (error: ApiException) {
                _state.value = _state.value.copy(loading = false, error = error.toUiMessage())
            } catch (error: Exception) {
                _state.value = _state.value.copy(
                    loading = false,
                    error = error.message ?: "Не удалось загрузить прогресс",
                )
            }
        }
    }

    fun onWeightInput(value: String) {
        _state.value = _state.value.copy(weightInput = value.filter { it.isDigit() || it == '.' || it == ',' })
    }

    fun saveWeight() {
        val raw = _state.value.weightInput.replace(',', '.')
        val weight = raw.toDoubleOrNull()
        if (weight == null || weight < 30.0 || weight > 400.0) {
            _state.value = _state.value.copy(actionError = "Введите вес от 30 до 400 кг")
            return
        }
        viewModelScope.launch {
            _state.value = _state.value.copy(saving = true, actionError = null)
            try {
                progress.addWeight(weight)
                refresh()
            } catch (error: ApiException) {
                _state.value = _state.value.copy(saving = false, actionError = error.toUiMessage())
            }
        }
    }
}
