package com.alventur.silipapp.ui

import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.ArrowForward
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.alventur.silipapp.data.remote.HouseholdDashboardState
import com.alventur.silipapp.energy.SolarProfile
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale
import kotlin.math.roundToInt

private const val SOLAR_SOURCE = "https://www.meralco.com.ph/residential/energy-solutions/solar-and-renewables/solar-net-metering"
private const val OWN_USE_SOURCE = "https://www.meralco.com.ph/residential/energy-solutions/solar-and-renewables/distributed-energy-resources"

@Composable
internal fun SolarEntryCard(onClick: () -> Unit) {
    Card(onClick = onClick, modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.tertiaryContainer)) {
        Row(Modifier.padding(20.dp), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Outlined.SolarPower, contentDescription = null, modifier = Modifier.size(48.dp), tint = MaterialTheme.colorScheme.onTertiaryContainer)
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text("Make room for solar", style = MaterialTheme.typography.titleLarge)
                Text("Your daytime use. Your next steps.", style = MaterialTheme.typography.bodyMedium)
                Text("Explore solar", style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.Bold)
            }
            Icon(Icons.AutoMirrored.Outlined.ArrowForward, contentDescription = null)
        }
    }
}

@Composable
internal fun SolarIntroduction(onBack: () -> Unit) {
    OutlinedButton(onClick = onBack, modifier = Modifier.heightIn(min = 48.dp)) { Text("Back to Home") }
    Spacer(Modifier.height(12.dp))
    Card(shape = RoundedCornerShape(28.dp), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.tertiaryContainer)) {
        Row(Modifier.padding(20.dp), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
            AliMascotIllustration(AliPose.Learning, Modifier.size(96.dp))
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Icon(Icons.Outlined.SolarPower, contentDescription = null, modifier = Modifier.size(36.dp))
                Text("Your solar journey", style = MaterialTheme.typography.headlineSmall)
                Text("Understand your home before choosing a system.", style = MaterialTheme.typography.bodyMedium)
            }
        }
    }
}

@Composable
private fun SolarCard(content: @Composable ColumnScope.() -> Unit) {
    Card(Modifier.fillMaxWidth(), shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface), border = CardDefaults.outlinedCardBorder()) {
        Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp), content = content)
    }
}

