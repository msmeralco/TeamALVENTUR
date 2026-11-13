package com.alventur.silipapp.notifications

import android.annotation.SuppressLint
import android.app.Notification
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import androidx.work.CoroutineWorker
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import androidx.work.workDataOf
import com.alventur.silipapp.MainActivity
import com.alventur.silipapp.R
import java.util.concurrent.TimeUnit

/**
 * "Remind me in 10 min" for a safety alert. One-time WorkManager job that posts a reminder on the
 * existing home-safety channel. Same notification rules as [AwayMonitor]: nothing is posted when
 * notifications are off, and the wording repeats what the clamp saw (a steady whole-home load).
 */
object SafetyReminder {
    private const val WORK_PREFIX = "silip-safety-reminder-"
    private const val KEY_MESSAGE = "message"
    private const val NOTIFICATION_ID = 75

    fun schedule(context: Context, alertId: String, message: String, minutes: Long = 10) {
        val request = OneTimeWorkRequestBuilder<SafetyReminderWorker>()
            .setInitialDelay(minutes, TimeUnit.MINUTES)
            .setInputData(workDataOf(KEY_MESSAGE to message))
            .build()
        WorkManager.getInstance(context).enqueueUniqueWork(WORK_PREFIX + alertId, ExistingWorkPolicy.REPLACE, request)
    }

    fun cancel(context: Context, alertId: String) {
        WorkManager.getInstance(context).cancelUniqueWork(WORK_PREFIX + alertId)
    }

    @SuppressLint("MissingPermission")
    internal fun post(context: Context, message: String) {
        if (!AwayMonitor.notificationsAllowed(context)) return
        NotificationChannels.create(context)
        val open = PendingIntent.getActivity(
            context, NOTIFICATION_ID, Intent(context, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        val notification = Notification.Builder(context, NotificationChannels.HOME_SAFETY)
            .setSmallIcon(R.drawable.ic_energy_notification)
            .setContentTitle("Reminder from Ali: check what's on at home")
            .setContentText(message)
            .setStyle(Notification.BigTextStyle().bigText(message))
            .setContentIntent(open)
            .setAutoCancel(true)
            .setVisibility(Notification.VISIBILITY_PRIVATE)
            .build()
        context.getSystemService(NotificationManager::class.java)?.notify(NOTIFICATION_ID, notification)
    }

    internal fun messageFrom(params: WorkerParameters): String =
        params.inputData.getString(KEY_MESSAGE)
            ?: "A steady load was still on at home. Check if something was left plugged in."
}

class SafetyReminderWorker(context: Context, private val params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result {
        SafetyReminder.post(applicationContext, SafetyReminder.messageFrom(params))
        return Result.success()
    }
}
