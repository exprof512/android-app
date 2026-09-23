package com.foodai.app.core.sync

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.time.LocalDate
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Single selected calendar date shared by Today / Week Plan.
 * Defaults to system today; user day taps update this without cloning per-screen.
 */
@Singleton
class SelectedDateStore @Inject constructor(
    private val bus: AppStateBus,
) {
    private val _date = MutableStateFlow(LocalDate.now())
    val date: StateFlow<LocalDate> = _date.asStateFlow()

    fun select(date: LocalDate) {
        if (_date.value == date) return
        _date.value = date
        bus.emit(DomainEvent.SelectedDateChanged(date))
    }

    fun resetToToday() {
        select(LocalDate.now())
    }
}
