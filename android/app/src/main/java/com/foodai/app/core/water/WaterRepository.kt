package com.foodai.app.core.water

import com.foodai.app.core.metrics.DailyMetricsStore
import com.foodai.app.core.network.ApiErrorParser
import com.foodai.app.core.network.WaterApi
import com.foodai.app.core.network.WaterEntryCreateRequest
import com.foodai.app.core.network.WaterEntryDto
import com.foodai.app.core.network.WaterTodayDto
import com.foodai.app.core.sync.AppStateBus
import com.foodai.app.core.sync.DomainEvent
import java.time.LocalDate
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class WaterRepository @Inject constructor(
    private val waterApi: WaterApi,
    private val metricsStore: DailyMetricsStore,
    private val bus: AppStateBus,
) {
    suspend fun today(date: LocalDate = LocalDate.now()): WaterTodayDto =
        wrap { waterApi.today(date.toString()) }

    suspend fun add(
        amountMl: Int,
        userId: String,
        date: LocalDate = LocalDate.now(),
    ): WaterEntryDto {
        val entry = wrap {
            waterApi.add(
                WaterEntryCreateRequest(
                    amountMl = amountMl,
                    recordedOn = date.toString(),
                ),
            )
        }
        // Offline mirror only — UI should prefer API totals.
        metricsStore.addWater(userId, amountMl)
        bus.emit(DomainEvent.WaterChanged(date))
        return entry
    }

    suspend fun undoLast(userId: String, date: LocalDate = LocalDate.now()) {
        wrap {
            val response = waterApi.deleteLast()
            if (!response.isSuccessful) {
                throw ApiErrorParser.fromHttp(response.code(), response.errorBody())
            }
        }
        runCatching {
            val today = waterApi.today(date.toString())
            metricsStore.setWater(userId, today.totalMl)
        }
        bus.emit(DomainEvent.WaterChanged(date))
    }

    private suspend fun <T> wrap(block: suspend () -> T): T =
        try {
            block()
        } catch (error: Throwable) {
            throw ApiErrorParser.fromThrowable(error)
        }
}
