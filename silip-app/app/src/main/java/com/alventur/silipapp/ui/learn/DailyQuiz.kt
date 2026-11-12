package com.alventur.silipapp.ui.learn

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import com.alventur.silipapp.data.local.ProgressStore
import com.alventur.silipapp.data.local.manilaToday
import com.alventur.silipapp.education.ChallengeQuestion
import com.alventur.silipapp.education.LessonCatalog
import com.alventur.silipapp.education.LessonQuizCatalog
import com.alventur.silipapp.ui.AdaptivePage
import com.alventur.silipapp.ui.AliPose
import com.alventur.silipapp.ui.ChallengeAnswerCard
import com.alventur.silipapp.ui.ChallengeFeedbackCard
import com.alventur.silipapp.ui.design.AnimatedAli
import com.alventur.silipapp.ui.design.StreakFlame
import com.alventur.silipapp.ui.design.rememberHaptics
import java.time.LocalDate

// WAVE 2: Learn/engagement owner expands this.
// Target (pillar 5): 15-second timer ring (ProgressRing), one question, instant Ali feedback,
// XP burst (AnimatedNumber + ConfettiBurst), streak flame pop (StreakFlame celebrateKey),
// and a short "streak freeze" explainer (ProgressStore.addStreakFreeze / StreakChange.SavedByFreeze).

/** XP for today's quiz: a correct answer earns more, showing up still counts. */
internal const val QUIZ_XP_CORRECT = 10
internal const val QUIZ_XP_TRIED = 5

/** Today's question, the same for everyone on a given Manila date. */
internal fun dailyQuestion(today: LocalDate = manilaToday()): ChallengeQuestion {
    val all = LessonCatalog.starterLessons.flatMap { LessonQuizCatalog.questionsFor(it.id) }.distinct()
    return all[Math.floorMod(today.toEpochDay(), all.size.toLong()).toInt()]
}

/**
 * Daily 15-second quiz. One question per Manila day; answering counts today for the Eco-Streak
 * via [ProgressStore.completeDailyQuiz]. Wave 1: no timer yet.
 */
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
    var selectedId by rememberSaveable { mutableStateOf<String?>(null) }
    var submitted by rememberSaveable { mutableStateOf(false) }
    val answer = question.answers.firstOrNull { it.id == selectedId }
    val alreadyDone = progress.quizDoneToday(today) && !submitted

    AdaptivePage(contentPadding) {
        item {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                AnimatedAli(pose = AliPose.Practice, size = 88.dp)
                Column(Modifier.weight(1f)) {
                    Text("Today's quiz", style = MaterialTheme.typography.titleLarge,
                        modifier = Modifier.semantics { heading() })
                    Text("One question. About 15 seconds.", style = MaterialTheme.typography.bodyMedium)
                }
                StreakFlame(
                    days = progress.streak.displayCount(today),
                    litToday = progress.streak.isLitToday(today),
                    celebrateKey = if (submitted) progress.streak.count else null
                )
            }
        }
        if (alreadyDone) {
            item { Text("You've done today's quiz. Come back tomorrow.", style = MaterialTheme.typography.bodyLarge) }
        } else {
            item { Text(question.prompt, style = MaterialTheme.typography.titleLarge) }
            items(question.answers, key = { it.id }) { option ->
                ChallengeAnswerCard(
                    text = option.text,
                    selected = selectedId == option.id,
                    enabled = !submitted,
                    onClick = { selectedId = option.id; haptics.select() }
                )
            }
            if (!submitted) item {
                Button(
                    onClick = {
                        val correct = answer?.correct == true
                        if (correct) haptics.confirm() else haptics.reject()
                        submitted = true
                        store.completeDailyQuiz(if (correct) QUIZ_XP_CORRECT else QUIZ_XP_TRIED, today)
                    },
                    enabled = selectedId != null,
                    modifier = Modifier.fillMaxWidth().heightIn(min = 52.dp)
                ) { Text("Check answer") }
            }
            if (submitted && answer != null) item {
                ChallengeFeedbackCard(isCorrect = answer.correct, explanation = question.explanation)
            }
        }
        item {
            OutlinedButton(onClick = onBack, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) {
                Text("Back to Learn")
            }
        }
    }
}
