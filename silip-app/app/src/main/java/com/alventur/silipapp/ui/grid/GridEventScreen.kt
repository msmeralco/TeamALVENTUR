package com.alventur.silipapp.ui.grid

import android.os.SystemClock
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.AcUnit
import androidx.compose.material.icons.outlined.ElectricBolt
import androidx.compose.material.icons.outlined.LocalLaundryService
import androidx.compose.material.icons.outlined.PlayArrow
import androidx.compose.material.icons.outlined.Schedule
import androidx.compose.material.icons.rounded.CheckCircle
import androidx.compose.material.icons.rounded.Warning
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.alventur.silipapp.data.demo.DemoGridEvent
import com.alventur.silipapp.data.demo.DemoHousehold
import com.alventur.silipapp.data.demo.DemoLabels
import com.alventur.silipapp.data.demo.ManilaZone
import com.alventur.silipapp.data.local.GridEventRecord
import com.alventur.silipapp.data.local.ProgressStore
import com.alventur.silipapp.data.local.manilaToday
import com.alventur.silipapp.ui.AdaptivePage
import com.alventur.silipapp.ui.AliPose
import com.alventur.silipapp.ui.DemoEvent
import com.alventur.silipapp.ui.DemoEventBus
import com.alventur.silipapp.ui.GridEventVisual
import com.alventur.silipapp.ui.design.AnimatedAli
import com.alventur.silipapp.ui.design.AnimatedPesos
import com.alventur.silipapp.ui.design.ConfettiBurst
import com.alventur.silipapp.ui.design.SilipMotion
import com.alventur.silipapp.ui.design.formatNumber
import com.alventur.silipapp.ui.design.orSnap
import com.alventur.silipapp.ui.design.pressScale
import com.alventur.silipapp.ui.design.rememberHaptics
import com.alventur.silipapp.ui.design.rememberReduceMotion
import com.alventur.silipapp.ui.learn.PinnedDemoLabel
import java.time.Duration
import java.time.LocalTime
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter
import java.util.Locale
import kotlin.math.cos
import kotlin.math.roundToInt
import kotlin.math.sin
import kotlinx.coroutines.delay

/** Invite → Joined → Live (the demo event hour) → Done. */
private enum class EventPhase { Invite, Joined, Live, Done }

/** How long "Simulate the event hour" takes to play 8–9 PM. */
private const val SIMULATION_MILLIS = 20_000

/** Gauge words. Always shown beside the gauge color. */
private enum class GaugeStatus(val label: String, val icon: ImageVector) {
    NearLimit("Near limit", Icons.Rounded.Warning),
    CoolingDown("Cooling down", Icons.Outlined.Schedule),
    SafeRange("Safe range", Icons.Rounded.CheckCircle)
}

private fun gaugeStatus(percent: Double): GaugeStatus = when {
    percent >= 90.0 -> GaugeStatus.NearLimit
    percent >= 82.0 -> GaugeStatus.CoolingDown
    else -> GaugeStatus.SafeRange
}

/** One suggested action with its estimated reduction in kW. */
private data class SuggestedAction(val text: String, val kw: Double, val icon: ImageVector)

/** Snapshot of the event at simulation progress t (0 = 8:00 PM, 1 = 9:00 PM). Demo data. */
private data class EventFrame(val joined: Int, val joinedSmooth: Float, val yourKw: Double, val loadPercent: Double, val clock: LocalTime)

private fun frameAt(event: DemoGridEvent, t: Float, joinedYou: Boolean, targetKw: Double): EventFrame {
    val first = event.initialJoined + if (joinedYou) 1 else 0
    val span = (event.finalJoined - first).coerceAtLeast(0)
    val joinShare = easeOut((t / 0.7f).coerceIn(0f, 1f))
    val joinedSmooth = first + span * joinShare
    // Load follows participation with a short lag, from the start load down to the target load.
    val coolShare = easeOut((t / 0.85f).coerceIn(0f, 1f))
    val load = event.startLoadPercent - (event.startLoadPercent - event.targetLoadPercent) * coolShare
    val yourKw = if (joinedYou) targetKw * (t / 0.08f).coerceIn(0f, 1f) else 0.0
    val clock = event.start.plusSeconds((Duration.between(event.start, event.end).seconds * t).toLong())
    return EventFrame(joinedSmooth.roundToInt(), joinedSmooth, yourKw, load, clock)
}

