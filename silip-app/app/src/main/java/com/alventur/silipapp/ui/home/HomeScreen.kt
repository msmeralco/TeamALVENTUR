package com.alventur.silipapp.ui.home

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.TrendingUp
import androidx.compose.material.icons.rounded.Bolt
import androidx.compose.material.icons.rounded.ChevronRight
import androidx.compose.material.icons.rounded.Warning
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.alventur.silipapp.data.demo.DemoHousehold
import com.alventur.silipapp.data.demo.DemoLabels
import com.alventur.silipapp.data.demo.ManilaZone
import com.alventur.silipapp.data.demo.burnRatePhpPerHour
import com.alventur.silipapp.data.local.AlertResolution
import com.alventur.silipapp.data.local.Progress
import com.alventur.silipapp.data.local.ProgressStore
import com.alventur.silipapp.data.local.manilaToday
import com.alventur.silipapp.data.remote.DeviceUsage
import com.alventur.silipapp.data.remote.HouseholdDashboardState
import com.alventur.silipapp.education.Lesson
import com.alventur.silipapp.energy.EnergyAnalysis
import com.alventur.silipapp.ui.AdaptivePage
import com.alventur.silipapp.ui.AliPose
import com.alventur.silipapp.ui.AwayAlertsCard
import com.alventur.silipapp.ui.DemoEvent
import com.alventur.silipapp.ui.DemoEventBus
import com.alventur.silipapp.ui.HomeCompanionSummary
import com.alventur.silipapp.ui.NextLessonCard
import com.alventur.silipapp.ui.PreviewBadge
import com.alventur.silipapp.ui.SectionHeading
import com.alventur.silipapp.ui.SolarEntryCard
import com.alventur.silipapp.ui.alerts.SafetyAlertSheet
import com.alventur.silipapp.ui.design.AliGlow
import com.alventur.silipapp.ui.design.AnimatedAli
import com.alventur.silipapp.ui.design.AnimatedPesos
import com.alventur.silipapp.ui.design.ProgressRing
import com.alventur.silipapp.ui.design.StreakFlame
import com.alventur.silipapp.ui.design.formatPesos
import com.alventur.silipapp.ui.design.pressScale
import com.alventur.silipapp.ui.design.rememberHaptics
import java.time.Instant
import java.time.LocalTime
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter
import java.util.Locale
import kotlin.math.max

/**
 * Home: "my money right now".
 *
 * Order (most useful first): Ali's greeting, the live burn-rate hero with "what changed", today's cost
 * against the daily budget, any safety alert, tonight's grid event (pilot preview), the Eco-Streak and
 * today's quiz, then solar, away reminders and the next lesson.
 *
 * Data: in demo mode ("Explore the demo home") Home uses Rosa's story at [DemoHousehold.STORY_NOW] so the
 * demo never reads as a stale sensor. With a real device Home reads the PoC usage API; while it is loading,
 * missing or failing, Home shows Ale's original [HomeCompanionSummary] states. Peso figures are always
 * labeled "estimate". An offline clamp is never described as safe.
 */
