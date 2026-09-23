package com.foodai.app.core.notifications

import android.app.AlarmManager
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.foodai.app.MainActivity
import com.foodai.app.R
import java.util.Calendar
import javax.inject.Inject
import javax.inject.Singleton

data class NotificationPrefs(
    val masterEnabled: Boolean = false,
    val meals: Boolean = true,
    val water: Boolean = true,
    val weight: Boolean = true,
    val weekly: Boolean = false,
)

@Singleton
class NotificationPreferences @Inject constructor(
    @dagger.hilt.android.qualifiers.ApplicationContext private val context: Context,
) {
    private val prefs: SharedPreferences =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun load(): NotificationPrefs = NotificationPrefs(
        masterEnabled = prefs.getBoolean(KEY_MASTER, false),
        meals = prefs.getBoolean(KEY_MEALS, true),
        water = prefs.getBoolean(KEY_WATER, true),
        weight = prefs.getBoolean(KEY_WEIGHT, true),
        weekly = prefs.getBoolean(KEY_WEEKLY, false),
    )

    fun save(prefsData: NotificationPrefs) {
        prefs.edit()
            .putBoolean(KEY_MASTER, prefsData.masterEnabled)
            .putBoolean(KEY_MEALS, prefsData.meals)
            .putBoolean(KEY_WATER, prefsData.water)
            .putBoolean(KEY_WEIGHT, prefsData.weight)
            .putBoolean(KEY_WEEKLY, prefsData.weekly)
            .apply()
    }

    companion object {
        const val PREFS = "foodai_notifications"
        const val KEY_MASTER = "master"
        const val KEY_MEALS = "meals"
        const val KEY_WATER = "water"
        const val KEY_WEIGHT = "weight"
        const val KEY_WEEKLY = "weekly"
    }
}