private fun easeOut(x: Float): Float = 1f - (1f - x) * (1f - x)

/**
 * Grid events tab: the demo April-night Grid Alert (pilot preview).
 *
 * Everything here is demo data: no event, consent or payout service exists. "Pilot preview" stays
 * pinned on screen. The household's suggested reduction uses [DemoHousehold.AIRCON_STEP_KW], the same
 * aircon step Home shows. [DemoEvent.StartGridEvent] resets the event to a fresh invite; joining
 * always takes the user's tap.
 */
@Composable
internal fun GridEventScreen(
    contentPadding: PaddingValues,
    demoEvents: DemoEventBus
) {
    val context = LocalContext.current
    val store = remember(context) { ProgressStore.get(context) }
    val progress by store.progress.collectAsState()
    val haptics = rememberHaptics()
    val event = DemoHousehold.gridEvent
    val targetKw = DemoHousehold.AIRCON_STEP_KW
    val actions = remember(event) {
        listOf(SuggestedAction("Turn off one aircon", targetKw, Icons.Outlined.AcUnit)) +
            event.suggestedActions
                .filterNot { (text, _) -> text.contains("aircon", ignoreCase = true) }
                .map { (text, kw) -> SuggestedAction(text, kw, Icons.Outlined.LocalLaundryService) }
    }

    var phaseName by rememberSaveable { mutableStateOf(EventPhase.Invite.name) }
    val phase = EventPhase.valueOf(phaseName)
    var simT by rememberSaveable { mutableFloatStateOf(0f) }
    var confettiKey by rememberSaveable { mutableStateOf<Long?>(null) }

    // Settings or Home can send a fresh sample event.
    LaunchedEffect(demoEvents.pending) {
        if (demoEvents.pending == DemoEvent.StartGridEvent) {
            phaseName = EventPhase.Invite.name
            simT = 0f
            demoEvents.consume(DemoEvent.StartGridEvent)
        }
    }

    // The demo event hour plays in about 20 seconds. It is data, not decoration, so it runs
    // under reduce motion too.
    LaunchedEffect(phase) {
        if (phase != EventPhase.Live) return@LaunchedEffect
        val clock = Animatable(simT)
        var lastJoined = frameAt(event, simT, true, targetKw).joined
        clock.animateTo(1f, tween(((1f - simT) * SIMULATION_MILLIS).toInt().coerceAtLeast(1), easing = LinearEasing)) {
            simT = value
            val joinedNow = frameAt(event, value, true, targetKw).joined
            if (joinedNow > lastJoined) haptics.tick()
            lastJoined = joinedNow
        }
        store.recordGridEvent(event.id, targetKw, event.rewardPhp, manilaToday())
        store.earnBadge(ProgressStore.BADGE_GRID_HELPER)
        haptics.confirm()
        confettiKey = SystemClock.elapsedRealtime()
        phaseName = EventPhase.Done.name
    }

    val frame = when (phase) {
        EventPhase.Invite -> frameAt(event, 0f, false, targetKw)
        EventPhase.Joined -> frameAt(event, 0f, true, targetKw)
        EventPhase.Live -> frameAt(event, simT, true, targetKw)
        EventPhase.Done -> frameAt(event, 1f, true, targetKw)
    }

    Box(Modifier.fillMaxSize()) {
        AdaptivePage(contentPadding) {
            item {
                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(
                        "Grid events",
                        style = MaterialTheme.typography.headlineSmall,
                        modifier = Modifier.semantics { heading() }
                    )
                    Text(
                        "Help your street's transformer on its busiest nights.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
            item {
                EventCard(
                    event = event,
                    phase = phase,
                    frame = frame,
                    targetKw = targetKw,
                    onJoin = {
                        haptics.confirm()
                        phaseName = EventPhase.Joined.name
                    },
                    onLeave = {
                        haptics.select()
                        phaseName = EventPhase.Invite.name
                    },
                    onSimulate = {
                        haptics.select()
                        simT = 0f
                        phaseName = EventPhase.Live.name
                    },
                    onReplay = {
                        simT = 0f
                        phaseName = EventPhase.Invite.name
                    }
                )
            }
            if (phase == EventPhase.Invite || phase == EventPhase.Joined) {
                item {
                    Text(
                        "What you can do from 8 to 9 PM",
                        style = MaterialTheme.typography.titleLarge,
                        modifier = Modifier.semantics { heading() }
                    )
                }
                items(actions, key = { it.text }) { action -> ActionRow(action) }
                item {
                    Text(
                        "kW figures are estimates. Keep the fridge and anything medical or essential on.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
            item { EventHistory(progress.gridEvents) }
            item { GridEventVisual() }
            item { Spacer(Modifier.height(40.dp)) }
        }
        ConfettiBurst(trigger = confettiKey, modifier = Modifier.matchParentSize(), origin = Offset(0.5f, 0.25f))
        PinnedDemoLabel(
            label = DemoLabels.PILOT,
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .padding(bottom = contentPadding.calculateBottomPadding() + 12.dp)
        )
    }
}

@Composable
private fun EventCard(
    event: DemoGridEvent,
    phase: EventPhase,
    frame: EventFrame,
    targetKw: Double,
    onJoin: () -> Unit,
    onLeave: () -> Unit,
    onSimulate: () -> Unit,
    onReplay: () -> Unit
) {
    val scheme = MaterialTheme.colorScheme
    val reduceMotion = rememberReduceMotion()
    val container by animateColorAsState(
        targetValue = if (phase == EventPhase.Done) scheme.primaryContainer else scheme.tertiaryContainer,
        animationSpec = SilipMotion.standard<Color>().orSnap(reduceMotion),
        label = "event-card"
    )
    Card(
        shape = RoundedCornerShape(28.dp),
        colors = CardDefaults.cardColors(containerColor = container),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Icon(Icons.Outlined.ElectricBolt, contentDescription = null, tint = scheme.tertiary)
                Text(
                    event.headline,
                    style = MaterialTheme.typography.titleLarge,
                    modifier = Modifier.weight(1f).semantics { heading() }
                )
                Text("8–9 PM", style = MaterialTheme.typography.titleMedium.copy(fontFamily = FontFamily.Monospace))
            }
            Text(event.message, style = MaterialTheme.typography.bodyLarge)

            TransformerGauge(percent = frame.loadPercent, modifier = Modifier.align(Alignment.CenterHorizontally))

            AnimatedContent(
                targetState = phase,
                transitionSpec = {
                    if (reduceMotion) fadeIn(SilipMotion.short()) togetherWith fadeOut(SilipMotion.short())
                    else fadeIn(SilipMotion.enter()) togetherWith fadeOut(SilipMotion.short())
                },
                label = "event-phase"
            ) { shown ->
                Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
                    when (shown) {
                        EventPhase.Invite -> {
                            Countdown(event)
                            NeighborsJoined(frame, event)
                            Button(
                                onClick = onJoin,
                                modifier = Modifier.fillMaxWidth().heightIn(min = 52.dp).pressScale()
                            ) { Text("Join for 8–9 PM") }
                            Text(
                                "Joining is part of the pilot preview. Nothing is sent and no payout service exists yet.",
                                style = MaterialTheme.typography.bodySmall
                            )
                        }
                        EventPhase.Joined -> {
                            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                                AnimatedAli(pose = AliPose.HouseholdCheck, size = 72.dp)
                                Column(Modifier.weight(1f)) {
                                    Text("You're in.", style = MaterialTheme.typography.titleLarge)
                                    Text(
                                        "Your goal: about −${formatNumber(targetKw, 2)} kW for one hour. One aircon off does it.",
                                        style = MaterialTheme.typography.bodyMedium
                                    )
                                }
                            }
                            Countdown(event)
                            NeighborsJoined(frame, event)
                            SimulateControl(onSimulate)
                            TextButton(onClick = onLeave, modifier = Modifier.heightIn(min = 48.dp)) {
                                Text("Leave this event")
                            }
                        }
                        EventPhase.Live -> LiveView(frame, event, targetKw)
                        EventPhase.Done -> DoneView(event, targetKw, onReplay)
                    }
                }
            }
        }
    }
}

/** Countdown to tonight's 8 PM (Manila). Ticks every second. */
@Composable
private fun Countdown(event: DemoGridEvent) {
    var now by remember { mutableStateOf(ZonedDateTime.now(ManilaZone)) }
    LaunchedEffect(Unit) {
        while (true) {
            delay(1_000)
            now = ZonedDateTime.now(ManilaZone)
        }
    }
    val start = now.toLocalDate().atTime(event.start).atZone(ManilaZone)
    val end = now.toLocalDate().atTime(event.end).atZone(ManilaZone)
    val (label, value, spoken) = when {
        now.isBefore(start) -> {
            val d = Duration.between(now, start)
            val h = d.toHours()
            val m = d.toMinutes() % 60
            val s = d.seconds % 60
            Triple(
                "Starts in",
                String.format(Locale.US, "%d:%02d:%02d", h, m, s),
                "Starts in $h hours $m minutes"
            )
        }
        now.isBefore(end) -> Triple("Happening now", "until 9 PM", "Happening now, until 9 PM")
        else -> Triple("Tonight's window has passed", "replay it below", "Tonight's window has passed. Use the demo control to replay it.")
    }
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp),
        modifier = Modifier.clearAndSetSemantics { contentDescription = spoken }
    ) {
        Icon(Icons.Outlined.Schedule, contentDescription = null)
        Text(label, style = MaterialTheme.typography.titleMedium, modifier = Modifier.weight(1f))
        Text(
            value,
            style = MaterialTheme.typography.titleLarge.copy(fontFamily = FontFamily.Monospace, fontFeatureSettings = "tnum")
        )
    }
}