@Composable
internal fun HomeScreen(
    contentPadding: PaddingValues,
    householdState: HouseholdDashboardState,
    progress: Progress,
    userName: String,
    nextLesson: Lesson,
    demoEvents: DemoEventBus,
    onOpenUsage: () -> Unit,
    onOpenSolar: () -> Unit,
    onOpenLesson: () -> Unit,
    onOpenQuiz: () -> Unit,
    onOpenGridEvent: () -> Unit,
    onRefreshHousehold: () -> Unit
) {
    val context = LocalContext.current
    val store = remember(context) { ProgressStore.get(context) }
    val today = manilaToday()
    val rate = remember(progress) { store.ratePhpPerKwh() }
    val ownRate = remember(progress) { store.hasOwnRate() }
    val reading = remember(householdState, progress.usingDemoHome, rate) {
        homeReading(householdState, progress.usingDemoHome, rate)
    }
    val alert = DemoHousehold.safetyAlert
    var showAlert by rememberSaveable { mutableStateOf(false) }
    // Show until acted on; a snoozed alert comes back when its snooze ends.
    val alertRecord = progress.alert(alert.id)
    val alertOpen = alertRecord == null ||
        (alertRecord.resolution == AlertResolution.Snoozed && !progress.isSnoozed(alert.id))
    val gridDoneToday = progress.gridEvents.any { it.date == today }
    val name = userName.ifBlank { if (progress.usingDemoHome) "Rosa" else "" }

    AdaptivePage(contentPadding) {
        item { Greeting(name = name, hot = reading?.isJump == true, now = reading?.clock) }

        if (reading != null) {
            item {
                BurnRateHero(
                    reading = reading,
                    ownRate = ownRate,
                    rate = rate,
                    onOpenUsage = onOpenUsage
                )
            }
            item {
                TodayBudgetCard(
                    costSoFar = reading.costTodayPhp,
                    dailyBudget = progress.profile.dailyBudgetPhp,
                    simulated = reading.simulated
                )
            }
        } else {
            item { HomeCompanionSummary(householdState, userName, onOpenUsage, onRefreshHousehold) }
        }

        if (progress.usingDemoHome && alertOpen) {
            item { SafetyAlertCard(onOpen = { showAlert = true }) }
        }
        if (!gridDoneToday) {
            item { GridEventBanner(onOpenGridEvent) }
        }
        item {
            StreakQuizCard(
                days = progress.streak.displayCount(today),
                litToday = progress.streak.isLitToday(today),
                quizDone = progress.quizDoneToday(today),
                onOpenQuiz = onOpenQuiz
            )
        }
        item { SolarEntryCard(onOpenSolar) }
        item { AwayAlertsCard() }
        item { SectionHeading("A small lesson for today") }
        item { NextLessonCard(nextLesson, onOpenLesson) }
    }

    val fromSettings = demoEvents.pending == DemoEvent.ShowSafetyAlert
    if (showAlert || fromSettings) {
        SafetyAlertSheet(
            alert = alert,
            onDismiss = {
                showAlert = false
                if (fromSettings) demoEvents.consume(DemoEvent.ShowSafetyAlert)
            },
            onResolved = { resolution -> store.resolveAlert(alert.id, resolution) },
            onSnooze = { store.snoozeAlert(alert.id) }
        )
    }
}

/* ---------- Reading: what Home shows, from the demo story or the live device ---------- */

/** Everything the hero and budget cards need, already in pesos. */
private data class HomeReading(
    val nowKw: Double,
    val beforeKw: Double,
    val nowPhpPerHour: Double,
    val beforePhpPerHour: Double,
    /** Local time the jump started, or null when there is no clear jump. */
    val changedAt: LocalTime?,
    val costTodayPhp: Double,
    val simulated: Boolean,
    val clock: LocalTime,
    val sensorFresh: Boolean
) {
    val deltaPhpPerHour: Double get() = nowPhpPerHour - beforePhpPerHour

    /** A sharp rise worth pointing out: at least ₱3/h more and at least 1.8× the earlier rate. */
    val isJump: Boolean get() = deltaPhpPerHour >= MIN_JUMP_PHP && nowPhpPerHour >= beforePhpPerHour * 1.8
}

private const val MIN_JUMP_PHP = 3.0

private fun homeReading(state: HouseholdDashboardState, demo: Boolean, rate: Double): HomeReading? {
    if (demo) {
        val before = DemoHousehold.storyKwBefore
        val now = DemoHousehold.storyKwNow
        return HomeReading(
            nowKw = now,
            beforeKw = before,
            nowPhpPerHour = burnRatePhpPerHour(now, rate),
            beforePhpPerHour = burnRatePhpPerHour(before, rate),
            changedAt = DemoHousehold.AIRCON_ON,
            costTodayPhp = DemoHousehold.kwhUntilStoryNow() * rate,
            simulated = true,
            clock = DemoHousehold.STORY_NOW,
            sensorFresh = true
        )
    }
    val device = (state as? HouseholdDashboardState.Loaded)?.device ?: return null
    return liveReading(device, rate)
}

