package com.foodai.app.core.analytics

import android.util.Log
import com.foodai.app.BuildConfig
import com.foodai.app.core.network.AnalyticsApi
import com.foodai.app.core.network.AnalyticsBatchRequest
import com.foodai.app.core.network.AnalyticsEventDto
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import javax.inject.Inject
import javax.inject.Singleton

interface AnalyticsTracker {
    fun track(eventName: String, properties: Map<String, String> = emptyMap())
}

@Singleton
class BackendAnalyticsTracker @Inject constructor(
    private val api: AnalyticsApi,
) : AnalyticsTracker {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    override fun track(eventName: String, properties: Map<String, String>) {
        scope.launch {
            try {
                api.postEvents(
                    AnalyticsBatchRequest(
                        events = listOf(
                            AnalyticsEventDto(
                                eventName = eventName,
                                platform = "android",
                                appVersion = BuildConfig.VERSION_NAME,
                                properties = properties,
                            ),
                        ),
                    ),
                )
            } catch (error: Throwable) {
                // Never block product flows.
                if (BuildConfig.DEBUG) {
                    Log.d("Analytics", "event dropped: $eventName", error)
                }
            }
        }
    }
}
