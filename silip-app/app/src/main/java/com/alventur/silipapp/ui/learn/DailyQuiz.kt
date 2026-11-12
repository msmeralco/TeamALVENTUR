package com.alventur.silipapp.ui.learn

import android.os.SystemClock
import android.view.accessibility.AccessibilityManager
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.fadeIn
import androidx.compose.animation.scaleIn
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.AcUnit
import androidx.compose.material.icons.rounded.Check
import androidx.compose.material.icons.rounded.Close
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.alventur.silipapp.R
import com.alventur.silipapp.data.demo.ManilaZone
import com.alventur.silipapp.data.local.ProgressStore
import com.alventur.silipapp.data.local.StreakChange
import com.alventur.silipapp.data.local.manilaToday
import com.alventur.silipapp.education.ChallengeAnswer
import com.alventur.silipapp.education.ChallengeQuestion
import com.alventur.silipapp.education.DailyQuizCatalog
import com.alventur.silipapp.ui.AdaptivePage
import com.alventur.silipapp.ui.AliPose
import com.alventur.silipapp.ui.design.AliGlow
import com.alventur.silipapp.ui.design.AnimatedAli
import com.alventur.silipapp.ui.design.AnimatedNumber
import com.alventur.silipapp.ui.design.ConfettiBurst
import com.alventur.silipapp.ui.design.ProgressRing
import com.alventur.silipapp.ui.design.SilipMotion
import com.alventur.silipapp.ui.design.StreakFlame
import com.alventur.silipapp.ui.design.pressScale
import com.alventur.silipapp.ui.design.rememberHaptics
import com.alventur.silipapp.ui.design.rememberReduceMotion
import java.time.Duration
import java.time.LocalDate
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter
import java.util.Locale
import kotlinx.coroutines.delay

/** XP for today's quiz: a correct answer earns more; showing up (even on time-out) still counts. */
internal const val QUIZ_XP_CORRECT = 10
internal const val QUIZ_XP_TRIED = 5

/** Seconds on the quiz timer. */
internal const val QUIZ_SECONDS = 15

/** Today's question, the same for everyone on a given Manila date. */
internal fun dailyQuestion(today: LocalDate = manilaToday()): ChallengeQuestion = DailyQuizCatalog.forDate(today)

private enum class QuizPhase { Ready, Asking, Correct, Wrong, TimeUp }