@Composable
private fun NeighborsJoined(frame: EventFrame, event: DemoGridEvent) {
    Column(
        verticalArrangement = Arrangement.spacedBy(8.dp),
        modifier = Modifier.clearAndSetSemantics {
            contentDescription = "${frame.joined} of ${event.targetHouseholds} households joined"
        }
    ) {
        Row(verticalAlignment = Alignment.Bottom) {
            Text("Households joined", style = MaterialTheme.typography.titleMedium, modifier = Modifier.weight(1f))
            Text(
                "${frame.joined} / ${event.targetHouseholds}",
                style = MaterialTheme.typography.titleLarge.copy(fontFamily = FontFamily.Monospace, fontFeatureSettings = "tnum")
            )
        }
        HouseholdDots(joined = frame.joinedSmooth, total = event.targetHouseholds)
    }
}

/** One dot per household on the street. Filled = joined. */
@Composable
private fun HouseholdDots(joined: Float, total: Int) {
    val filled = MaterialTheme.colorScheme.primary
    val empty = MaterialTheme.colorScheme.outline.copy(alpha = 0.45f)
    val perRow = 15
    val rows = (total + perRow - 1) / perRow
    Canvas(
        Modifier
            .fillMaxWidth()
            .height((rows * 16).dp)
    ) {
        val cell = size.width / perRow
        val radius = minOf(cell, 16.dp.toPx()) * 0.32f
        for (i in 0 until total) {
            val cx = cell * (i % perRow) + cell / 2f
            val cy = 16.dp.toPx() * (i / perRow) + 8.dp.toPx()
            val fill = (joined - i).coerceIn(0f, 1f)
            drawCircle(color = empty, radius = radius, center = Offset(cx, cy), style = Stroke(1.5.dp.toPx()))
            if (fill > 0f) drawCircle(color = filled.copy(alpha = fill), radius = radius, center = Offset(cx, cy))
        }
    }
}

