package com.alventur.silipapp.ui

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.alventur.silipapp.data.remote.DeviceUsage
import com.alventur.silipapp.energy.*
import com.alventur.silipapp.notifications.AwayMonitor
import com.google.android.gms.location.*
import com.google.android.gms.tasks.CancellationTokenSource
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

@Composable
private fun FeatureCard(content: @Composable ColumnScope.() -> Unit) {
    Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(28.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = CardDefaults.outlinedCardBorder()) {
        Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp), content = content)
    }
}

@Composable
internal fun selectedEnergyRate(): Double {
    val context = LocalContext.current
    val prefs = remember { context.getSharedPreferences("silip_cost", Context.MODE_PRIVATE) }
    var rate by remember { mutableDoubleStateOf(prefs.getString("rate", null)?.toDoubleOrNull() ?: MeralcoRate.PHP_PER_KWH) }
    DisposableEffect(prefs) {
        val listener = SharedPreferences.OnSharedPreferenceChangeListener { source, _ ->
            rate = source.getString("rate", null)?.toDoubleOrNull() ?: MeralcoRate.PHP_PER_KWH
        }
        prefs.registerOnSharedPreferenceChangeListener(listener)
        onDispose { prefs.unregisterOnSharedPreferenceChangeListener(listener) }
    }
    return rate
}

@Composable
internal fun PriceEstimateCard(device: DeviceUsage) {
    val context = LocalContext.current
    val prefs = remember { context.getSharedPreferences("silip_cost", Context.MODE_PRIVATE) }
    var rate by rememberSaveable { mutableStateOf(prefs.getString("rate", null)?.toDoubleOrNull() ?: MeralcoRate.PHP_PER_KWH) }
    var custom by rememberSaveable { mutableStateOf(prefs.contains("rate")) }
    var expanded by rememberSaveable { mutableStateOf(false) }
    var input by rememberSaveable { mutableStateOf(rate.toString()) }
    val valid = input.toDoubleOrNull()?.takeIf { it.isFinite() && it > 0 && it <= 100 }
    FeatureCard {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            EnergyIcon(Icons.Outlined.Payments)
            Column(Modifier.weight(1f)) {
                Text("Estimated energy cost", style = MaterialTheme.typography.titleMedium)
                Text("Last 7 days of stored readings", style = MaterialTheme.typography.bodySmall)
            }
        }
        if (device.points.isEmpty()) Text("Waiting for usage", style = MaterialTheme.typography.headlineSmall)
        else Text(pesos(MeralcoRate.cost(device.totalKwh, rate)), style = MaterialTheme.typography.headlineLarge, fontWeight = FontWeight.ExtraBold)
        Text(if (device.isSimulated) "Simulated usage · price estimate" else "Sensor-based estimate", color = MaterialTheme.colorScheme.primary)
        Text(if (custom) "Your bill rate · ₱${number(rate, 4)}/kWh" else "Meralco · ${MeralcoRate.MONTH} · ₱${number(rate, 4)}/kWh",
            style = MaterialTheme.typography.bodySmall)
        TextButton(onClick = { expanded = !expanded }) { Text(if (expanded) "Hide calculation" else "How is this calculated?") }
        if (expanded) {
            Text("${number(device.totalKwh)} kWh × ₱${number(rate, 4)}/kWh. The default uses Meralco's 200 kWh/month non-lifeline benchmark. Actual charges vary with consumption, taxes, discounts and billing dates. Current-clamp kWh also depends on voltage and power-factor assumptions.", style = MaterialTheme.typography.bodySmall)
            Text("This is an energy-cost estimate, not your official bill. The bundled rate is dated October 2026 and does not refresh automatically.", style = MaterialTheme.typography.bodySmall)
            TextButton(onClick = { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(MeralcoRate.SOURCE))) }) { Text("View Meralco source") }
            OutlinedTextField(value = input, onValueChange = { input = it }, label = { Text("Rate from your Meralco bill (₱/kWh)") },
                isError = valid == null, supportingText = { if (valid == null) Text("Enter a rate above 0 and up to 100.") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal), modifier = Modifier.fillMaxWidth())
            Button(onClick = { rate = valid!!; custom = true; prefs.edit().putString("rate", rate.toString()).apply() }, enabled = valid != null) { Text("Use my bill rate") }
            if (custom) TextButton(onClick = {
                rate = MeralcoRate.PHP_PER_KWH; input = rate.toString(); custom = false; prefs.edit().remove("rate").apply()
            }) { Text("Use published Meralco rate") }
        }
    }
}

