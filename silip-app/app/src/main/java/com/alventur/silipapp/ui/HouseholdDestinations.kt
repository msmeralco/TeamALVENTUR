package com.alventur.silipapp.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.ArrowForward
import androidx.compose.material.icons.automirrored.outlined.ArrowBack
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.alventur.silipapp.data.remote.DeviceUsage
import com.alventur.silipapp.data.remote.HouseholdDashboardState
import com.alventur.silipapp.energy.EnergyAnalysis
import java.time.Duration
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

/** Home answers "what should I do?" with a companion, a compact summary and a route to detail. */
@Composable
internal fun HomeCompanionSummary(
    state: HouseholdDashboardState,
    userName: String,
    onOpenUsage: () -> Unit,
    onRefresh: () -> Unit
) {
    val scheme = MaterialTheme.colorScheme
    val rate = selectedEnergyRate()
    Card(Modifier.fillMaxWidth(), shape = RoundedCornerShape(28.dp),
        colors = CardDefaults.cardColors(containerColor = scheme.primaryContainer)) {
        Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
                AliMascotIllustration(AliPose.Welcome, Modifier.size(96.dp))
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(userName.takeIf(String::isNotBlank)?.let { "Hi, $it!" } ?: "Welcome home!",
                        style = MaterialTheme.typography.headlineSmall, color = scheme.onPrimaryContainer)
                    Text("A small step toward smarter energy.", style = MaterialTheme.typography.bodyMedium,
                        color = scheme.onPrimaryContainer)
                }
                IconButton(onClick = onRefresh, enabled = state != HouseholdDashboardState.Loading) {
                    Icon(Icons.Outlined.Refresh, contentDescription = "Refresh household summary", tint = scheme.onPrimaryContainer)
                }
            }
            if (state is HouseholdDashboardState.Loaded) {
                val device = state.device
                if (device.points.isNotEmpty()) {
                    Text("Last 7 days · estimated cost", style = MaterialTheme.typography.labelLarge, color = scheme.onPrimaryContainer)
                    Text("₱${amount(device.totalKwh * rate)}", style = MaterialTheme.typography.headlineLarge,
                        fontWeight = FontWeight.ExtraBold, color = scheme.onPrimaryContainer)
                    Text("${amount(device.totalKwh)} kWh · ${if (device.isSimulated) "simulated usage" else "sensor readings"}",
                        style = MaterialTheme.typography.bodyMedium, color = scheme.onPrimaryContainer)
                    Text("₱${String.format(Locale.ROOT, "%.4f", rate)}/kWh · full calculation in Usage", style = MaterialTheme.typography.bodySmall,
                        color = scheme.onPrimaryContainer)
                } else Text("Your sensor's first reading will appear here.", color = scheme.onPrimaryContainer)
                Text(sensorStatus(device.lastSeenAt), style = MaterialTheme.typography.bodySmall, color = scheme.onPrimaryContainer)
                Button(onClick = onOpenUsage, modifier = Modifier.fillMaxWidth().heightIn(min = 52.dp)) {
                    Text("See my usage breakdown", Modifier.weight(1f))
                    Icon(Icons.AutoMirrored.Outlined.ArrowForward, contentDescription = null)
                }
            }
        }
    }
    if (state !is HouseholdDashboardState.Loaded) {
        Spacer(Modifier.height(16.dp))
        HouseholdSnapshot(state, onRefresh)
    }
}

private data class UsageBar(val at: Instant, val kwh: Double, val count: Int)

