package com.alventur.silipapp.notifications

import android.Manifest
import android.annotation.SuppressLint
import android.app.Notification
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.work.*
import com.alventur.silipapp.MainActivity
import com.alventur.silipapp.R
import com.alventur.silipapp.data.remote.HttpHouseholdApi
import com.alventur.silipapp.energy.EnergyAnalysis
import com.google.android.gms.location.*
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.tasks.await
import java.time.Instant
import java.util.concurrent.TimeUnit

object AwayMonitor {
    private const val WORK = "silip-away-check"
    private const val CHECK = "silip-away-now"
    fun prefs(context: Context) = context.getSharedPreferences("silip_away", Context.MODE_PRIVATE)
    fun notificationsAllowed(context: Context): Boolean =
        (Build.VERSION.SDK_INT < 33 || context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED) &&
            context.getSystemService(NotificationManager::class.java).let { manager ->
                manager.areNotificationsEnabled() && manager.getNotificationChannel(NotificationChannels.HOME_SAFETY)?.importance != NotificationManager.IMPORTANCE_NONE
            }
    fun locationAllowed(context: Context): Boolean = context.checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED &&
        (Build.VERSION.SDK_INT < 29 || context.checkSelfPermission(Manifest.permission.ACCESS_BACKGROUND_LOCATION) == PackageManager.PERMISSION_GRANTED)

    private fun fenceIntent(context: Context): PendingIntent = PendingIntent.getBroadcast(context, 4,
        Intent(context, AwayGeofenceReceiver::class.java), PendingIntent.FLAG_UPDATE_CURRENT or
            if (Build.VERSION.SDK_INT >= 31) PendingIntent.FLAG_MUTABLE else 0)

    @SuppressLint("MissingPermission")
    suspend fun enableAutomatic(context: Context, lat: Double, lon: Double) {
        require(lat.isFinite() && lat in -90.0..90.0 && lon.isFinite() && lon in -180.0..180.0)
        check(locationAllowed(context)) { "Allow precise location and location all the time first." }
        check(notificationsAllowed(context)) { "Allow notifications first." }
        val fence = Geofence.Builder().setRequestId("silip-home").setCircularRegion(lat, lon, 200f)
            .setExpirationDuration(Geofence.NEVER_EXPIRE)
            .setTransitionTypes(Geofence.GEOFENCE_TRANSITION_ENTER or Geofence.GEOFENCE_TRANSITION_EXIT)
            .setNotificationResponsiveness(120_000).build()
        val request = GeofencingRequest.Builder().addGeofence(fence)
            .setInitialTrigger(GeofencingRequest.INITIAL_TRIGGER_ENTER or GeofencingRequest.INITIAL_TRIGGER_EXIT).build()
        // Store the intended mode first so the initial transition cannot arrive before setup.
        val p = prefs(context)
        p.edit().putBoolean("auto", true).putString("lat", lat.toString()).putString("lon", lon.toString()).apply()
        try {
            LocationServices.getGeofencingClient(context).addGeofences(request, fenceIntent(context)).await()
            p.edit().remove("error").apply()
            schedule(context)
        } catch (e: Exception) {
            setAway(context, false)
            p.edit().putBoolean("auto", false).putString("error", "Automatic alerts need setup again.").apply()
            throw e
        }
    }

    fun setAway(context: Context, away: Boolean) {
        val p = prefs(context)
        val wasAway = p.getBoolean("away", false)
        val edit = p.edit().putBoolean("away", away)
        if (away && !wasAway) edit.putLong("departed", Instant.now().epochSecond).putBoolean("notified", false).remove("status")
        if (!away) edit.remove("departed").putBoolean("notified", false)
        edit.apply()
        if (away) { schedule(context); checkNow(context) }
        else {
            WorkManager.getInstance(context).cancelUniqueWork(CHECK)
            context.getSystemService(NotificationManager::class.java).cancel(73)
            if (!p.getBoolean("auto", false)) WorkManager.getInstance(context).cancelUniqueWork(WORK)
        }
    }

