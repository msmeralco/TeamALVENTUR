package com.alventur.silipapp.ui.usage

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.ArrowBack
import androidx.compose.material.icons.automirrored.outlined.ArrowForward
import androidx.compose.material.icons.outlined.Bedtime
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.Schedule
import androidx.compose.material.icons.outlined.ShowChart
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.alventur.silipapp.data.demo.DemoLabels
import com.alventur.silipapp.data.local.ProgressStore
import com.alventur.silipapp.data.remote.DeviceUsage
import com.alventur.silipapp.energy.EnergyAnalysis
import com.alventur.silipapp.energy.EnergySample
import com.alventur.silipapp.ui.AliPose
import com.alventur.silipapp.ui.PreviewBadge
import com.alventur.silipapp.ui.design.AnimatedAli
import com.alventur.silipapp.ui.design.AnimatedNumber
import com.alventur.silipapp.ui.design.AnimatedPesos
import com.alventur.silipapp.ui.design.ProgressRing
import com.alventur.silipapp.ui.design.SilipMotion
import com.alventur.silipapp.ui.design.formatPesos
import com.alventur.silipapp.ui.design.pressScale
import com.alventur.silipapp.ui.design.rememberHaptics
import com.alventur.silipapp.ui.design.rememberReduceMotion
import java.time.Duration
import java.time.Instant
import java.time.YearMonth
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale
import kotlin.math.max
import kotlin.math.roundToInt

/*
 * Usage, redesigned: "when does my home use energy, and what will this month cost?"
 *
 * One card answers the question at a glance (period switch, unit switch, an animated total and a chart
 * you scrub with a finger), then three insight chips and a month-end outlook against the budget from
 * onboarding. Ale's forecast, cost-calculation and reading-detail cards stay below on the Usage page.
 *
 * Truth rules: peso values are estimates (kWh × the user's bill rate or the dated Meralco benchmark);
 * the clamp sees whole-home power, so insights name times, not appliances; simulated data is labeled.
 */

private enum class Period(val label: String) { Today("Today"), Week("7 days") }
private enum class Measure(val label: String) { Energy("kWh"), Pesos("₱") }

private data class Bar(val start: Instant, val kwh: Double, val readings: Int)

private val DayFormat: DateTimeFormatter = DateTimeFormatter.ofPattern("EEE, MMM d", Locale.US)
private val ShortDay: DateTimeFormatter = DateTimeFormatter.ofPattern("EEE", Locale.US)
private val HourFormat: DateTimeFormatter = DateTimeFormatter.ofPattern("h a", Locale.US)
private val StampFormat: DateTimeFormatter = DateTimeFormatter.ofPattern("MMM d, h:mm a", Locale.US)

/** The new top of the Usage page. Reads rate and budget from on-device progress. */
@Composable
internal fun UsageDashboard(device: DeviceUsage, onRefresh: () -> Unit) {
    val context = LocalContext.current
    val store = remember(context) { ProgressStore.get(context) }
    val progress by store.progress.collectAsState()
    val rate = remember(progress) { store.ratePhpPerKwh() }
    val zone = ZoneId.systemDefault()
    val samples = remember(device.points) { EnergyAnalysis.samples(device.points).sortedBy { it.at } }

    var period by rememberSaveable(device.clampId) { mutableStateOf(Period.Today) }
    var unit by rememberSaveable(device.clampId) { mutableStateOf(Measure.Pesos) }
    val bars = remember(samples, period, zone) { barsFor(samples, period, zone) }

    Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
        Header(simulated = device.isSimulated, onRefresh = onRefresh)
        if (samples.isEmpty()) {
            EmptyState()
            return@Column
        }
        ChartCard(
            bars = bars,
            period = period,
            unit = unit,
            rate = rate,
            dailyBudget = progress.profile.dailyBudgetPhp,
            zone = zone,
            onPeriod = { period = it },
            onUnit = { unit = it }
        )
        InsightChips(samples = samples, bars = bars, period = period, zone = zone)
        MonthOutlook(
            samples = samples,
            rate = rate,
            monthlyBudget = progress.profile.monthlyBudgetPhp,
            simulated = device.isSimulated,
            zone = zone
        )
        SensorLine(device)
    }
}

/* ---------- Data ---------- */

