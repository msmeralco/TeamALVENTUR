package com.alventur.silipapp.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.ArrowForward
import androidx.compose.material.icons.automirrored.outlined.ReceiptLong
import androidx.compose.material.icons.automirrored.outlined.FactCheck
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.alventur.silipapp.data.remote.DeviceUsage
import com.alventur.silipapp.data.remote.HouseholdDashboardState
import com.alventur.silipapp.education.Lesson
import java.time.Duration
import java.time.Instant
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

/** Large, themed visual cues always paired with a short visible label. */
@Composable
internal fun EnergyIcon(icon: ImageVector, modifier: Modifier = Modifier) {
    Surface(modifier = modifier.size(56.dp), shape = RoundedCornerShape(18.dp),
        color = MaterialTheme.colorScheme.primaryContainer) {
        Box(contentAlignment = Alignment.Center) {
            Icon(icon, contentDescription = null, modifier = Modifier.size(30.dp),
                tint = MaterialTheme.colorScheme.onPrimaryContainer)
        }
    }
}

internal fun lessonIcon(id: String): ImageVector = when (id) {
    "phantom-loads" -> Icons.Outlined.PowerSettingsNew
    "cooling-wisely" -> Icons.Outlined.AcUnit
    "bill-basics" -> Icons.AutoMirrored.Outlined.ReceiptLong
    "leaving-home" -> Icons.Outlined.Home
    else -> Icons.Outlined.Lightbulb
}

@Composable
internal fun HouseholdSnapshot(state: HouseholdDashboardState, onRefresh: () -> Unit) {
    if (state !is HouseholdDashboardState.Loaded) {
        Card(shape = RoundedCornerShape(28.dp), modifier = Modifier.fillMaxWidth()) {
            Row(Modifier.padding(20.dp), verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                AliMascotIllustration(AliPose.HouseholdCheck, Modifier.size(80.dp))
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    when (state) {
                        HouseholdDashboardState.Loading -> {
                            Text("Checking your home…", style = MaterialTheme.typography.titleMedium)
                            LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
                        }
                        is HouseholdDashboardState.NotFound -> {
                            Text("Let's find your sensor", style = MaterialTheme.typography.titleMedium)
                            Text("Check the device ID in Settings.", style = MaterialTheme.typography.bodyMedium)
                        }
                        is HouseholdDashboardState.Error -> {
                            Text("Usage couldn't load", style = MaterialTheme.typography.titleMedium)
                            Text(state.message, style = MaterialTheme.typography.bodyMedium)
                        }
                    }
                    if (state != HouseholdDashboardState.Loading) {
                        OutlinedButton(onClick = onRefresh, modifier = Modifier.heightIn(min = 48.dp)) {
                            Icon(Icons.Outlined.Refresh, contentDescription = null)
                            Text("Try again", Modifier.padding(start = 8.dp))
                        }
                    }
                }
            }
        }
        return
    }
    val device = state.device
    val scheme = MaterialTheme.colorScheme
    Card(shape = RoundedCornerShape(28.dp), colors = CardDefaults.cardColors(containerColor = scheme.surface),
        border = CardDefaults.outlinedCardBorder(), modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                EnergyIcon(Icons.Outlined.Home)
                Column(Modifier.weight(1f)) {
                    Text("Your home's energy", style = MaterialTheme.typography.titleMedium)
                    Text("Last 7 days of readings", style = MaterialTheme.typography.bodySmall, color = scheme.onSurfaceVariant)
                }
                IconButton(onClick = onRefresh) {
                    Icon(Icons.Outlined.Refresh, contentDescription = "Refresh household readings")
                }
            }
            Text(if (device.points.isEmpty()) "Waiting for readings" else "${device.totalKwh.pretty()} kWh",
                style = MaterialTheme.typography.headlineLarge, fontWeight = FontWeight.ExtraBold)
            if (device.points.isNotEmpty()) {
                DailyEnergyBars(device)
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                Icon(if (device.isSimulated) Icons.Outlined.Science else Icons.Outlined.Sensors,
                    contentDescription = null, modifier = Modifier.size(20.dp), tint = scheme.primary)
                Text(if (device.isSimulated) "Simulated usage" else "Sensor readings",
                    style = MaterialTheme.typography.labelLarge, color = scheme.primary)
            }
            Text(freshnessLabel(device.lastSeenAt), style = MaterialTheme.typography.bodySmall,
                color = scheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun DailyEnergyBars(device: DeviceUsage) {
    val locale = LocalConfiguration.current.locales[0]
    // The API's points are 15-minute averages. Partial days stay visibly identified.
    val days = remember(device.points) {
        device.points.mapNotNull { point ->
            runCatching { OffsetDateTime.parse(point.timestamp).atZoneSameInstant(ZoneId.systemDefault()).toLocalDate() to point.powerKw * 0.25 }.getOrNull()
        }.groupBy({ it.first }, { it.second }).toSortedMap().entries.toList()
    }
    val maximum = days.maxOfOrNull { it.value.sum() }?.coerceAtLeast(0.01) ?: 1.0
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.Bottom) {
        days.forEach { (date, values) ->
            val energy = values.sum()
            Column(Modifier.weight(1f).semantics {
                contentDescription = "$date: ${energy.pretty()} kilowatt hours, ${values.size} readings"
            }, horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Box(Modifier.height(64.dp).fillMaxWidth(), contentAlignment = Alignment.BottomCenter) {
                    Box(Modifier.fillMaxWidth().height((energy / maximum * 60).coerceAtLeast(3.0).dp)
                        .background(MaterialTheme.colorScheme.primary, RoundedCornerShape(6.dp)))
                }
                Text(date.format(DateTimeFormatter.ofPattern("EEEEE", locale)),
                    style = MaterialTheme.typography.labelMedium)
            }
        }
    }
    Text("Daily kWh · first and last days may be partial", style = MaterialTheme.typography.bodySmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant)
}