/**
 * Daily 15-second quiz. One question per Manila day.
 *
 * Habit over pressure: a wrong answer or a time-out still counts today for the Eco-Streak
 * ([ProgressStore.completeDailyQuiz]) and earns [QUIZ_XP_TRIED]. With TalkBack on there is no time limit.
 * Every 7th streak day earns one streak freeze (up to [ProgressStore.MAX_FREEZES]).
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun DailyQuizScreen(
    contentPadding: PaddingValues,
    onBack: () -> Unit
) {
    val context = LocalContext.current
    val store = remember(context) { ProgressStore.get(context) }
    val progress by store.progress.collectAsState()
    val haptics = rememberHaptics()
    val today = manilaToday()
    val question = remember(today) { dailyQuestion(today) }
    val untimed = remember(context) {
        context.getSystemService(AccessibilityManager::class.java)?.isTouchExplorationEnabled == true
    }

    var phaseName by rememberSaveable { mutableStateOf(QuizPhase.Ready.name) }
    val phase = QuizPhase.valueOf(phaseName)
    var pickedId by rememberSaveable { mutableStateOf<String?>(null) }
    var remainingMs by rememberSaveable { mutableLongStateOf(QUIZ_SECONDS * 1000L) }
    var awardedXp by rememberSaveable { mutableIntStateOf(0) }
    var streakChangeName by rememberSaveable { mutableStateOf<String?>(null) }
    var freezeEarned by rememberSaveable { mutableStateOf(false) }
    var celebrateKey by rememberSaveable { mutableStateOf<Int?>(null) }
    var confettiKey by rememberSaveable { mutableStateOf<Long?>(null) }
    var showFreezeSheet by rememberSaveable { mutableStateOf(false) }

    // Opened after finishing today's quiz in an earlier visit: show "come back tomorrow".
    val alreadyDone = progress.quizDoneToday(today) && phase == QuizPhase.Ready

    fun finish(picked: ChallengeAnswer?) {
        if (phaseName != QuizPhase.Asking.name) return
        val correct = picked?.correct == true
        val firstToday = !store.progress.value.quizDoneToday(today)
        val update = store.completeDailyQuiz(if (correct) QUIZ_XP_CORRECT else QUIZ_XP_TRIED, today)
        store.earnBadge(ProgressStore.BADGE_FIRST_QUIZ)
        val grew = update.change == StreakChange.Started || update.change == StreakChange.Continued ||
            update.change == StreakChange.SavedByFreeze
        if (grew && update.streak.count > 0 && update.streak.count % 7 == 0) {
            freezeEarned = store.addStreakFreeze() > update.streak.freezes
            store.earnBadge(ProgressStore.BADGE_WEEK_STREAK)
        }
        awardedXp = if (firstToday) (if (correct) QUIZ_XP_CORRECT else QUIZ_XP_TRIED) else 0
        streakChangeName = update.change.name
        if (update.change != StreakChange.AlreadyCountedToday) celebrateKey = update.streak.count
        pickedId = picked?.id
        phaseName = when {
            picked == null -> QuizPhase.TimeUp.name
            correct -> QuizPhase.Correct.name
            else -> QuizPhase.Wrong.name
        }
        when {
            correct -> {
                haptics.confirm()
                confettiKey = SystemClock.elapsedRealtime()
            }
            picked != null -> haptics.reject()
        }
    }

    // The timer drains in real time and survives rotation via remainingMs.
    LaunchedEffect(phase, untimed) {
        if (phase != QuizPhase.Asking || untimed) return@LaunchedEffect
        val endAt = SystemClock.elapsedRealtime() + remainingMs
        while (remainingMs > 0) {
            delay(100)
            remainingMs = (endAt - SystemClock.elapsedRealtime()).coerceAtLeast(0)
        }
        finish(null)
    }

    Box(Modifier.fillMaxSize()) {
        AdaptivePage(contentPadding) {
            item {
                QuizHeader(
                    streakDays = progress.streak.displayCount(today),
                    litToday = progress.streak.isLitToday(today),
                    celebrateKey = celebrateKey
                )
            }
            when {
                alreadyDone -> item {
                    ComeBackTomorrow(
                        freezes = progress.streak.freezes,
                        onExplainFreezes = { showFreezeSheet = true }
                    )
                }
                phase == QuizPhase.Ready -> item {
                    ReadyCard(
                        untimed = untimed,
                        onStart = {
                            haptics.select()
                            remainingMs = QUIZ_SECONDS * 1000L
                            phaseName = QuizPhase.Asking.name
                        }
                    )
                }
                else -> {
                    item {
                        QuestionBlock(
                            prompt = question.prompt,
                            remainingMs = remainingMs,
                            untimed = untimed,
                            answered = phase != QuizPhase.Asking
                        )
                    }
                    itemsIndexed(question.answers, key = { _, answer -> answer.id }) { index, answer ->
                        AnswerChip(
                            letter = ('A' + index).toString(),
                            answer = answer,
                            phase = phase,
                            picked = pickedId == answer.id,
                            onPick = { finish(answer) }
                        )
                    }
                    if (phase != QuizPhase.Asking) {
                        item {
                            ResultCard(
                                phase = phase,
                                question = question,
                                awardedXp = awardedXp,
                                streakChange = streakChangeName?.let { runCatching { StreakChange.valueOf(it) }.getOrNull() },
                                streakDays = progress.streak.displayCount(today),
                                freezeEarned = freezeEarned,
                                onExplainFreezes = { showFreezeSheet = true }
                            )
                        }
                    }
                }
            }
            item {
                OutlinedButton(
                    onClick = onBack,
                    modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp).pressScale()
                ) { Text("Back to Learn") }
            }
        }
        ConfettiBurst(trigger = confettiKey, modifier = Modifier.matchParentSize(), origin = Offset(0.5f, 0.3f))
    }

    if (showFreezeSheet) {
        val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
        ModalBottomSheet(onDismissRequest = { showFreezeSheet = false }, sheetState = sheetState) {
            StreakFreezeExplainer(
                freezes = progress.streak.freezes,
                onClose = { showFreezeSheet = false }
            )
        }
    }
}

@Composable
private fun QuizHeader(streakDays: Int, litToday: Boolean, celebrateKey: Any?) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Text(
                "Today's quiz",
                style = MaterialTheme.typography.headlineSmall,
                modifier = Modifier.semantics { heading() }
            )
            Text(
                "One question. A new one every day.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        Surface(shape = RoundedCornerShape(18.dp), color = MaterialTheme.colorScheme.surfaceVariant) {
            StreakFlame(
                days = streakDays,
                litToday = litToday,
                celebrateKey = celebrateKey,
                modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp)
            )
        }
    }
}

@Composable
private fun ReadyCard(untimed: Boolean, onStart: () -> Unit) {
    Card(
        shape = RoundedCornerShape(28.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            Modifier.padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            Box(contentAlignment = Alignment.Center) {
                ProgressRing(
                    progress = 1f,
                    size = 140.dp,
                    strokeWidth = 10.dp,
                    trackColor = MaterialTheme.colorScheme.surface,
                    contentDescription = if (untimed) "No time limit" else "$QUIZ_SECONDS seconds"
                ) {
                    AnimatedAli(pose = AliPose.Practice, size = 88.dp)
                }
            }
            Text(
                if (untimed) "Ready when you are." else "Ready? You'll have $QUIZ_SECONDS seconds.",
                style = MaterialTheme.typography.titleLarge
            )
            Text(
                "Showing up is what counts. Right, wrong or out of time, today still counts for your streak.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onPrimaryContainer
            )
            Button(
                onClick = onStart,
                modifier = Modifier.fillMaxWidth().heightIn(min = 52.dp).pressScale()
            ) { Text("Start the quiz") }
        }
    }
}

@Composable
private fun QuestionBlock(prompt: String, remainingMs: Long, untimed: Boolean, answered: Boolean) {
    val seconds = ((remainingMs + 999) / 1000).toInt()
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        if (!untimed) {
            ProgressRing(
                progress = remainingMs / (QUIZ_SECONDS * 1000f),
                size = 76.dp,
                strokeWidth = 7.dp,
                trackColor = MaterialTheme.colorScheme.surfaceVariant,
                contentDescription = if (answered) "Timer stopped" else "$seconds seconds left"
            ) {
                Text(
                    seconds.toString(),
                    style = MaterialTheme.typography.titleLarge.copy(fontFamily = FontFamily.Monospace),
                    fontWeight = FontWeight.Bold
                )
            }
        }
        Text(
            prompt,
            style = MaterialTheme.typography.titleLarge,
            modifier = Modifier.weight(1f).semantics { heading() }
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun AnswerChip(
    letter: String,
    answer: ChallengeAnswer,
    phase: QuizPhase,
    picked: Boolean,
    onPick: () -> Unit
) {
    val scheme = MaterialTheme.colorScheme
    val asking = phase == QuizPhase.Asking
    // After answering: the right answer is green with a check and the word "Answer";
    // a wrong pick is orange with a cross and "Your pick". Never color alone.
    val showRight = !asking && answer.correct
    val showWrongPick = !asking && picked && !answer.correct
    val container = when {
        showRight -> scheme.primaryContainer
        showWrongPick -> scheme.tertiaryContainer
        else -> scheme.surface
    }
    val border = when {
        showRight -> BorderStroke(2.dp, scheme.primary)
        showWrongPick -> BorderStroke(2.dp, scheme.tertiary)
        else -> BorderStroke(1.dp, scheme.outlineVariant)
    }
    val status = when {
        showRight && picked -> "Your pick, correct"
        showRight -> "Answer"
        showWrongPick -> "Your pick"
        else -> null
    }
    Surface(
        onClick = onPick,
        enabled = asking,
        shape = RoundedCornerShape(20.dp),
        color = container,
        border = border,
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 56.dp)
            .pressScale()
            .graphicsLayer { alpha = if (!asking && status == null) 0.6f else 1f }
            .semantics {
                role = Role.Button
                if (status != null) stateDescription = status
            }
    ) {
        Row(
            Modifier.padding(horizontal = 16.dp, vertical = 14.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Surface(shape = RoundedCornerShape(10.dp), color = scheme.surfaceVariant, modifier = Modifier.size(32.dp)) {
                Box(contentAlignment = Alignment.Center) {
                    when {
                        showRight -> Icon(Icons.Rounded.Check, contentDescription = null, tint = scheme.primary)
                        showWrongPick -> Icon(Icons.Rounded.Close, contentDescription = null, tint = scheme.tertiary)
                        else -> Text(letter, fontWeight = FontWeight.Bold, modifier = Modifier.clearAndSetSemantics { })
                    }
                }
            }
            Text(answer.text, style = MaterialTheme.typography.bodyLarge, modifier = Modifier.weight(1f))
            if (status != null) {
                Text(
                    if (showRight) "Answer" else "Your pick",
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.Bold,
                    color = if (showRight) scheme.primary else scheme.tertiary,
                    modifier = Modifier.clearAndSetSemantics { }
                )
            }
        }
    }
}

@Composable
private fun ResultCard(
    phase: QuizPhase,
    question: ChallengeQuestion,
    awardedXp: Int,
    streakChange: StreakChange?,
    streakDays: Int,
    freezeEarned: Boolean,
    onExplainFreezes: () -> Unit
) {
    val scheme = MaterialTheme.colorScheme
    val reduceMotion = rememberReduceMotion()
    val rightAnswer = question.answers.firstOrNull { it.correct }?.text.orEmpty()
    val (pose, glow, title) = when (phase) {
        QuizPhase.Correct -> Triple(AliPose.Success, AliGlow.Green, "Tama! That's right.")
        QuizPhase.Wrong -> Triple(AliPose.Caution, AliGlow.Orange, "Not quite.")
        else -> Triple(AliPose.Learning, AliGlow.Green, "Time's up. No worries.")
    }
    val body = when (phase) {
        QuizPhase.Correct -> question.explanation
        else -> "The answer: $rightAnswer. ${question.explanation}"
    }
    Card(
        shape = RoundedCornerShape(26.dp),
        colors = CardDefaults.cardColors(
            containerColor = if (phase == QuizPhase.Wrong) scheme.tertiaryContainer else scheme.primaryContainer
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                modifier = Modifier.semantics(mergeDescendants = true) { liveRegion = LiveRegionMode.Polite }
            ) {
                AnimatedAli(pose = pose, glow = glow, size = 84.dp)
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(title, style = MaterialTheme.typography.titleLarge)
                    Text(body, style = MaterialTheme.typography.bodyMedium)
                }
            }
            if (awardedXp > 0) {
                val pop = remember { Animatable(if (reduceMotion) 1f else 0.4f) }
                LaunchedEffect(Unit) { if (!reduceMotion) pop.animateTo(1f, SilipMotion.playful()) }
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    modifier = Modifier.graphicsLayer {
                        scaleX = pop.value
                        scaleY = pop.value
                    }
                ) {
                    Image(
                        painter = painterResource(R.drawable.silip_energy_token),
                        contentDescription = null,
                        contentScale = ContentScale.Fit,
                        modifier = Modifier.size(32.dp)
                    )
                    AnimatedNumber(
                        value = awardedXp.toDouble(),
                        countFrom = 0.0,
                        format = { "+${it.toInt()} XP" },
                        style = MaterialTheme.typography.headlineSmall,
                        accessibilityText = "Plus $awardedXp XP"
                    )
                }
            }
            streakLine(streakChange, streakDays)?.let { line ->
                Text(line, style = MaterialTheme.typography.bodyLarge, fontWeight = FontWeight.SemiBold)
            }
            AnimatedVisibility(visible = freezeEarned, enter = fadeIn() + scaleIn(initialScale = 0.9f)) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Icon(Icons.Outlined.AcUnit, contentDescription = null, tint = scheme.primary)
                    Text(
                        "7 days in a row. You earned a streak freeze.",
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = FontWeight.SemiBold
                    )
                }
            }
            TextButton(onClick = onExplainFreezes, modifier = Modifier.heightIn(min = 48.dp)) {
                Text("How streak freezes work")
            }
        }
    }
}

/** Plain, no-guilt words for what happened to the streak. */
private fun streakLine(change: StreakChange?, days: Int): String? = when (change) {
    StreakChange.Started -> "Day 1 of your Eco-Streak."
    StreakChange.Continued -> "Day $days of your Eco-Streak."
    StreakChange.SavedByFreeze -> "A streak freeze covered the missed day. Day $days."
    StreakChange.Restarted -> "Welcome back. A fresh streak starts today."
    StreakChange.AlreadyCountedToday -> "Today already counts for your streak."
    null -> null
}