@Composable
private fun SimulateControl(onSimulate: () -> Unit) {
    Surface(
        shape = RoundedCornerShape(20.dp),
        color = MaterialTheme.colorScheme.surface,
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Demo control", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold)
            Text(
                "Plays the 8–9 PM hour in about 20 seconds with demo data.",
                style = MaterialTheme.typography.bodySmall
            )
            OutlinedButton(
                onClick = onSimulate,
                modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp).pressScale()
            ) {
                Icon(Icons.Outlined.PlayArrow, contentDescription = null)
                Text("Simulate the event hour", Modifier.padding(start = 8.dp))
            }
        }
    }
}

@Composable
private fun LiveView(frame: EventFrame, event: DemoGridEvent, targetKw: Double) {
    val clockText = frame.clock.format(DateTimeFormatter.ofPattern("h:mm a", Locale.US))
    val hourDone = (Duration.between(event.start, frame.clock).seconds.toFloat() /
        Duration.between(event.start, event.end).seconds.toFloat()).coerceIn(0f, 1f)
    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.clearAndSetSemantics { contentDescription = "Event hour, $clockText, demo playback" }
        ) {
            Text("Event hour", style = MaterialTheme.typography.titleMedium, modifier = Modifier.weight(1f))
            Text(
                clockText,
                style = MaterialTheme.typography.titleLarge.copy(fontFamily = FontFamily.Monospace, fontFeatureSettings = "tnum")
            )
        }
        LinearProgressIndicator(progress = { hourDone }, modifier = Modifier.fillMaxWidth())

        Column(
            verticalArrangement = Arrangement.spacedBy(8.dp),
            modifier = Modifier.clearAndSetSemantics {
                contentDescription = "Your reduction ${formatNumber(frame.yourKw, 2)} of ${formatNumber(targetKw, 2)} kilowatts, estimate"
            }
        ) {
            Row(verticalAlignment = Alignment.Bottom) {
                Text("Your reduction (estimate)", style = MaterialTheme.typography.titleMedium, modifier = Modifier.weight(1f))
                Text(
                    "−${formatNumber(frame.yourKw, 2)} / ${formatNumber(targetKw, 2)} kW",
                    style = MaterialTheme.typography.titleMedium.copy(fontFamily = FontFamily.Monospace, fontFeatureSettings = "tnum")
                )
            }
            LinearProgressIndicator(
                progress = { if (targetKw > 0) (frame.yourKw / targetKw).toFloat().coerceIn(0f, 1f) else 0f },
                modifier = Modifier.fillMaxWidth()
            )
        }
        NeighborsJoined(frame, event)
    }
}