@Composable
internal fun ForecastAndInsights(device: DeviceUsage) {
    var showModel by rememberSaveable { mutableStateOf(false) }
    var showInsightDetails by rememberSaveable { mutableStateOf(false) }
    val forecast = remember(device.points) { EnergyAnalysis.forecast(device.points) }
    val data = remember(device.points) { EnergyAnalysis.samples(device.points) }
    val rate = selectedEnergyRate()
    FeatureCard {
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
            EnergyIcon(Icons.Outlined.Timeline)
            Text("Your next busy hours", style = MaterialTheme.typography.titleLarge, modifier = Modifier.weight(1f))
        }
        if (forecast == null) {
            Text("A few more days to learn your pattern.", style = MaterialTheme.typography.titleMedium)
            Text("Needs at least five days with 80% interval coverage. Missing readings stay missing.", style = MaterialTheme.typography.bodyMedium)
        } else {
            val latest = data.last().at
            val stale = !EnergyAnalysis.isFresh(latest, Instant.now())
            Text(when {
                device.isSimulated -> "Simulated pattern forecast"
                stale -> "Historical forecast · sensor out of date"
                else -> "Next 24 hours · estimated"
            }, color = MaterialTheme.colorScheme.primary)
            Text("${number(forecast.kwh)} kWh · ${pesos(forecast.kwh * rate)}", style = MaterialTheme.typography.headlineSmall)
            Text("24 hours from ${dateTime(forecast.points.first().at)}", style = MaterialTheme.typography.bodySmall)
            val hours = forecast.points.chunked(4).map { it.map(EnergySample::kw).average() }
            val max = hours.maxOrNull()?.coerceAtLeast(0.01) ?: 1.0
            Row(Modifier.fillMaxWidth().height(72.dp), horizontalArrangement = Arrangement.spacedBy(3.dp), verticalAlignment = Alignment.Bottom) {
                hours.forEach { value -> Box(Modifier.weight(1f).height((value / max * 68).coerceAtLeast(2.0).dp)
                    .background(MaterialTheme.colorScheme.primary, RoundedCornerShape(4.dp))) }
            }
            Text("Hourly forecast · tallest bars mean higher demand", style = MaterialTheme.typography.bodySmall)
            Text("Busiest: ${time(forecast.busiestHour.first().at)}–${time(forecast.busiestHour.last().at.plusSeconds(900))}", style = MaterialTheme.typography.titleMedium)
            Text("${forecast.model} · experimental", style = MaterialTheme.typography.bodySmall)
            TextButton(onClick = { showModel = !showModel }) { Text(if (showModel) "Hide forecast details" else "About this forecast") }
            if (showModel) Text("Checked on the last 24 hours. Average test error: ${number(forecast.validationMaeKw)} kW. Regression is compared against the previous day's pattern. This estimates whole-home demand; it cannot predict a person's activities or identify an appliance.", style = MaterialTheme.typography.bodySmall)
        }
    }
    Spacer(Modifier.height(16.dp))
    if (data.isNotEmpty()) FeatureCard {
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
            AliMascotIllustration(AliPose.HouseholdCheck, Modifier.size(72.dp))
            Text("Ali's saving ideas", style = MaterialTheme.typography.titleLarge, modifier = Modifier.weight(1f))
        }
        val byHour = data.groupBy { it.at.atZone(ZoneId.systemDefault()).hour }
        val busiest = byHour.maxBy { it.value.map(EnergySample::kw).average() }
        InsightAction(Icons.Outlined.AcUnit, "Busy around ${hourLabel(busiest.key)}",
            "If cooling is on, use a comfortable setting and switch off fans in empty rooms.")
        val night = data.filter { it.at.atZone(ZoneId.systemDefault()).hour in 0..5 }
        if (night.size >= 24) {
            InsightAction(Icons.Outlined.PowerSettingsNew, "Overnight: ${number(night.map(EnergySample::kw).average())} kW",
                "Check unused TVs, lights and chargers before bed. Keep essentials on.")
        }
        InsightAction(Icons.Outlined.Savings, "Example: ${pesos(0.4 * rate)} / day",
            "50 W switched off for 8 hours = 0.40 kWh saved.")
        TextButton(onClick = { showInsightDetails = !showInsightDetails }) { Text(if (showInsightDetails) "Hide insight details" else "Why these ideas?") }
        if (showInsightDetails) Text("Busy hours and overnight averages come from whole-home readings; appliances aren't identified. The saving is a 50 W scenario at your selected rate, rather than a measured result. Moving the same usage to another hour alone won't reduce this flat-rate estimate. Keep refrigeration and medical equipment running.", style = MaterialTheme.typography.bodySmall)
        if (device.isSimulated) Text("These observations use simulated household data.", style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
private fun InsightAction(icon: androidx.compose.ui.graphics.vector.ImageVector, title: String, body: String) {
    Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
        EnergyIcon(icon)
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium)
            Text(body, style = MaterialTheme.typography.bodyMedium)
        }
    }
}