@Composable
private fun ComeBackTomorrow(freezes: Int, onExplainFreezes: () -> Unit) {
    var now by remember { mutableStateOf(ZonedDateTime.now(ManilaZone)) }
    LaunchedEffect(Unit) {
        while (true) {
            delay(30_000)
            now = ZonedDateTime.now(ManilaZone)
        }
    }
    val next = now.toLocalDate().plusDays(1).atStartOfDay(ManilaZone)
    val wait = Duration.between(now, next).coerceAtLeast(Duration.ZERO)
    val hours = wait.toHours()
    val minutes = wait.toMinutes() % 60
    val dayLabel = next.format(DateTimeFormatter.ofPattern("EEE, MMM d", Locale.getDefault()))

    Card(
        shape = RoundedCornerShape(28.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            Modifier.padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            AnimatedAli(pose = AliPose.Welcome, size = 120.dp)
            Text("Done for today. Nice one.", style = MaterialTheme.typography.titleLarge)
            Text(
                "Come back tomorrow for a new question.",
                style = MaterialTheme.typography.bodyLarge
            )
            Text(
                "Opens $dayLabel, 12:00 AM Manila time (in ${hours} h ${minutes} min).",
                style = MaterialTheme.typography.bodyMedium.copy(fontFeatureSettings = "tnum"),
                color = MaterialTheme.colorScheme.onPrimaryContainer
            )
            Text(
                if (freezes == 1) "You have 1 streak freeze." else "You have $freezes streak freezes.",
                style = MaterialTheme.typography.bodyMedium
            )
            TextButton(onClick = onExplainFreezes, modifier = Modifier.heightIn(min = 48.dp)) {
                Text("How streak freezes work")
            }
        }
    }
}