    private fun schedule(context: Context) {
        val request = PeriodicWorkRequestBuilder<AwayCheckWorker>(15, TimeUnit.MINUTES)
            .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build()).build()
        WorkManager.getInstance(context).enqueueUniquePeriodicWork(WORK, ExistingPeriodicWorkPolicy.KEEP, request)
    }
    fun checkNow(context: Context) {
        val request = OneTimeWorkRequestBuilder<AwayCheckWorker>()
            .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build()).build()
        WorkManager.getInstance(context).enqueueUniqueWork(CHECK, ExistingWorkPolicy.REPLACE, request)
    }
    suspend fun disable(context: Context) {
        prefs(context).edit().putBoolean("auto", false).apply()
        setAway(context, false)
        // Always clear local state even when Google Play services is unavailable.
        runCatching { LocationServices.getGeofencingClient(context).removeGeofences(fenceIntent(context)).await() }
    }
    fun restore(context: Context) {
        if (prefs(context).getBoolean("auto", false)) {
            WorkManager.getInstance(context).enqueueUniqueWork("silip-restore-fence", ExistingWorkPolicy.KEEP,
                OneTimeWorkRequestBuilder<AwayRestoreWorker>().build())
        }
    }
    @SuppressLint("MissingPermission")
    fun notify(context: Context, demo: Boolean = false) {
        if (!notificationsAllowed(context)) return
        NotificationChannels.create(context)
        val open = PendingIntent.getActivity(context, 73, Intent(context, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val text = if (demo) "Example: your home is still using power while you're away. Check non-essential loads."
            else "Your home has sustained use above your away threshold. Check unused lights, fans or cooling; keep essentials on."
        val notification = Notification.Builder(context, NotificationChannels.HOME_SAFETY)
            .setSmallIcon(R.drawable.ic_energy_notification)
            .setContentTitle(if (demo) "Demo · away energy reminder" else "Away from home? Check your energy")
            .setContentText(text).setStyle(Notification.BigTextStyle().bigText(text))
            .setContentIntent(open).setAutoCancel(true).setVisibility(Notification.VISIBILITY_PRIVATE).build()
        context.getSystemService(NotificationManager::class.java).notify(if (demo) 74 else 73, notification)
    }
}

class AwayGeofenceReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val event = GeofencingEvent.fromIntent(intent) ?: return
        if (!AwayMonitor.prefs(context).getBoolean("auto", false)) return
        if (event.hasError()) {
            AwayMonitor.prefs(context).edit().putBoolean("auto", false)
                .putString("error", "Location monitoring stopped. Enable automatic alerts again.").apply()
            AwayMonitor.setAway(context, false)
            return
        }
        when (event.geofenceTransition) {
            Geofence.GEOFENCE_TRANSITION_EXIT -> AwayMonitor.setAway(context, true)
            Geofence.GEOFENCE_TRANSITION_ENTER -> AwayMonitor.setAway(context, false)
        }
    }
}

class AwayBootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED || intent.action == Intent.ACTION_MY_PACKAGE_REPLACED) AwayMonitor.restore(context)
    }
}

class AwayRestoreWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result {
        val p = AwayMonitor.prefs(applicationContext)
        if (!p.getBoolean("auto", false)) return Result.success()
        val lat = p.getString("lat", null)?.toDoubleOrNull() ?: return Result.failure()
        val lon = p.getString("lon", null)?.toDoubleOrNull() ?: return Result.failure()
        return try { AwayMonitor.enableAutomatic(applicationContext, lat, lon); Result.success() }
        catch (e: CancellationException) { throw e }
        catch (_: Exception) { Result.failure() }
    }
}

class AwayCheckWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result {
        val p = AwayMonitor.prefs(applicationContext)
        if (p.getBoolean("auto", false) && !AwayMonitor.locationAllowed(applicationContext)) {
            AwayMonitor.disable(applicationContext)
            p.edit().putString("error", "Automatic alerts stopped because location permission changed.").apply()
            return Result.success()
        }
        if (!p.getBoolean("away", false) || p.getBoolean("notified", false)) return Result.success()
        val departed = p.getLong("departed", 0)
        if (departed == 0L) return Result.success()
        val id = applicationContext.getSharedPreferences("silip_demo_device", Context.MODE_PRIVATE)
            .getString("clamp_id", "silip-esp32-test") ?: return Result.success()
        return try {
            val device = HttpHouseholdApi().getDeviceUsage(id)
            val threshold = p.getString("threshold", "0.3")?.toDoubleOrNull() ?: 0.3
            val demand = EnergyAnalysis.awayDemand(device, Instant.ofEpochSecond(departed), threshold, Instant.now())
            val status = when {
                device.isSimulated -> "Paused: usage includes simulated data. Use the demo notification to preview."
                demand != null -> "Sustained use above your threshold."
                else -> "Waiting for two fresh post-departure intervals above your threshold."
            }
            p.edit().putString("status", status).apply()
            // Re-check departure after the network call: returning home cancels an in-flight alert.
            synchronized(AwayMonitor) {
                val currentId = applicationContext.getSharedPreferences("silip_demo_device", Context.MODE_PRIVATE).getString("clamp_id", "silip-esp32-test")
                if (demand != null && !p.getBoolean("notified", false) && currentId == id && p.getBoolean("away", false) &&
                    p.getLong("departed", 0) == departed && AwayMonitor.notificationsAllowed(applicationContext)) {
                    AwayMonitor.notify(applicationContext)
                    p.edit().putBoolean("notified", true).apply()
                }
            }
            Result.success()
        } catch (e: CancellationException) { throw e }
        catch (_: Exception) {
            p.edit().putString("status", "Could not check usage. Will try again when connected.").apply()
            if (runAttemptCount < 3) Result.retry() else Result.failure()
        }
    }
}