@Composable
internal fun AwayAlertsCard() {
    val context = LocalContext.current
    val prefs = remember { AwayMonitor.prefs(context) }
    var revision by remember { mutableIntStateOf(0) }
    val owner = LocalLifecycleOwner.current
    DisposableEffect(prefs, owner) {
        val listener = SharedPreferences.OnSharedPreferenceChangeListener { _, _ -> revision++ }
        val observer = LifecycleEventObserver { _, event -> if (event == Lifecycle.Event.ON_RESUME) revision++ }
        prefs.registerOnSharedPreferenceChangeListener(listener); owner.lifecycle.addObserver(observer)
        onDispose { prefs.unregisterOnSharedPreferenceChangeListener(listener); owner.lifecycle.removeObserver(observer) }
    }
    @Suppress("UNUSED_VARIABLE") val observeChanges = revision
    val scope = rememberCoroutineScope()
    var expanded by rememberSaveable { mutableStateOf(false) }
    var message by rememberSaveable { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    var threshold by rememberSaveable { mutableStateOf(prefs.getString("threshold", "0.3") ?: "0.3") }
    var candidate by remember { mutableStateOf<android.location.Location?>(null) }
    val token = remember { CancellationTokenSource() }
    DisposableEffect(Unit) { onDispose { token.cancel() } }
    val permission = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { grants ->
        message = if (grants.values.all { it }) "Permission granted. Continue setup below." else "Permission declined. Manual away mode is still available."
        revision++
    }
    val away = prefs.getBoolean("away", false)
    val automatic = prefs.getBoolean("auto", false)
    val automaticReady = automatic && AwayMonitor.locationAllowed(context) && AwayMonitor.notificationsAllowed(context)
    val notifications = AwayMonitor.notificationsAllowed(context)
    FeatureCard {
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
            EnergyIcon(Icons.Outlined.NotificationsActive)
            Column(Modifier.weight(1f)) {
                Text("Leaving home?", style = MaterialTheme.typography.titleMedium)
                Text(if (away) "Away mode on" else "Check what stays on", style = MaterialTheme.typography.bodySmall)
            }
        }
        Text("Ali can remind you if power stays above your limit after you leave.", style = MaterialTheme.typography.bodyMedium)
        if (!notifications) OutlinedButton(onClick = {
            if (Build.VERSION.SDK_INT >= 33 && context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED)
                permission.launch(arrayOf(Manifest.permission.POST_NOTIFICATIONS))
            else context.startActivity(Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS).putExtra(Settings.EXTRA_APP_PACKAGE, context.packageName))
        }) { Text("Allow notifications") }
        Button(onClick = { AwayMonitor.setAway(context, !away) }, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) {
            Text(if (away) "I'm home" else "I'm away — check my usage")
        }
        if (away) {
            Text(prefs.getString("status", null) ?: "Waiting for fresh readings after departure.", style = MaterialTheme.typography.bodySmall)
            TextButton(onClick = { AwayMonitor.checkNow(context) }) { Text("Check now") }
        }
        TextButton(onClick = { expanded = !expanded }) { Text(if (expanded) "Hide alert settings" else "Set up automatic departure alerts") }
        if (expanded) {
            Text("Two consecutive 15-minute readings above the limit trigger one reminder per departure. Checks run about every 15 minutes; Android and internet availability may delay them. A reminder checks household usage, not fire or appliance safety.", style = MaterialTheme.typography.bodySmall)
            Text("Only this phone's departure is detected. Others may still be home. Simulated or stale readings pause real alerts.", style = MaterialTheme.typography.bodySmall)
            OutlinedTextField(value = threshold, onValueChange = { threshold = it }, label = { Text("Away limit (kW)") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal), modifier = Modifier.fillMaxWidth())
            val limit = threshold.toDoubleOrNull()?.takeIf { it.isFinite() && it in 0.05..20.0 }
            Text("Start above your essential background usage. 0.30 kW = 300 W. Keep essential loads on.", style = MaterialTheme.typography.bodySmall)
            OutlinedButton(enabled = limit != null, onClick = { prefs.edit().putString("threshold", limit.toString()).apply(); message = "Away limit saved." }) { Text("Save away limit") }
            if (!automatic) {
                OutlinedButton(enabled = !busy, onClick = {
                    if (context.checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
                        permission.launch(arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION))
                    } else scope.launch {
                        busy = true
                        try { candidate = currentHome(context, token); if (candidate == null) message = "Couldn't get an accurate location. Turn on location and try outdoors." }
                        catch (e: CancellationException) { throw e }
                        catch (_: Exception) { message = "Couldn't get your location. Check location settings and try again." }
                        finally { busy = false }
                    }
                }) { Text(if (busy) "Finding location…" else "1 · Set home to my current location") }
                if (prefs.contains("lat")) Text("Home location saved on this phone.", style = MaterialTheme.typography.bodySmall)
                if (!AwayMonitor.locationAllowed(context)) {
                    Text("Automatic alerts need precise location and 'Allow all the time' so your phone can detect leaving a 200 m home area while SILIP is closed. Location stays on this phone and with Android's location service.", style = MaterialTheme.typography.bodySmall)
                    TextButton(onClick = {
                        if (Build.VERSION.SDK_INT == 29) permission.launch(arrayOf(Manifest.permission.ACCESS_BACKGROUND_LOCATION))
                        else context.startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:${context.packageName}")))
                    }) { Text("2 · Open location permission settings") }
                }
                Button(enabled = prefs.contains("lat") && AwayMonitor.locationAllowed(context) && notifications && !busy, onClick = {
                    scope.launch {
                        busy = true
                        try {
                            AwayMonitor.enableAutomatic(context, prefs.getString("lat", "")!!.toDouble(), prefs.getString("lon", "")!!.toDouble())
                            message = "Automatic alerts enabled."
                        } catch (e: CancellationException) { throw e }
                        catch (_: Exception) { message = "Couldn't enable departure detection. Check Google Play services, location and permissions, then try again." }
                        finally { busy = false }
                    }
                }) { Text("3 · Enable automatic alerts") }
            } else {
                Text(if (automaticReady) "Automatic departure detection on · 200 m home area" else "Automatic alerts paused · check location and notification permissions", style = MaterialTheme.typography.bodyMedium)
                TextButton(onClick = { scope.launch { AwayMonitor.disable(context) } }) { Text("Turn off automatic alerts") }
            }
            TextButton(enabled = notifications, onClick = { AwayMonitor.notify(context, demo = true) }) { Text("Send a demo notification") }
            prefs.getString("error", null)?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        }
        if (message.isNotBlank()) Text(message, style = MaterialTheme.typography.bodySmall)
    }
    candidate?.let { location ->
        AlertDialog(onDismissRequest = { candidate = null }, title = { Text("Are you at home now?") },
            text = { Text("Use this location for your 200 m home area? It is saved on this phone. You can turn detection off at any time.") },
            confirmButton = { TextButton(onClick = {
                prefs.edit().putString("lat", location.latitude.toString()).putString("lon", location.longitude.toString()).apply()
                candidate = null; message = "Home saved. Continue with location permission below."
            }) { Text("Yes, save home") } }, dismissButton = { TextButton(onClick = { candidate = null }) { Text("Cancel") } })
    }
}

@SuppressLint("MissingPermission")
private suspend fun currentHome(context: Context, token: CancellationTokenSource): android.location.Location? {
    val request = CurrentLocationRequest.Builder().setPriority(Priority.PRIORITY_HIGH_ACCURACY)
        .setMaxUpdateAgeMillis(0).setDurationMillis(20_000).build()
    return LocationServices.getFusedLocationProviderClient(context).getCurrentLocation(request, token.token).await()
        ?.takeIf { it.hasAccuracy() && it.accuracy <= 100f }
}

private fun number(value: Double, decimals: Int = 2) = String.format(Locale.getDefault(), "%.${decimals}f", value)
private fun pesos(value: Double) = "₱" + String.format(Locale.getDefault(), "%,.2f", value)
private fun time(at: Instant) = DateTimeFormatter.ofPattern("h:mm a", Locale.getDefault()).withZone(ZoneId.systemDefault()).format(at)
private fun dateTime(at: Instant) = DateTimeFormatter.ofPattern("MMM d, h:mm a", Locale.getDefault()).withZone(ZoneId.systemDefault()).format(at)
private fun hourLabel(hour: Int) = time(java.time.LocalDate.now().atTime(hour, 0).atZone(ZoneId.systemDefault()).toInstant())