private fun barsFor(samples: List<EnergySample>, period: Period, zone: ZoneId): List<Bar> {
    val end = samples.lastOrNull()?.at ?: return emptyList()
    return when (period) {
        Period.Today -> {
            val from = end.minus(Duration.ofHours(24))
            samples.filter { it.at > from }
                .groupBy { it.at.atZone(zone).withMinute(0).withSecond(0).withNano(0).toInstant() }
                .toSortedMap()
                .map { (start, group) -> Bar(start, group.sumOf { it.kw * 0.25 }, group.size) }
        }
        Period.Week -> {
            val from = end.minus(Duration.ofDays(7))
            samples.filter { it.at > from }
                .groupBy { it.at.atZone(zone).toLocalDate().atStartOfDay(zone).toInstant() }
                .toSortedMap()
                .map { (start, group) -> Bar(start, group.sumOf { it.kw * 0.25 }, group.size) }
        }
    }
}

private fun valueOf(bar: Bar, unit: Measure, rate: Double) = if (unit == Measure.Pesos) bar.kwh * rate else bar.kwh

private fun barTitle(bar: Bar, period: Period, zone: ZoneId): String {
    val local = bar.start.atZone(zone)
    return when (period) {
        Period.Today -> "${local.format(HourFormat)}–${local.plusHours(1).format(HourFormat)}"
        Period.Week -> local.format(DayFormat)
    }
}

private fun kwh(value: Double) = String.format(Locale.US, "%.2f kWh", value)

/* ---------- Header ---------- */

@Composable
private fun Header(simulated: Boolean, onRefresh: () -> Unit) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        AnimatedAli(pose = AliPose.HouseholdCheck, size = 64.dp)
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Text("Your usage", style = MaterialTheme.typography.headlineSmall, modifier = Modifier.semantics { heading() })
            Text(
                "When your home uses energy, and what it costs.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            if (simulated) PreviewBadge(label = DemoLabels.SIMULATED)
        }
        IconButton(onClick = onRefresh) { Icon(Icons.Outlined.Refresh, contentDescription = "Refresh usage") }
    }
}

