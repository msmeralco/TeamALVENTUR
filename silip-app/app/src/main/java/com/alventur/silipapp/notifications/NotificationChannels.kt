package com.alventur.silipapp.notifications

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.os.Build

object NotificationChannels {
    const val HOME_SAFETY = "home_safety"

    fun create(context: Context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return

        val channel = NotificationChannel(
            HOME_SAFETY,
            "Home safety reminders",
            NotificationManager.IMPORTANCE_DEFAULT
        ).apply {
            description = "Optional reminders to check your home before leaving."
        }

        context.getSystemService(NotificationManager::class.java)
            ?.createNotificationChannel(channel)
    }
}