/**
 * Live device: "now" is the latest quarter hour; "before" is the median of the hour that ended 30 min
 * earlier, so a single spike does not count as the baseline. The jump time is the first quarter hour
 * after that hour that rose well above the baseline.
 */
private fun liveReading(device: DeviceUsage, rate: Double): HomeReading? {
    val points = device.points.mapNotNull { p ->
        runCatching { Instant.parse(p.timestamp) to p.powerKw }.getOrNull()
    }.filter { it.second.isFinite() && it.second >= 0.0 }.sortedBy { it.first }
    val last = points.lastOrNull() ?: return null
    val lastAt = last.first.atZone(ManilaZone)

    val baselineWindow = points.filter {
        val z = it.first.atZone(ManilaZone)
        !z.isBefore(lastAt.minusMinutes(90)) && z.isBefore(lastAt.minusMinutes(30))
    }.map { it.second }.sorted()
    val beforeKw = baselineWindow.getOrNull(baselineWindow.size / 2) ?: last.second

    val jumpAt = points.firstOrNull {
        !it.first.atZone(ManilaZone).isBefore(lastAt.minusMinutes(30)) && it.second >= beforeKw + 0.3
    }?.first?.atZone(ManilaZone)?.toLocalTime()

    val todayKwh = points.filter { it.first.atZone(ManilaZone).toLocalDate() == lastAt.toLocalDate() }
        .sumOf { it.second * 0.25 }

    return HomeReading(
        nowKw = last.second,
        beforeKw = beforeKw,
        nowPhpPerHour = burnRatePhpPerHour(last.second, rate),
        beforePhpPerHour = burnRatePhpPerHour(beforeKw, rate),
        changedAt = jumpAt,
        costTodayPhp = todayKwh * rate,
        simulated = device.isSimulated,
        clock = ZonedDateTime.now(ManilaZone).toLocalTime(),
        sensorFresh = EnergyAnalysis.isFresh(last.first, Instant.now())
    )
}

private val TimeFormat: DateTimeFormatter = DateTimeFormatter.ofPattern("h:mm a", Locale.US)

/* ---------- Greeting ---------- */