@Composable
internal fun SolarDaytimeCard(state: HouseholdDashboardState) {
    val device = (state as? HouseholdDashboardState.Loaded)?.device
    val profile = remember(device?.points) { device?.let { SolarProfile.from(it.points) } }
    val rate = selectedEnergyRate()
    var coverage by rememberSaveable { mutableFloatStateOf(0.5f) }
    var details by rememberSaveable { mutableStateOf(false) }
    SolarCard {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            EnergyIcon(Icons.Outlined.WbSunny)
            Text("When does your home use energy?", style = MaterialTheme.typography.titleLarge, modifier = Modifier.weight(1f))
        }
        if (profile == null || profile.daytimeIntervals == 0) {
            Text("Daytime readings will help you explore solar.", style = MaterialTheme.typography.bodyLarge)
            Text("You can start the preparation checklist below while your sensor collects data.", style = MaterialTheme.typography.bodyMedium)
        } else {
            Text("${(profile.daytimeShare * 100).roundToInt()}% during 9 AM–4 PM", style = MaterialTheme.typography.headlineSmall)
            LinearProgressIndicator(progress = { profile.daytimeShare.toFloat() }, modifier = Modifier.fillMaxWidth().height(12.dp))
            Text("${solarNumber(profile.daytimeKwh)} kWh daytime · ${solarNumber(profile.otherKwh)} kWh at other times", style = MaterialTheme.typography.bodyMedium)
            Text("${if (device?.isSimulated == true) "Simulated usage" else "Sensor readings"} · ${solarDate(profile.first)}–${solarDate(profile.last)}", style = MaterialTheme.typography.bodySmall)
            Text("This is a daytime-use window, not measured sunshine or solar production. Missing readings are excluded.", style = MaterialTheme.typography.bodySmall)
            Text("Try a solar what-if", style = MaterialTheme.typography.titleLarge)
            Text("If solar supplied ${(coverage * 100).roundToInt()}% of your recorded daytime energy…", style = MaterialTheme.typography.bodyMedium)
            Slider(value = coverage, onValueChange = { coverage = it }, valueRange = 0f..1f, steps = 19,
                modifier = Modifier.fillMaxWidth().semantics {
                    contentDescription = "Assumed share of daytime energy supplied by solar"
                })
            val avoided = profile.avoidedImportKwh(coverage.toDouble())
            Text("${solarNumber(avoided)} kWh of grid imports avoided", style = MaterialTheme.typography.titleMedium)
            Text("About ₱${solarNumber(avoided * rate)} in energy cost for this recorded period", style = MaterialTheme.typography.bodyMedium)
            Text("Illustrative scenario · system costs and export credits excluded", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.primary)
            TextButton(onClick = { details = !details }) { Text(if (details) "Hide assumptions" else "How to read this scenario") }
            if (details) {
                Text("The slider assumes solar is available at the same times as the chosen share of daytime demand. It does not size panels or predict production, savings, payback or roof suitability. The cost uses your selected ₱${solarNumber(rate)} per kWh estimate, rather than an exact avoided-charge calculation.", style = MaterialTheme.typography.bodySmall)
                Text("An installer needs roof area, shading, local weather, equipment and interval demand. If you already have solar, separate generation/import/export readings are needed to assess actual performance. These household readings cannot measure those flows separately.", style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

@Composable
internal fun SolarHowItWorks() {
    SolarCard {
        Text("Follow the sunshine", style = MaterialTheme.typography.titleLarge)
        SolarStep(Icons.Outlined.SolarPower, "Generate", "Panels produce electricity when sunlight is available.")
        SolarStep(Icons.Outlined.Home, "Use it at home", "On-site generation serves the home first; the grid supplies any shortfall.")
        SolarStep(Icons.Outlined.SwapHoriz, "Handle the extra", "Approved exports may earn bill credits. Export rates differ from retail import rates.")
        Text("A practical first step", style = MaterialTheme.typography.titleMedium)
        Text("If you have solar, consider moving flexible tasks into generating hours. For a home empty on weekdays, ask an installer about matching system size to daytime demand, storage and approved export options.", style = MaterialTheme.typography.bodyMedium)
    }
}

@Composable
private fun SolarStep(icon: androidx.compose.ui.graphics.vector.ImageVector, title: String, body: String) {
    Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
        EnergyIcon(icon)
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium)
            Text(body, style = MaterialTheme.typography.bodyMedium)
        }
    }
}

@Composable
internal fun SolarPreparationCard() {
    val context = LocalContext.current
    val prefs = remember { context.getSharedPreferences("silip_solar_preparation", Context.MODE_PRIVATE) }
    val ids = listOf("review-use", "installer-questions", "connection-guide")
    var completed by remember { mutableStateOf(ids.filter { prefs.getBoolean(it, false) }.toSet()) }
    val steps = listOf(
        "review-use" to "I reviewed my daytime energy use",
        "installer-questions" to "I prepared questions about my roof, shade and budget",
        "connection-guide" to "I checked Meralco's connection options"
    )
    SolarCard {
        Text("Your next steps", style = MaterialTheme.typography.titleLarge)
        Text("${completed.size} of 3 prepared · saved on this phone", style = MaterialTheme.typography.bodySmall)
        LinearProgressIndicator(progress = { completed.size / 3f }, modifier = Modifier.fillMaxWidth())
        steps.forEach { (id, label) ->
            Row(Modifier.fillMaxWidth().heightIn(min = 56.dp).toggleable(value = id in completed, role = Role.Checkbox, onValueChange = { checked ->
                completed = if (checked) completed + id else completed - id
                prefs.edit().putBoolean(id, checked).apply()
            }), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Checkbox(checked = id in completed, onCheckedChange = null)
                Text(label, modifier = Modifier.weight(1f), style = MaterialTheme.typography.bodyMedium)
            }
        }
        Text("Self-reported preparation · this does not confirm solar eligibility or installation approval.", style = MaterialTheme.typography.bodySmall)
        Button(onClick = { openSolarGuide(context, SOLAR_SOURCE) }, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) { Text("Meralco solar & net metering") }
        OutlinedButton(onClick = { openSolarGuide(context, OWN_USE_SOURCE) }, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) { Text("Explore own-use solar options") }
    }
}

private fun openSolarGuide(context: Context, url: String) { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url))) }
private fun solarNumber(value: Double) = String.format(Locale.getDefault(), "%,.2f", value)
private fun solarDate(at: java.time.Instant) = DateTimeFormatter.ofPattern("MMM d", Locale.getDefault()).withZone(ZoneId.systemDefault()).format(at)