@Composable
private fun DoneView(event: DemoGridEvent, targetKw: Double, onReplay: () -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            modifier = Modifier.semantics(mergeDescendants = true) { liveRegion = LiveRegionMode.Polite }
        ) {
            AnimatedAli(pose = AliPose.Success, size = 96.dp)
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text("Salamat! The transformer is in a safe range.", style = MaterialTheme.typography.titleLarge)
                Text(
                    "${event.finalJoined} households cut load together. Yours: about ${formatNumber(targetKw, 2)} kWh (estimate).",
                    style = MaterialTheme.typography.bodyMedium
                )
            }
        }
        Surface(shape = RoundedCornerShape(20.dp), color = MaterialTheme.colorScheme.surface, modifier = Modifier.fillMaxWidth()) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Row(verticalAlignment = Alignment.Bottom, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text("+", style = MaterialTheme.typography.headlineMedium, modifier = Modifier.clearAndSetSemantics { })
                    AnimatedPesos(
                        amount = event.rewardPhp.toDouble(),
                        countFrom = 0.0,
                        decimals = 0,
                        style = MaterialTheme.typography.headlineMedium,
                        accessibilityText = "Plus ${event.rewardPhp} pesos pending"
                    )
                    Text("pending", style = MaterialTheme.typography.titleMedium, modifier = Modifier.padding(bottom = 4.dp))
                }
                Text(
                    "Pilot preview, no payout service yet.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
        OutlinedButton(onClick = onReplay, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp).pressScale()) {
            Text("Replay the demo event")
        }
    }
}