@Composable
private fun Greeting(name: String, hot: Boolean, now: LocalTime?) {
    val hour = (now ?: LocalTime.now(ManilaZone)).hour
    val hello = when {
        hour < 12 -> "Good morning"
        hour < 18 -> "Good afternoon"
        else -> "Good evening"
    }
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        AnimatedAli(
            pose = if (hot) AliPose.HouseholdCheck else AliPose.Welcome,
            glow = AliGlow.Green,
            size = 72.dp
        )
        Column(Modifier.weight(1f)) {
            Text(
                if (name.isBlank()) "$hello!" else "$hello, $name!",
                style = MaterialTheme.typography.headlineSmall,
                modifier = Modifier.semantics { heading() }
            )
            Text(
                if (hot) "Your home is using more right now. Here's what it costs."
                else "Here's what your home costs right now.",
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

/* ---------- Burn-rate hero ---------- */

@Composable
private fun BurnRateHero(reading: HomeReading, ownRate: Boolean, rate: Double, onOpenUsage: () -> Unit) {
    val jump = reading.isJump
    val accent = if (jump) MaterialTheme.colorScheme.tertiary else MaterialTheme.colorScheme.primary
    // Ring fills against a "busy hour" scale: three times the earlier rate, or the current rate if higher.
    val scale = max(reading.beforePhpPerHour * 3, reading.nowPhpPerHour).coerceAtLeast(1.0)
    val status = when {
        !reading.sensorFresh -> "Sensor out of date"
        jump -> "Higher than usual"
        else -> "Steady"
    }

    Card(
        shape = RoundedCornerShape(28.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = CardDefaults.outlinedCardBorder(),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    "Right now",
                    style = MaterialTheme.typography.titleMedium,
                    modifier = Modifier.weight(1f).semantics { heading() }
                )
                if (reading.simulated) PreviewBadge(label = DemoLabels.SIMULATED)
            }
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(18.dp)) {
                ProgressRing(
                    progress = (reading.nowPhpPerHour / scale).toFloat(),
                    size = 132.dp,
                    strokeWidth = 12.dp,
                    color = accent,
                    trackColor = if (jump) MaterialTheme.colorScheme.tertiaryContainer
                    else MaterialTheme.colorScheme.primaryContainer,
                    pulse = jump && reading.sensorFresh,
                    contentDescription = "Estimated ${formatPesos(reading.nowPhpPerHour)} per hour. $status."
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Icon(Icons.Rounded.Bolt, contentDescription = null, tint = accent, modifier = Modifier.size(22.dp))
                        Text("per hour", style = MaterialTheme.typography.labelMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    AnimatedPesos(
                        amount = reading.nowPhpPerHour,
                        decimals = 2,
                        suffix = "/h",
                        countFrom = reading.beforePhpPerHour,
                        style = MaterialTheme.typography.displaySmall.copy(
                            fontFamily = FontFamily.Monospace,
                            fontWeight = FontWeight.SemiBold
                        ),
                        accessibilityText = "Estimated ${formatPesos(reading.nowPhpPerHour)} per hour"
                    )
                    Text(
                        status,
                        style = MaterialTheme.typography.titleSmall,
                        color = accent
                    )
                    Text(
                        "${"%.2f".format(reading.nowKw)} kW · estimate",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
            if (jump && reading.changedAt != null) {
                WhatChangedChip(
                    deltaPhpPerHour = reading.deltaPhpPerHour,
                    since = reading.changedAt
                )
            }
            Text(
                if (ownRate) "Uses the rate from your bill (${formatPesos(rate)}/kWh)."
                else "Uses the dated Meralco residential benchmark (${formatPesos(rate)}/kWh). Add your bill rate in Settings for a closer estimate.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            OutlinedButton(
                onClick = onOpenUsage,
                modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp).pressScale()
            ) {
                Text("See today's usage")
                Spacer(Modifier.width(4.dp))
                Icon(Icons.Rounded.ChevronRight, contentDescription = null)
            }
        }
    }
}

/** "+₱7.50/h since 2:10 PM". Hedged: the clamp sees whole-home power, not appliances. */
@Composable
private fun WhatChangedChip(deltaPhpPerHour: Double, since: LocalTime) {
    val text = "+${formatPesos(deltaPhpPerHour)}/h since ${since.format(TimeFormat)}"
    Surface(
        shape = RoundedCornerShape(18.dp),
        color = MaterialTheme.colorScheme.tertiaryContainer,
        contentColor = MaterialTheme.colorScheme.onTertiaryContainer,
        modifier = Modifier.fillMaxWidth().semantics(mergeDescendants = true) {}
    ) {
        Row(
            Modifier.padding(horizontal = 14.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Icon(Icons.AutoMirrored.Rounded.TrendingUp, contentDescription = null)
            Column {
                Text(text, style = MaterialTheme.typography.titleSmall)
                Text(
                    "Likely a large appliance, such as an aircon. SILIP sees whole-home power, not which appliance.",
                    style = MaterialTheme.typography.bodySmall
                )
            }
        }
    }
}

/* ---------- Today vs budget ---------- */

@Composable
private fun TodayBudgetCard(costSoFar: Double, dailyBudget: Double?, simulated: Boolean) {
    val over = dailyBudget != null && costSoFar > dailyBudget
    val accent = if (over) MaterialTheme.colorScheme.tertiary else MaterialTheme.colorScheme.primary
    Card(
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = CardDefaults.outlinedCardBorder(),
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            Modifier.padding(18.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            ProgressRing(
                progress = if (dailyBudget != null && dailyBudget > 0) (costSoFar / dailyBudget).toFloat() else 0f,
                size = 72.dp,
                strokeWidth = 8.dp,
                color = accent,
                contentDescription = if (dailyBudget != null)
                    "${formatPesos(costSoFar)} of ${formatPesos(dailyBudget, 0)} daily budget"
                else "${formatPesos(costSoFar)} so far today"
            ) {
                Text(
                    if (dailyBudget != null && dailyBudget > 0) "${((costSoFar / dailyBudget) * 100).toInt()}%" else "—",
                    style = MaterialTheme.typography.labelLarge
                )
            }
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text("Today so far", style = MaterialTheme.typography.titleMedium)
                AnimatedPesos(
                    amount = costSoFar,
                    decimals = 2,
                    style = MaterialTheme.typography.headlineSmall.copy(fontFamily = FontFamily.Monospace)
                )
                Text(
                    when {
                        dailyBudget == null -> "Estimate. Tell Ali your last bill (Settings → Replay intro) to set a daily budget."
                        over -> "Estimate. Above your ${formatPesos(dailyBudget, 0)} daily budget."
                        else -> "Estimate. Within your ${formatPesos(dailyBudget, 0)} daily budget."
                    } + if (simulated) " Simulated." else "",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

/* ---------- Alert card ---------- */

@Composable
private fun SafetyAlertCard(onOpen: () -> Unit) {
    val haptics = rememberHaptics()
    Card(
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.tertiaryContainer,
            contentColor = MaterialTheme.colorScheme.onTertiaryContainer
        ),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                AnimatedAli(pose = AliPose.Caution, glow = AliGlow.Orange, size = 64.dp)
                Column(Modifier.weight(1f)) {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        Icon(Icons.Rounded.Warning, contentDescription = null, modifier = Modifier.size(18.dp))
                        Text("Check your home", style = MaterialTheme.typography.titleMedium)
                    }
                    Text(
                        "Something has been on for a while since you left.",
                        style = MaterialTheme.typography.bodyMedium
                    )
                    PreviewBadge(label = DemoLabels.SIMULATED)
                }
            }
            Button(
                onClick = {
                    haptics.select()
                    onOpen()
                },
                modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp).pressScale()
            ) { Text("See what Ali noticed") }
        }
    }
}

/* ---------- Grid event banner ---------- */

@Composable
private fun GridEventBanner(onOpen: () -> Unit) {
    val event = DemoHousehold.gridEvent
    Card(
        onClick = onOpen,
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer),
        modifier = Modifier.fillMaxWidth().pressScale().semantics {
            contentDescription = "Grid Alert tonight. Reduce load ${event.start.format(TimeFormat)} to " +
                "${event.end.format(TimeFormat)} to earn ${event.rewardPhp} pesos. ${DemoLabels.PILOT}."
        }
    ) {
        Row(
            Modifier.padding(18.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            AnimatedAli(pose = AliPose.Success, glow = AliGlow.Green, size = 56.dp)
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text("${event.headline} tonight", style = MaterialTheme.typography.titleMedium)
                Text(
                    "Help your street's transformer ${event.start.format(TimeFormat)}–${event.end.format(TimeFormat)} " +
                        "and earn ₱${event.rewardPhp}.",
                    style = MaterialTheme.typography.bodyMedium
                )
                PreviewBadge(label = DemoLabels.PILOT)
            }
            Icon(Icons.Rounded.ChevronRight, contentDescription = null)
        }
    }
}

/* ---------- Streak + quiz ---------- */

@Composable
private fun StreakQuizCard(days: Int, litToday: Boolean, quizDone: Boolean, onOpenQuiz: () -> Unit) {
    Card(
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = CardDefaults.outlinedCardBorder(),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                StreakFlame(days = days, litToday = litToday, size = 40.dp)
                Column(Modifier.weight(1f)) {
                    Text("Eco-Streak", style = MaterialTheme.typography.titleMedium)
                    Text(
                        if (quizDone) "Today's quiz is done. See you tomorrow." else "15 seconds keeps your streak going.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
            if (!quizDone) {
                Button(onClick = onOpenQuiz, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp).pressScale()) {
                    Text("Take today's quiz")
                }
            }
        }
    }
}