/** Usage answers "when and how much?" with inspectable historical data before advice or settings. */
@Composable
internal fun UsageExplorer(device: DeviceUsage, onRefresh: () -> Unit) {
    var hoursOnly by rememberSaveable(device.clampId) { mutableStateOf(false) }
    var inPesos by rememberSaveable(device.clampId) { mutableStateOf(false) }
    var selectedIndex by rememberSaveable(device.clampId, hoursOnly) { mutableIntStateOf(-1) }
    val rate = selectedEnergyRate()
    val data = remember(device.points) { EnergyAnalysis.samples(device.points) }
    val zone = ZoneId.systemDefault()
    val bars = remember(data, hoursOnly, zone) {
        val end = data.lastOrNull()?.at
        val window = if (hoursOnly && end != null) data.filter { it.at > end.minusSeconds(86400) } else data
        window.groupBy { sample ->
            val local = sample.at.atZone(zone)
            if (hoursOnly) local.toLocalDate().atTime(local.hour / 4 * 4, 0).atZone(zone).toInstant()
            else local.toLocalDate().atStartOfDay(zone).toInstant()
        }.toSortedMap().map { (at, samples) -> UsageBar(at, samples.sumOf { it.kw * 0.25 }, samples.size) }
    }
    val currentIndex = (if (selectedIndex < 0) bars.lastIndex else selectedIndex).coerceIn(0, bars.lastIndex.coerceAtLeast(0))
    val selected = bars.getOrNull(currentIndex)
    val total = bars.sumOf { it.kwh }
    val highest = bars.maxOfOrNull { it.kwh }?.coerceAtLeast(0.001) ?: 1.0
    val scheme = MaterialTheme.colorScheme
    Card(Modifier.fillMaxWidth(), shape = RoundedCornerShape(28.dp),
        colors = CardDefaults.cardColors(containerColor = scheme.surface), border = CardDefaults.outlinedCardBorder()) {
        Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("Explore your usage", style = MaterialTheme.typography.headlineSmall, modifier = Modifier.weight(1f))
                IconButton(onClick = onRefresh) { Icon(Icons.Outlined.Refresh, contentDescription = "Refresh usage chart") }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                FilterChip(selected = !hoursOnly, onClick = { hoursOnly = false }, label = { Text("7 days") }, modifier = Modifier.weight(1f).heightIn(min = 48.dp))
                FilterChip(selected = hoursOnly, onClick = { hoursOnly = true }, label = { Text("24 hours") }, modifier = Modifier.weight(1f).heightIn(min = 48.dp))
            }
            if (data.isEmpty()) {
                Text("Waiting for enough readings to draw your chart.", style = MaterialTheme.typography.bodyMedium)
            } else {
                Text(if (inPesos) "₱${amount(total * rate)}" else "${amount(total)} kWh",
                    style = MaterialTheme.typography.headlineLarge, fontWeight = FontWeight.ExtraBold)
                Text(if (hoursOnly) "24-hour window ending ${stamp(data.last().at)}"
                    else "${shortDate(data.first().at)} – ${shortDate(data.last().at)} · stored readings",
                    style = MaterialTheme.typography.bodySmall)
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    FilterChip(selected = !inPesos, onClick = { inPesos = false }, label = { Text("Energy · kWh") })
                    FilterChip(selected = inPesos, onClick = { inPesos = true }, label = { Text("Cost · ₱") })
                }
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp), verticalAlignment = Alignment.Bottom) {
                    bars.forEachIndexed { index, bar ->
                        val isSelected = index == currentIndex
                        Column(Modifier.weight(1f)
                            .selectable(isSelected, role = Role.RadioButton, onClick = { selectedIndex = index })
                            .semantics { contentDescription = "${stamp(bar.at)}, ${amount(bar.kwh)} kilowatt hours, estimated ${amount(bar.kwh * rate)} pesos, ${bar.count} readings" }
                            .padding(vertical = 8.dp), horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Box(Modifier.fillMaxWidth().height(112.dp), contentAlignment = Alignment.BottomCenter) {
                                Box(Modifier.fillMaxWidth().padding(horizontal = 2.dp)
                                    .height((bar.kwh / highest * 104).coerceAtLeast(3.0).dp)
                                    .background(scheme.primary, RoundedCornerShape(6.dp))
                                    .then(if (isSelected) Modifier.border(2.dp, scheme.onSurface, RoundedCornerShape(6.dp)) else Modifier))
                            }
                            Text(if (hoursOnly) bar.at.atZone(zone).hour.toString().padStart(2, '0') else bar.at.atZone(zone).dayOfMonth.toString(),
                                style = MaterialTheme.typography.labelLarge, fontWeight = if (isSelected) FontWeight.ExtraBold else FontWeight.Normal)
                        }
                    }
                }
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(onClick = { selectedIndex = currentIndex - 1 }, enabled = currentIndex > 0,
                        modifier = Modifier.weight(1f).heightIn(min = 48.dp)) {
                        Icon(Icons.AutoMirrored.Outlined.ArrowBack, contentDescription = null)
                        Text("Earlier", Modifier.padding(start = 8.dp))
                    }
                    OutlinedButton(onClick = { selectedIndex = currentIndex + 1 }, enabled = currentIndex < bars.lastIndex,
                        modifier = Modifier.weight(1f).heightIn(min = 48.dp)) {
                        Text("Later", Modifier.padding(end = 8.dp))
                        Icon(Icons.AutoMirrored.Outlined.ArrowForward, contentDescription = null)
                    }
                }
                if (selected != null) {
                    Surface(shape = RoundedCornerShape(16.dp), color = scheme.primaryContainer) {
                        Column(Modifier.fillMaxWidth().padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            Text("Selected · ${if (hoursOnly) stamp(selected.at) + " (4-hour group)" else shortDate(selected.at)}", style = MaterialTheme.typography.labelLarge)
                            Text(if (inPesos) "₱${amount(selected.kwh * rate)} estimated" else "${amount(selected.kwh)} kWh", style = MaterialTheme.typography.titleLarge)
                            Text("${selected.count} × 15-minute readings", style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
                Text(if (hoursOnly) "Hour labels use the 24-hour clock. Tap a bar for details." else "Bar labels are calendar dates. Tap a day for details.", style = MaterialTheme.typography.bodySmall)
                Text("${if (device.isSimulated) "Simulated usage" else "Sensor readings"} · boundary groups may be partial", style = MaterialTheme.typography.bodySmall, color = scheme.primary)
                Text(sensorStatus(device.lastSeenAt), style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

private fun amount(value: Double) = String.format(Locale.getDefault(), "%,.2f", value)
private fun shortDate(at: Instant) = DateTimeFormatter.ofPattern("MMM d", Locale.getDefault()).withZone(ZoneId.systemDefault()).format(at)
private fun stamp(at: Instant) = DateTimeFormatter.ofPattern("MMM d, h:mm a", Locale.getDefault()).withZone(ZoneId.systemDefault()).format(at)
private fun sensorStatus(timestamp: String?): String {
    val seen = timestamp?.let { runCatching { Instant.parse(it) }.getOrNull() } ?: return "Waiting for the sensor's first report"
    val old = Duration.between(seen, Instant.now()).seconds !in 0..1800
    return "${if (old) "Sensor out of date" else "Sensor last seen"} · ${stamp(seen)}"
}