@Composable
private fun StreakFreezeExplainer(freezes: Int, onClose: () -> Unit) {
    Column(
        Modifier
            .fillMaxWidth()
            .padding(horizontal = 24.dp)
            .padding(bottom = 24.dp)
            .navigationBarsPadding(),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            AnimatedAli(pose = AliPose.Learning, size = 72.dp)
            Text(
                "Streak freezes",
                style = MaterialTheme.typography.headlineSmall,
                modifier = Modifier.semantics { heading() }
            )
        }
        FreezePoint("Miss a day and a freeze covers it. Your streak keeps going.")
        FreezePoint("You earn one every time your streak reaches 7, 14, 21 days and so on.")
        FreezePoint("You can hold up to ${ProgressStore.MAX_FREEZES} at a time.")
        FreezePoint("No freeze left? A new streak simply starts. Your XP and badges stay.")
        Surface(shape = RoundedCornerShape(16.dp), color = MaterialTheme.colorScheme.surfaceVariant) {
            Row(
                Modifier
                    .fillMaxWidth()
                    .padding(14.dp)
                    .semantics(mergeDescendants = true) { },
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Icon(Icons.Outlined.AcUnit, contentDescription = null)
                Text(
                    if (freezes == 1) "You have 1 freeze now." else "You have $freezes freezes now.",
                    style = MaterialTheme.typography.titleMedium
                )
            }
        }
        Button(onClick = onClose, modifier = Modifier.fillMaxWidth().heightIn(min = 52.dp).pressScale()) {
            Text("Got it")
        }
    }
}

@Composable
private fun FreezePoint(text: String) {
    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        Icon(
            Icons.Rounded.Check,
            contentDescription = null,
            tint = MaterialTheme.colorScheme.primary,
            modifier = Modifier.size(20.dp).padding(top = 2.dp)
        )
        Text(text, style = MaterialTheme.typography.bodyLarge, modifier = Modifier.weight(1f))
    }
}
