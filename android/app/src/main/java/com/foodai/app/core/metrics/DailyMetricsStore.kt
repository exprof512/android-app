package com.foodai.app.core.metrics

import android.content.Context
import android.content.SharedPreferences
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import java.time.LocalDate
import javax.inject.Inject
import javax.inject.Singleton

data class DailyMetrics(
    val waterMl: Int = 0,
    val waterGoalMl: Int = 2000,
    val steps: Int = 0,
    val stepsGoal: Int = 8000,
    val stepsAvailable: Boolean = false,
)

/**
 * Local daily water + step cache, scoped by user id so accounts don't leak data.
 */
@Singleton
class DailyMetricsStore @Inject constructor(
    @ApplicationContext context: Context,
) {
    private val prefs: SharedPreferences =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
    private val sensorManager = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
    private val stepSensor: Sensor? = sensorManager.getDefaultSensor(Sensor.TYPE_STEP_COUNTER)

    fun metrics(userId: String): DailyMetrics {
        val day = LocalDate.now().toString()
        val water = prefs.getInt(key(userId, "water", day), 0)
        val baseline = prefs.getFloat(key(userId, "steps_baseline", day), -1f)
        val latest = prefs.getFloat(key(userId, "steps_latest", day), -1f)
        val steps = if (baseline >= 0f && latest >= baseline) {
            (latest - baseline).toInt()
        } else {
            prefs.getInt(key(userId, "steps", day), 0)
        }
        return DailyMetrics(
            waterMl = water,
            steps = steps.coerceAtLeast(0),
            stepsAvailable = stepSensor != null,
        )
    }

    fun addWater(userId: String, deltaMl: Int): DailyMetrics {
        val day = LocalDate.now().toString()
        val next = (prefs.getInt(key(userId, "water", day), 0) + deltaMl).coerceIn(0, 6000)
        prefs.edit().putInt(key(userId, "water", day), next).apply()
        return metrics(userId)
    }

    fun setWater(userId: String, ml: Int): DailyMetrics {
        val day = LocalDate.now().toString()
        prefs.edit().putInt(key(userId, "water", day), ml.coerceIn(0, 6000)).apply()
        return metrics(userId)
    }

    /** Observe hardware step counter; updates daily delta for [userId]. */
    fun observeSteps(userId: String): Flow<Int> = callbackFlow {
        val sensor = stepSensor
        if (sensor == null) {
            trySend(metrics(userId).steps)
            close()
            return@callbackFlow
        }
        val day = LocalDate.now().toString()
        val listener = object : SensorEventListener {
            override fun onSensorChanged(event: SensorEvent?) {
                val total = event?.values?.firstOrNull() ?: return
                var baseline = prefs.getFloat(key(userId, "steps_baseline", day), -1f)
                if (baseline < 0f) {
                    baseline = total
                    prefs.edit().putFloat(key(userId, "steps_baseline", day), baseline).apply()
                }
                prefs.edit().putFloat(key(userId, "steps_latest", day), total).apply()
                val steps = (total - baseline).toInt().coerceAtLeast(0)
                prefs.edit().putInt(key(userId, "steps", day), steps).apply()
                trySend(steps)
            }

            override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) = Unit
        }
        sensorManager.registerListener(listener, sensor, SensorManager.SENSOR_DELAY_UI)
        trySend(metrics(userId).steps)
        awaitClose { sensorManager.unregisterListener(listener) }
    }

    fun clearUser(userId: String) {
        val editor = prefs.edit()
        prefs.all.keys.filter { it.startsWith("$userId:") }.forEach { editor.remove(it) }
        editor.apply()
    }

    fun clearAll() {
        prefs.edit().clear().apply()
    }

    private fun key(userId: String, field: String, day: String) = "$userId:$field:$day"

    companion object {
        private const val PREFS = "foodai_daily_metrics"
    }
}