@Composable
private fun EmptyState() {
    Card(
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = CardDefaults.outlinedCardBorder(),
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(Modifier.padding(18.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            AnimatedAli(pose = AliPose.Learning, size = 56.dp)
            Text(
                "Ali is waiting for the clamp's first readings. Your chart appears after about an hour.",
                style = MaterialTheme.typography.bodyLarge
            )
        }
    }
}

/* ---------- Chart card ---------- */

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ChartCard(
    bars: List<Bar>,
    period: Period,
    unit: Measure,
    rate: Double,
    dailyBudget: Double?,
    zone: ZoneId,
    onPeriod: (Period) -> Unit,
    onUnit: (Measure) -> Unit
) {
    val haptics = rememberHaptics()
    var selected by rememberSaveable(period, bars.size) { mutableIntStateOf(bars.lastIndex) }
    val index = selected.coerceIn(0, max(0, bars.lastIndex))
    val total = bars.sumOf { valueOf(it, unit, rate) }
    val peak = bars.indices.maxByOrNull { bars[it].kwh } ?: -1
    // Budget line only where it means something: daily budget against daily bars in pesos.
    val budgetLine = if (period == Period.Week && unit == Measure.Pesos) dailyBudget else null

    Card(
        shape = RoundedCornerShape(28.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = CardDefaults.outlinedCardBorder(),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            SingleChoiceSegmentedButtonRow(Modifier.fillMaxWidth()) {
                Period.entries.forEachIndexed { i, p ->
                    SegmentedButton(
                        selected = period == p,
                        onClick = { haptics.select(); onPeriod(p) },
                        shape = SegmentedButtonDefaults.itemShape(i, Period.entries.size),
                        modifier = Modifier.heightIn(min = 48.dp)
                    ) { Text(p.label) }
                }
            }

            Row(verticalAlignment = Alignment.Bottom) {
                Column(Modifier.weight(1f)) {
                    Text(
                        if (period == Period.Today) "Last 24 hours" else "Last 7 days",
                        style = MaterialTheme.typography.labelLarge,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    val totalStyle = MaterialTheme.typography.displaySmall.copy(
                        fontFamily = FontFamily.Monospace, fontWeight = FontWeight.SemiBold
                    )
                    if (unit == Measure.Pesos) {
                        AnimatedPesos(amount = total, decimals = 2, style = totalStyle)
                    } else {
                        AnimatedNumber(value = total, format = { kwh(it) }, style = totalStyle)
                    }
                    Text(
                        if (unit == Measure.Pesos) "Estimate at ${formatPesos(rate)}/kWh" else "Energy measured by the clamp",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                SingleChoiceSegmentedButtonRow {
                    Measure.entries.forEachIndexed { i, u ->
                        SegmentedButton(
                            selected = unit == u,
                            onClick = { haptics.select(); onUnit(u) },
                            shape = SegmentedButtonDefaults.itemShape(i, Measure.entries.size),
                            modifier = Modifier.heightIn(min = 48.dp)
                        ) { Text(u.label) }
                    }
                }
            }

            // Selected bar detail: changes as the finger moves across the chart.
            val bar = bars.getOrNull(index)
            AnimatedContent(
                targetState = index,
                transitionSpec = { fadeIn(tween(SilipMotion.SHORT)) togetherWith fadeOut(tween(SilipMotion.SHORT)) },
                label = "selected-bar"
            ) { i ->
                val b = bars.getOrNull(i)
                Surface(
                    shape = RoundedCornerShape(16.dp),
                    color = if (i == peak) MaterialTheme.colorScheme.tertiaryContainer else MaterialTheme.colorScheme.primaryContainer,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(Modifier.padding(horizontal = 14.dp, vertical = 10.dp), verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f)) {
                            Text(
                                if (b != null) barTitle(b, period, zone) else "",
                                style = MaterialTheme.typography.labelLarge
                            )
                            Text(
                                if (b != null) "${kwh(b.kwh)} · ${formatPesos(b.kwh * rate)} est." else "",
                                style = MaterialTheme.typography.titleMedium
                            )
                        }
                        if (i == peak) {
                            Text("Peak", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.tertiary)
                        }
                    }
                }
            }

            BarChart(
                values = bars.map { valueOf(it, unit, rate) },
                selected = index,
                peak = peak,
                budgetLine = budgetLine,
                animationKey = "$period-$unit",
                onSelect = { i ->
                    if (i != index) {
                        haptics.tick()
                        selected = i
                    }
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(168.dp)
                    .semantics {
                        contentDescription = "Usage chart, ${bars.size} bars. " +
                            (bar?.let { "Selected ${barTitle(it, period, zone)}, ${kwh(it.kwh)}." } ?: "") +
                            " Use the earlier and later buttons to move."
                    }
            )
            AxisLabels(bars = bars, period = period, zone = zone)

            if (budgetLine != null) {
                Text(
                    "Dashed line: your daily budget of ${formatPesos(budgetLine, 0)}.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            // Buttons for TalkBack and anyone who prefers taps over dragging.
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                StepButton("Earlier", Icons.AutoMirrored.Outlined.ArrowBack, enabled = index > 0, Modifier.weight(1f)) {
                    haptics.tick(); selected = index - 1
                }
                StepButton("Later", Icons.AutoMirrored.Outlined.ArrowForward, enabled = index < bars.lastIndex, Modifier.weight(1f)) {
                    haptics.tick(); selected = index + 1
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun StepButton(label: String, icon: ImageVector, enabled: Boolean, modifier: Modifier, onClick: () -> Unit) {
    Surface(
        onClick = onClick,
        enabled = enabled,
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.surfaceVariant,
        modifier = modifier.heightIn(min = 48.dp).pressScale()
    ) {
        Row(
            Modifier.padding(12.dp),
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(icon, contentDescription = null, modifier = Modifier.size(18.dp))
            Text(label, Modifier.padding(start = 6.dp), style = MaterialTheme.typography.labelLarge)
        }
    }
}

/**
 * Bars grow in when the period or unit changes. Tap or drag across to select; the caller adds a haptic
 * tick per bar. The peak bar uses the caution color (with the "Peak" word in the detail row above).
 */
@Composable
private fun BarChart(
    values: List<Double>,
    selected: Int,
    peak: Int,
    budgetLine: Double?,
    animationKey: String,
    onSelect: (Int) -> Unit,
    modifier: Modifier = Modifier
) {
    val reduceMotion = rememberReduceMotion()
    val grow = remember { Animatable(0f) }
    LaunchedEffect(animationKey, values.size) {
        if (reduceMotion) grow.snapTo(1f) else {
            grow.snapTo(0f)
            grow.animateTo(1f, tween(SilipMotion.COUNT, easing = SilipMotion.EnterEasing))
        }
    }
    val select by rememberUpdatedState(onSelect)
    val scheme = MaterialTheme.colorScheme
    val barColor = scheme.primary
    val dimColor = scheme.primary.copy(alpha = 0.45f)
    val peakColor = scheme.tertiary
    val lineColor = scheme.onSurfaceVariant
    val ceiling = max(values.maxOrNull() ?: 0.0, budgetLine ?: 0.0).coerceAtLeast(0.001)

    fun indexAt(x: Float, width: Float): Int =
        if (values.isEmpty()) 0 else ((x / width) * values.size).toInt().coerceIn(0, values.lastIndex)

    Canvas(
        modifier
            .pointerInput(values.size) {
                detectTapGestures { offset -> select(indexAt(offset.x, size.width.toFloat())) }
            }
            .pointerInput(values.size) {
                detectHorizontalDragGestures { change, _ ->
                    change.consume()
                    select(indexAt(change.position.x, size.width.toFloat()))
                }
            }
    ) {
        if (values.isEmpty()) return@Canvas
        val slot = size.width / values.size
        val gap = (slot * 0.18f).coerceAtMost(8.dp.toPx())
        val barWidth = slot - gap
        values.forEachIndexed { i, v ->
            val h = (v / ceiling).toFloat() * size.height * grow.value
            val color = when {
                i == peak -> peakColor
                i == selected -> barColor
                else -> dimColor
            }
            drawRoundRect(
                color = color,
                topLeft = Offset(i * slot + gap / 2, size.height - max(h, 3.dp.toPx())),
                size = Size(barWidth, max(h, 3.dp.toPx())),
                cornerRadius = CornerRadius(6.dp.toPx(), 6.dp.toPx())
            )
        }
        // Selection marker: a thin line above the selected bar.
        val sx = selected * slot + slot / 2
        drawLine(lineColor, Offset(sx, 0f), Offset(sx, 6.dp.toPx()), strokeWidth = 2.dp.toPx())
        if (budgetLine != null) {
            val y = size.height - (budgetLine / ceiling).toFloat() * size.height
            drawLine(
                color = lineColor,
                start = Offset(0f, y),
                end = Offset(size.width, y),
                strokeWidth = 1.5.dp.toPx(),
                pathEffect = PathEffect.dashPathEffect(floatArrayOf(10f, 8f))
            )
        }
    }
}

@Composable
private fun AxisLabels(bars: List<Bar>, period: Period, zone: ZoneId) {
    val every = if (period == Period.Today) 6 else 1
    Row(Modifier.fillMaxWidth()) {
        bars.forEachIndexed { i, bar ->
            val local = bar.start.atZone(zone)
            Text(
                text = if (i % every == 0) {
                    if (period == Period.Today) local.format(HourFormat) else local.format(ShortDay)
                } else "",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center,
                maxLines = 1,
                softWrap = false,
                modifier = Modifier.weight(1f)
            )
        }
    }
}

/* ---------- Insights ---------- */

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun InsightChips(samples: List<EnergySample>, bars: List<Bar>, period: Period, zone: ZoneId) {
    val peak = bars.maxByOrNull { it.kwh }
    // "Always on": the quietest hour between 1 and 5 AM, as average kW (fridge, router, standby).
    val night = samples.filter { it.at.atZone(zone).hour in 1..4 }
    val alwaysOnKw = night.groupBy { it.at.atZone(zone).toLocalDate() }
        .values.map { day -> day.map { it.kw }.average() }.minOrNull()
    val perDay = if (period == Period.Week && bars.isNotEmpty()) bars.sumOf { it.kwh } / bars.size else null

    FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        if (peak != null) {
            Insight(
                icon = Icons.Outlined.ShowChart,
                title = if (period == Period.Today) "Busiest hour" else "Busiest day",
                body = barTitle(peak, period, zone)
            )
        }
        if (alwaysOnKw != null) {
            Insight(
                icon = Icons.Outlined.Bedtime,
                title = "Always on at night",
                body = String.format(Locale.US, "%.2f kW", alwaysOnKw)
            )
        }
        if (perDay != null) {
            Insight(icon = Icons.Outlined.Schedule, title = "Average day", body = kwh(perDay))
        } else if (bars.isNotEmpty()) {
            Insight(icon = Icons.Outlined.Schedule, title = "Average hour", body = kwh(bars.sumOf { it.kwh } / bars.size))
        }
    }
}

@Composable
private fun Insight(icon: ImageVector, title: String, body: String) {
    Surface(
        shape = RoundedCornerShape(18.dp),
        color = MaterialTheme.colorScheme.secondaryContainer,
        modifier = Modifier.semantics(mergeDescendants = true) {}
    ) {
        Row(Modifier.padding(horizontal = 14.dp, vertical = 10.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(icon, contentDescription = null, modifier = Modifier.size(20.dp))
            Column(Modifier.padding(start = 10.dp)) {
                Text(title, style = MaterialTheme.typography.labelMedium)
                Text(body, style = MaterialTheme.typography.titleSmall)
            }
        }
    }
}

/* ---------- Month-end outlook ---------- */

@Composable
private fun MonthOutlook(
    samples: List<EnergySample>,
    rate: Double,
    monthlyBudget: Int?,
    simulated: Boolean,
    zone: ZoneId
) {
    // Average of complete days only, so a half-finished day does not pull the estimate down.
    val days = samples.groupBy { it.at.atZone(zone).toLocalDate() }.filterValues { it.size >= 90 }
    if (days.isEmpty()) return
    val avgDailyKwh = days.values.map { day -> day.sumOf { it.kw * 0.25 } }.average()
    val month = YearMonth.now(zone)
    val monthKwh = avgDailyKwh * month.lengthOfMonth()
    val monthPhp = monthKwh * rate
    val over = monthlyBudget != null && monthPhp > monthlyBudget
    val accent = if (over) MaterialTheme.colorScheme.tertiary else MaterialTheme.colorScheme.primary

    Card(
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = CardDefaults.outlinedCardBorder(),
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(Modifier.padding(18.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(16.dp)) {
            ProgressRing(
                progress = if (monthlyBudget != null && monthlyBudget > 0) (monthPhp / monthlyBudget).toFloat() else 0f,
                size = 84.dp,
                strokeWidth = 9.dp,
                color = accent,
                contentDescription = "Month-end estimate ${formatPesos(monthPhp, 0)}" +
                    (monthlyBudget?.let { " against a ${formatPesos(it.toDouble(), 0)} budget" } ?: "")
            ) {
                Text(
                    if (monthlyBudget != null && monthlyBudget > 0) "${((monthPhp / monthlyBudget) * 100).roundToInt()}%" else "—",
                    style = MaterialTheme.typography.titleSmall
                )
            }
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text("${month.month.name.lowercase().replaceFirstChar { it.uppercase() }} bill outlook", style = MaterialTheme.typography.titleMedium)
                AnimatedPesos(
                    amount = monthPhp,
                    decimals = 0,
                    style = MaterialTheme.typography.headlineSmall.copy(fontFamily = FontFamily.Monospace)
                )
                Text(
                    buildString {
                        append("Estimate from your average day (${kwh(avgDailyKwh)}) × ${month.lengthOfMonth()} days. ")
                        when {
                            monthlyBudget == null -> append("Set a budget by telling Ali your last bill.")
                            over -> append("About ${formatPesos(monthPhp - monthlyBudget, 0)} over your ${formatPesos(monthlyBudget.toDouble(), 0)} budget.")
                            else -> append("About ${formatPesos(monthlyBudget - monthPhp, 0)} under your ${formatPesos(monthlyBudget.toDouble(), 0)} budget.")
                        }
                        append(" Your actual bill also has fixed charges and taxes.")
                        if (simulated) append(" Simulated.")
                    },
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

@Composable
private fun SensorLine(device: DeviceUsage) {
    val seen = device.lastSeenAt?.let { runCatching { Instant.parse(it) }.getOrNull() }
    val text = when {
        seen == null -> "Waiting for the sensor's first report."
        device.isSimulated -> "Simulated readings · last reading ${seen.atZone(ZoneId.systemDefault()).format(StampFormat)}"
        EnergyAnalysis.isFresh(seen, Instant.now()) -> "Clamp online · last reading ${seen.atZone(ZoneId.systemDefault()).format(StampFormat)}"
        else -> "Clamp out of date · last reading ${seen.atZone(ZoneId.systemDefault()).format(StampFormat)}. No reading is not the same as safe."
    }
    Text(text, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
}
