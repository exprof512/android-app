package com.foodai.app.core.metrics

import android.Manifest
import android.content.Context
import android.content.SharedPreferences
import android.content.pm.PackageManager
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.Build
import androidx.core.content.ContextCompat
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
    val stepsPermissionNeeded: Boolean = false,
)

/**
 * Local daily water + step cache, scoped by user id so accounts don't leak data.
 * Steps: prefer TYPE_STEP_COUNTER; fallback to TYPE_STEP_DETECTOR.
 * Sensor is registered only after ACTIVITY_RECOGNITION is granted (API 29+).
 */
@Singleton
class DailyMetricsStore @Inject constructor(
    @ApplicationContext private val context: Context,
) {
    private val prefs: SharedPreferences =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
    private val sensorManager = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
    private val stepCounter: Sensor? = sensorManager.getDefaultSensor(Sensor.TYPE_STEP_COUNTER)
    private val stepDetector: Sensor? = sensorManager.getDefaultSensor(Sensor.TYPE_STEP_DETECTOR)

    fun hasStepHardware(): Boolean = stepCounter != null || stepDetector != null

    fun hasStepPermission(): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) return true
        return ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.ACTIVITY_RECOGNITION,
        ) == PackageManager.PERMISSION_GRANTED
    }

    fun metrics(userId: String): DailyMetrics {
        val day = LocalDate.now().toString()
        val water = prefs.getInt(key(userId, "water", day), 0)
        val steps = prefs.getInt(key(userId, "steps", day), 0)
        val hw = hasStepHardware()
        val perm = hasStepPermission()
        return DailyMetrics(
            waterMl = water,
            steps = steps.coerceAtLeast(0),
            stepsAvailable = hw && perm,
            stepsPermissionNeeded = hw && !perm,
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

    /** Observe hardware steps; no-ops until permission is granted. */
    fun observeSteps(userId: String): Flow<Int> = callbackFlow {
        if (!hasStepPermission()) {
            trySend(metrics(userId).steps)
            close()
            return@callbackFlow
        }
        val day = LocalDate.now().toString()
        val counter = stepCounter
        val detector = stepDetector
        if (counter == null && detector == null) {
            trySend(0)
            close()
            return@callbackFlow
        }

        val listener = object : SensorEventListener {
            override fun onSensorChanged(event: SensorEvent?) {
                val sensorType = event?.sensor?.type ?: return
                when (sensorType) {
                    Sensor.TYPE_STEP_COUNTER -> {
                        val total = event.values.firstOrNull() ?: return
                        var baseline = prefs.getFloat(key(userId, "steps_baseline", day), -1f)
                        if (baseline < 0f) {
                            baseline = total
                            prefs.edit().putFloat(key(userId, "steps_baseline", day), baseline).apply()
                        }
                        val steps = (total - baseline).toInt().coerceAtLeast(0)
                        prefs.edit()
                            .putFloat(key(userId, "steps_latest", day), total)
                            .putInt(key(userId, "steps", day), steps)
                            .apply()
                        trySend(steps)
                    }
                    Sensor.TYPE_STEP_DETECTOR -> {
                        // Each event ≈ one step (used when counter is missing).
                        val current = prefs.getInt(key(userId, "steps", day), 0) + 1
                        prefs.edit().putInt(key(userId, "steps", day), current).apply()
                        trySend(current)
                    }
                }
            }

            override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) = Unit
        }

        if (counter != null) {
            sensorManager.registerListener(listener, counter, SensorManager.SENSOR_DELAY_NORMAL)
        } else if (detector != null) {
            sensorManager.registerListener(listener, detector, SensorManager.SENSOR_DELAY_NORMAL)
        }
        trySend(prefs.getInt(key(userId, "steps", day), 0))
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
