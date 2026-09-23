package com.foodai.app.core.progress

import com.foodai.app.core.network.ApiErrorParser
import com.foodai.app.core.network.ProgressApi
import com.foodai.app.core.network.ProgressSummaryDto
import com.foodai.app.core.network.WeightEntryCreateRequest
import com.foodai.app.core.network.WeightEntryDto
import com.foodai.app.core.profile.ProfileRepository
import com.foodai.app.core.sync.AppStateBus
import com.foodai.app.core.sync.DomainEvent
import java.time.Instant
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ProgressRepository @Inject constructor(
    private val progressApi: ProgressApi,
    private val profiles: ProfileRepository,
    private val bus: AppStateBus,
) {
    suspend fun summary(date: String? = null, period: Int? = null): ProgressSummaryDto =
        wrap { progressApi.summary(date = date, period = period) }

    suspend fun listEntries(): List<WeightEntryDto> =
        wrap { progressApi.listWeightEntries() }

    suspend fun addWeight(weightKg: Double, note: String? = null): WeightEntryDto {
        val entry = wrap {
            progressApi.createWeightEntry(
                WeightEntryCreateRequest(
                    measuredAt = Instant.now().toString(),
                    weightKg = weightKg,
                    note = note,
                ),
            )
        }
        profiles.invalidateLocal()
        bus.emit(DomainEvent.WeightChanged(weightKg))
        bus.emit(DomainEvent.ProfileChanged("weight"))
        return entry
    }

    private suspend fun <T> wrap(block: suspend () -> T): T =
        try {
            block()
        } catch (error: Throwable) {
            throw ApiErrorParser.fromThrowable(error)
        }
}