@Singleton
class NotificationScheduler @Inject constructor(
    @dagger.hilt.android.qualifiers.ApplicationContext private val context: Context,
    private val preferences: NotificationPreferences,
) {
    fun ensureChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val manager = context.getSystemService(NotificationManager::class.java) ?: return
        val channel = NotificationChannel(
            CHANNEL_ID,
            "Напоминания FoodAI",
            NotificationManager.IMPORTANCE_DEFAULT,
        ).apply {
            description = "Приёмы пищи, вода, вес и недельный итог"
        }
        manager.createNotificationChannel(channel)
    }

    fun reschedule() {
        ensureChannel()
        cancelAll()
        val prefs = preferences.load()
        if (!prefs.masterEnabled) return
        if (prefs.meals) {
            scheduleDaily(REQ_BREAKFAST, 9, 0, KIND_MEAL, "Время завтрака", "Отметь приём пищи в FoodAI")
            scheduleDaily(REQ_LUNCH, 13, 0, KIND_MEAL, "Время обеда", "Не забудь отметить обед")
            scheduleDaily(REQ_DINNER, 19, 0, KIND_MEAL, "Время ужина", "Заверши день по плану")
        }
        if (prefs.water) {
            scheduleDaily(REQ_WATER, 11, 0, KIND_WATER, "Вода", "Выпей стакан воды (+250 мл)")
            scheduleDaily(REQ_WATER_PM, 16, 0, KIND_WATER, "Вода", "Ещё один стакан воды")
        }
        if (prefs.weight) {
            scheduleDaily(REQ_WEIGHT, 8, 0, KIND_WEIGHT, "Вес", "Запиши утренний вес")
        }
        if (prefs.weekly) {
            scheduleWeekly(REQ_WEEKLY, Calendar.SUNDAY, 18, 0, KIND_WEEKLY, "Неделя", "Посмотри итоги недели в FoodAI")
        }
    }

    fun cancelAll() {
        listOf(REQ_BREAKFAST, REQ_LUNCH, REQ_DINNER, REQ_WATER, REQ_WATER_PM, REQ_WEIGHT, REQ_WEEKLY)
            .forEach { cancel(it) }
    }

    private fun scheduleDaily(requestCode: Int, hour: Int, minute: Int, kind: String, title: String, body: String) {
        val calendar = Calendar.getInstance().apply {
            set(Calendar.HOUR_OF_DAY, hour)
            set(Calendar.MINUTE, minute)
            set(Calendar.SECOND, 0)
            set(Calendar.MILLISECOND, 0)
            if (before(Calendar.getInstance())) add(Calendar.DAY_OF_YEAR, 1)
        }
        val alarm = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        val intent = Intent(context, FoodAiAlarmReceiver::class.java).apply {
            action = ACTION_REMIND
            putExtra(EXTRA_KIND, kind)
            putExtra(EXTRA_TITLE, title)
            putExtra(EXTRA_BODY, body)
            putExtra(EXTRA_REQ, requestCode)
        }
        val pending = PendingIntent.getBroadcast(
            context,
            requestCode,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        alarm.setInexactRepeating(
            AlarmManager.RTC_WAKEUP,
            calendar.timeInMillis,
            AlarmManager.INTERVAL_DAY,
            pending,
        )
    }

    private fun scheduleWeekly(
        requestCode: Int,
        dayOfWeek: Int,
        hour: Int,
        minute: Int,
        kind: String,
        title: String,
        body: String,
    ) {
        val calendar = Calendar.getInstance().apply {
            set(Calendar.DAY_OF_WEEK, dayOfWeek)
            set(Calendar.HOUR_OF_DAY, hour)
            set(Calendar.MINUTE, minute)
            set(Calendar.SECOND, 0)
            set(Calendar.MILLISECOND, 0)
            if (before(Calendar.getInstance())) add(Calendar.WEEK_OF_YEAR, 1)
        }
        val alarm = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        val intent = Intent(context, FoodAiAlarmReceiver::class.java).apply {
            action = ACTION_REMIND
            putExtra(EXTRA_KIND, kind)
            putExtra(EXTRA_TITLE, title)
            putExtra(EXTRA_BODY, body)
            putExtra(EXTRA_REQ, requestCode)
        }
        val pending = PendingIntent.getBroadcast(
            context,
            requestCode,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        alarm.setInexactRepeating(
            AlarmManager.RTC_WAKEUP,
            calendar.timeInMillis,
            AlarmManager.INTERVAL_DAY * 7,
            pending,
        )
    }

    private fun cancel(requestCode: Int) {
        val alarm = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        val intent = Intent(context, FoodAiAlarmReceiver::class.java).apply { action = ACTION_REMIND }
        val pending = PendingIntent.getBroadcast(
            context,
            requestCode,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        alarm.cancel(pending)
    }

    companion object {
        const val CHANNEL_ID = "foodai_reminders"
        const val ACTION_REMIND = "com.foodai.app.action.REMIND"
        const val EXTRA_KIND = "kind"
        const val EXTRA_TITLE = "title"
        const val EXTRA_BODY = "body"
        const val EXTRA_REQ = "req"
        const val KIND_MEAL = "meal"
        const val KIND_WATER = "water"
        const val KIND_WEIGHT = "weight"
        const val KIND_WEEKLY = "weekly"
        private const val REQ_BREAKFAST = 1001
        private const val REQ_LUNCH = 1002
        private const val REQ_DINNER = 1003
        private const val REQ_WATER = 1004
        private const val REQ_WATER_PM = 1005
        private const val REQ_WEIGHT = 1006
        private const val REQ_WEEKLY = 1007
    }
}

class FoodAiAlarmReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent?) {
        if (intent?.action != NotificationScheduler.ACTION_REMIND &&
            intent?.action != Intent.ACTION_BOOT_COMPLETED
        ) {
            return
        }
        if (intent.action == Intent.ACTION_BOOT_COMPLETED) {
            // Reschedule from prefs after reboot.
            val prefs = context.getSharedPreferences(NotificationPreferences.PREFS, Context.MODE_PRIVATE)
            if (!prefs.getBoolean(NotificationPreferences.KEY_MASTER, false)) return
            val scheduler = NotificationScheduler(
                context.applicationContext,
                NotificationPreferences(context.applicationContext),
            )
            scheduler.reschedule()
            return
        }
        val title = intent.getStringExtra(NotificationScheduler.EXTRA_TITLE) ?: "FoodAI"
        val body = intent.getStringExtra(NotificationScheduler.EXTRA_BODY) ?: "Напоминание"
        val req = intent.getIntExtra(NotificationScheduler.EXTRA_REQ, 2000)
        val open = PendingIntent.getActivity(
            context,
            req + 50,
            Intent(context, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val notification = NotificationCompat.Builder(context, NotificationScheduler.CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_launcher)
            .setContentTitle(title)
            .setContentText(body)
            .setContentIntent(open)
            .setAutoCancel(true)
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .build()
        runCatching {
            NotificationManagerCompat.from(context).notify(req, notification)
        }
    }
}