@Composable
internal fun AliActionCard(onOpenUsage: () -> Unit) {
    Card(shape = RoundedCornerShape(28.dp), colors = CardDefaults.cardColors(
        containerColor = MaterialTheme.colorScheme.primaryContainer)) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                AliMascotIllustration(AliPose.HouseholdCheck, Modifier.size(96.dp))
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text("Let's spot your busy hours", style = MaterialTheme.typography.titleLarge,
                        color = MaterialTheme.colorScheme.onPrimaryContainer)
                    Text("Start with your home's usage pattern.", style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onPrimaryContainer)
                }
            }
            Button(onClick = onOpenUsage, modifier = Modifier.fillMaxWidth().heightIn(min = 52.dp)) {
                Text("Explore my usage", modifier = Modifier.weight(1f))
                Icon(Icons.AutoMirrored.Outlined.ArrowForward, contentDescription = null)
            }
        }
    }
}

@Composable
internal fun NextLessonCard(lesson: Lesson, onClick: () -> Unit) {
    Card(onClick = onClick, shape = RoundedCornerShape(24.dp), border = CardDefaults.outlinedCardBorder(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface), modifier = Modifier.fillMaxWidth()) {
        Row(Modifier.padding(16.dp), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
            EnergyIcon(lessonIcon(lesson.id))
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(lesson.title, style = MaterialTheme.typography.titleMedium)
                Text("${lesson.estimatedMinutes} min · +${lesson.points} XP", style = MaterialTheme.typography.bodySmall)
            }
            Icon(Icons.AutoMirrored.Outlined.ArrowForward, contentDescription = null)
        }
    }
}

@Composable
internal fun UsageMeaningCard() {
    Card(shape = RoundedCornerShape(24.dp), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
        Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            MeaningRow(Icons.Outlined.Speed, "kW = how fast", "Power used at a moment in time.")
            MeaningRow(Icons.Outlined.Bolt, "kWh = how much", "Energy used over a period of time.")
            MeaningRow(Icons.Outlined.Payments, "Pesos = estimated cost", "Needs your electricity rate first.")
        }
    }
}

@Composable
private fun MeaningRow(icon: ImageVector, title: String, detail: String) {
    Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
        EnergyIcon(icon)
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium)
            Text(detail, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
internal fun ReadingDetails(device: DeviceUsage) {
    var expanded by rememberSaveable { mutableStateOf(false) }
    OutlinedCard(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(24.dp)) {
        TextButton(onClick = { expanded = !expanded }, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) {
            Icon(Icons.Outlined.Info, contentDescription = null)
            Text(if (expanded) "Hide reading details" else "Reading details", Modifier.weight(1f))
            Icon(if (expanded) Icons.Outlined.ExpandLess else Icons.Outlined.ExpandMore, contentDescription = null)
        }
        if (expanded) Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Device · ${device.clampId}")
            Text("Transformer · ${device.transformerId}")
            Text("${device.points.size} intervals · 15 minutes each")
            Text("Whole-home usage. Individual appliances aren't identified.", style = MaterialTheme.typography.bodyMedium)
            Text("The seven-day window ends at the latest stored reading. A cost estimate needs a rate and measurement assumptions.",
                style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
internal fun GridEventVisual() {
    var expanded by rememberSaveable { mutableStateOf(false) }
    Card(shape = RoundedCornerShape(28.dp), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer)) {
        Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            PreviewBadge(label = "Demo concept")
            AliMascotIllustration(AliPose.Welcome, Modifier.size(144.dp))
            Text("Small shifts. Shared impact.", style = MaterialTheme.typography.headlineSmall)
            Text("Move a flexible task to a quieter hour.", style = MaterialTheme.typography.bodyLarge)
            Button(onClick = { expanded = !expanded }, modifier = Modifier.fillMaxWidth().heightIn(min = 52.dp)) {
                Text(if (expanded) "Close example" else "See an example")
            }
            if (expanded) {
                MeaningRow(Icons.Outlined.Schedule, "An invitation arrives", "Example: move laundry past the evening peak.")
                MeaningRow(Icons.Outlined.TouchApp, "You choose", "Join or skip. Keep essential appliances on.")
                MeaningRow(Icons.AutoMirrored.Outlined.FactCheck, "Results get checked", "A future program would verify the change before any reward.")
                Text("Illustration only · live events and payouts are not available.", style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

private fun Double.pretty() = String.format(Locale.getDefault(), "%.2f", this)

private fun freshnessLabel(timestamp: String?): String {
    if (timestamp == null) return "Waiting for the sensor's first report"
    return runCatching {
        val seen = OffsetDateTime.parse(timestamp)
        val stamp = seen.atZoneSameInstant(ZoneId.systemDefault())
            .format(DateTimeFormatter.ofPattern("MMM d · h:mm a", Locale.getDefault()))
        val stale = Duration.between(seen.toInstant(), Instant.now()).toMinutes() > 30
        "${if (stale) "Sensor out of date" else "Sensor last seen"} · $stamp"
    }.getOrDefault("Sensor report time unavailable")
}