@Composable
private fun ActionRow(action: SuggestedAction) {
    Surface(
        shape = RoundedCornerShape(20.dp),
        color = MaterialTheme.colorScheme.surface,
        modifier = Modifier
            .fillMaxWidth()
            .clearAndSetSemantics {
                contentDescription = "${action.text}, about minus ${formatNumber(action.kw, 2)} kilowatts, estimate"
            }
    ) {
        Row(
            Modifier.padding(horizontal = 16.dp, vertical = 14.dp).heightIn(min = 24.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Icon(action.icon, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
            Text(action.text, style = MaterialTheme.typography.bodyLarge, modifier = Modifier.weight(1f))
            Text(
                "≈ −${formatNumber(action.kw, 2)} kW",
                style = MaterialTheme.typography.titleMedium.copy(fontFamily = FontFamily.Monospace)
            )
        }
    }
}

@Composable
private fun EventHistory(records: List<GridEventRecord>) {
    val dateFormat = remember { DateTimeFormatter.ofPattern("EEE, MMM d", Locale.getDefault()) }
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text("Your event history", style = MaterialTheme.typography.titleLarge, modifier = Modifier.semantics { heading() })
        if (records.isEmpty()) {
            Text(
                "No events yet. Events you finish show up here.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        records.take(10).forEach { record ->
            Surface(
                shape = RoundedCornerShape(20.dp),
                color = MaterialTheme.colorScheme.surface,
                modifier = Modifier.fillMaxWidth().semantics(mergeDescendants = true) { }
            ) {
                Row(
                    Modifier.padding(horizontal = 16.dp, vertical = 12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Icon(Icons.Rounded.CheckCircle, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                    Column(Modifier.weight(1f)) {
                        Text("${record.date.format(dateFormat)}, 8–9 PM", style = MaterialTheme.typography.titleMedium)
                        Text(
                            "About ${formatNumber(record.kwhSaved, 2)} kWh saved (estimate)",
                            style = MaterialTheme.typography.bodySmall
                        )
                    }
                    Column(horizontalAlignment = Alignment.End) {
                        Text(
                            "₱${record.rewardPhp}",
                            style = MaterialTheme.typography.titleMedium.copy(fontFamily = FontFamily.Monospace)
                        )
                        Text("Pending", style = MaterialTheme.typography.labelMedium)
                    }
                }
            }
        }
    }
}

/**
 * Transformer load gauge: a 240° arc from 0 to 100% of the rating. Orange with "Near limit" at the
 * top, green with "Safe range" once enough homes cut load. Color always comes with the word and
 * the percentage. The 90% tick marks where "Near limit" begins.
 */
@Composable
private fun TransformerGauge(percent: Double, modifier: Modifier = Modifier) {
    val scheme = MaterialTheme.colorScheme
    val reduceMotion = rememberReduceMotion()
    val status = gaugeStatus(percent)
    val statusColor by animateColorAsState(
        targetValue = when (status) {
            GaugeStatus.NearLimit -> scheme.tertiary
            GaugeStatus.CoolingDown -> scheme.outline
            GaugeStatus.SafeRange -> scheme.primary
        },
        animationSpec = tween<Color>(600).orSnap(reduceMotion),
        label = "gauge-color"
    )
    val track = scheme.surface
    val tickColor = scheme.onSurfaceVariant
    val fraction = (percent / 100.0).toFloat().coerceIn(0f, 1f)

    Box(
        modifier = modifier.size(width = 232.dp, height = 200.dp),
        contentAlignment = Alignment.Center
    ) {
        Canvas(Modifier.size(232.dp).align(Alignment.TopCenter)) {
            val stroke = 18.dp.toPx()
            val inset = stroke * 1.4f
            val arcSize = Size(size.width - inset * 2, size.height - inset * 2)
            val topLeft = Offset(inset, inset)
            val startAngle = 150f
            val sweep = 240f
            drawArc(track, startAngle, sweep, false, topLeft, arcSize, style = Stroke(stroke, cap = StrokeCap.Round))
            drawArc(statusColor, startAngle, sweep * fraction, false, topLeft, arcSize, style = Stroke(stroke, cap = StrokeCap.Round))
            // Tick where "Near limit" starts (90%).
            val radius = arcSize.width / 2f
            val center = Offset(size.width / 2f, size.height / 2f)
            val angle = Math.toRadians((startAngle + sweep * 0.9f).toDouble())
            val inner = radius + stroke * 0.65f
            val outer = radius + stroke * 1.25f
            drawLine(
                color = tickColor,
                start = Offset(center.x + (inner * cos(angle)).toFloat(), center.y + (inner * sin(angle)).toFloat()),
                end = Offset(center.x + (outer * cos(angle)).toFloat(), center.y + (outer * sin(angle)).toFloat()),
                strokeWidth = 2.dp.toPx(),
                cap = StrokeCap.Round
            )
        }
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(2.dp),
            modifier = Modifier
                .padding(top = 8.dp)
                .semantics(mergeDescendants = true) {
                    contentDescription = "Transformer load ${percent.roundToInt()} percent, ${status.label}"
                }
        ) {
            Text("Transformer load", style = MaterialTheme.typography.labelLarge, color = scheme.onSurfaceVariant)
            Text(
                "${percent.roundToInt()}%",
                style = MaterialTheme.typography.displaySmall.copy(fontFeatureSettings = "tnum")
            )
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite }
            ) {
                Icon(status.icon, contentDescription = null, tint = statusColor, modifier = Modifier.size(20.dp))
                Text(status.label, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            }
        }
    }
}
