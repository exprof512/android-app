package com.foodai.app.core.sync

import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import java.time.LocalDate
import javax.inject.Inject
import javax.inject.Singleton

/** Typed domain events for cross-screen invalidation (Phase 18). */
sealed interface DomainEvent {
    data class PlanChanged(val reason: String = "mutation") : DomainEvent
    data class WeightChanged(val weightKg: Double? = null) : DomainEvent
    data class ProfileChanged(val reason: String = "mutation") : DomainEvent
    data class NutritionLogChanged(val date: LocalDate = LocalDate.now()) : DomainEvent
    data class ShoppingChanged(val mealPlanId: String? = null) : DomainEvent
    data class SelectedDateChanged(val date: LocalDate) : DomainEvent
}

@Singleton
class AppStateBus @Inject constructor() {
    private val _events = MutableSharedFlow<DomainEvent>(extraBufferCapacity = 64)
    val events: SharedFlow<DomainEvent> = _events.asSharedFlow()

    fun emit(event: DomainEvent) {
        _events.tryEmit(event)
    }
}
