package com.foodai.app.core.progress

import com.foodai.app.core.network.ApiErrorParser
import com.foodai.app.core.network.ProgressApi
import com.foodai.app.core.network.ProgressSummaryDto
import com.foodai.app.core.network.WeightEntryCreateRequest
import com.foodai.app.core.network.WeightEntryDto
import java.time.Instant
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ProgressRepository @Inject constructor(
    private val progressApi: ProgressApi,
) {
    suspend fun summary(date: String? = null): ProgressSummaryDto =
        wrap { progressApi.summary(date) }

    suspend fun listEntries(): List<WeightEntryDto> =
        wrap { progressApi.listWeightEntries() }

    suspend fun addWeight(weightKg: Double, note: String? = null): WeightEntryDto =
        wrap {
            progressApi.createWeightEntry(
                WeightEntryCreateRequest(
                    measuredAt = Instant.now().toString(),
                    weightKg = weightKg,
                    note = note,
                ),
            )
        }

    private suspend fun <T> wrap(block: suspend () -> T): T =
        try {
            block()
        } catch (error: Throwable) {
            throw ApiErrorParser.fromThrowable(error)
        }
}
