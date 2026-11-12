package com.alventur.silipapp.ui.home

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.alventur.silipapp.data.demo.DemoHousehold
import com.alventur.silipapp.data.local.Progress
import com.alventur.silipapp.data.local.ProgressStore
import com.alventur.silipapp.data.local.manilaToday
import com.alventur.silipapp.data.remote.HouseholdDashboardState
import com.alventur.silipapp.education.Lesson
import com.alventur.silipapp.ui.AdaptivePage
import com.alventur.silipapp.ui.AwayAlertsCard
import com.alventur.silipapp.ui.DemoEvent
import com.alventur.silipapp.ui.DemoEventBus
import com.alventur.silipapp.ui.HomeCompanionSummary
import com.alventur.silipapp.ui.NextLessonCard
import com.alventur.silipapp.ui.SectionHeading
import com.alventur.silipapp.ui.SolarEntryCard
import com.alventur.silipapp.ui.alerts.SafetyAlertSheet
import com.alventur.silipapp.ui.design.StreakFlame
import com.alventur.silipapp.ui.design.pressScale

// WAVE 2: Home owner expands this.
// Target (see silip-mobile-redesign-prompt.md, pillar 2): Ali greeting by time of day; live burn-rate
// hero (AnimatedPesos + ProgressRing pulse, burnRatePhpPerHour(kw, rate)); "What changed" delta chip;
// today's cost vs progress.profile.dailyBudgetPhp (ProgressRing); streak + quiz card; alert card for
// DemoHousehold.safetyAlert when progress.usingDemoHome; grid event banner. Keep the existing
// HomeCompanionSummary data paths (live PoC API, simulated label, sensor freshness).

/**
 * Home: "my money right now".
 *
 * Wave 1 placeholder: the previous Home content plus a streak/quiz row and the sample safety alert.
 * Opens [SafetyAlertSheet] when [demoEvents] has [DemoEvent.ShowSafetyAlert] pending.
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

    AdaptivePage(contentPadding) {
        item { HomeCompanionSummary(householdState, userName, onOpenUsage, onRefreshHousehold) }
        item {
            StreakQuizCard(
                days = progress.streak.displayCount(today),
                litToday = progress.streak.isLitToday(today),
                quizDone = progress.quizDoneToday(today),
                onOpenQuiz = onOpenQuiz
            )
        }
        item {
            OutlinedButton(
                onClick = onOpenGridEvent,
                modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)
            ) { Text("Grid Alert tonight (pilot preview)") }
        }
        item { SolarEntryCard(onOpenSolar) }
        item { AwayAlertsCard() }
        item { SectionHeading("A small lesson for today") }
        item { NextLessonCard(nextLesson, onOpenLesson) }
    }

    if (demoEvents.pending == DemoEvent.ShowSafetyAlert) {
        SafetyAlertSheet(
            alert = DemoHousehold.safetyAlert,
            onDismiss = { demoEvents.consume(DemoEvent.ShowSafetyAlert) },
            onResolved = { resolution -> store.resolveAlert(DemoHousehold.safetyAlert.id, resolution) },
            onSnooze = { store.snoozeAlert(DemoHousehold.safetyAlert.id) }
        )
    }
}

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
                StreakFlame(days = days, litToday = litToday, size = 36.dp)
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
