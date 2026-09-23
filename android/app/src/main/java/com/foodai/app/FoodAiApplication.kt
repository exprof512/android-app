package com.foodai.app

import android.app.Application
import coil.ImageLoader
import coil.ImageLoaderFactory
import com.foodai.app.core.notifications.NotificationScheduler
import dagger.hilt.android.HiltAndroidApp
import javax.inject.Inject

@HiltAndroidApp
class FoodAiApplication : Application(), ImageLoaderFactory {
    @Inject
    lateinit var imageLoader: ImageLoader

    @Inject
    lateinit var notificationScheduler: NotificationScheduler

    override fun onCreate() {
        super.onCreate()
        // Channel + restore alarms from prefs after process restart.
        notificationScheduler.ensureChannel()
        notificationScheduler.reschedule()
    }

    override fun newImageLoader(): ImageLoader = imageLoader
}
