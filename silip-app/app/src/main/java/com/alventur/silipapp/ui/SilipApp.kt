package com.alventur.silipapp.ui

import android.content.Context
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.Image
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.MenuBook
import androidx.compose.material.icons.outlined.Bolt
import androidx.compose.material.icons.outlined.CardGiftcard
import androidx.compose.material.icons.outlined.EmojiEvents
import androidx.compose.material.icons.outlined.Home
import androidx.compose.material.icons.outlined.Lightbulb
import androidx.compose.material.icons.outlined.TipsAndUpdates
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.alventur.silipapp.R
import com.alventur.silipapp.data.remote.HouseholdApi
import com.alventur.silipapp.data.remote.HouseholdApiException
import com.alventur.silipapp.data.remote.HouseholdDashboardState
import com.alventur.silipapp.education.ChallengeAnswer
import com.alventur.silipapp.education.Lesson
import com.alventur.silipapp.education.LessonCatalog
import com.alventur.silipapp.education.LessonQuizCatalog
import java.io.IOException
import kotlinx.coroutines.CancellationException

private enum class Destination(
    val label: String,
    val icon: ImageVector
) {
    Home("Home", Icons.Outlined.Home),
    Usage("Usage", Icons.Outlined.Bolt),
    Learn("Learn", Icons.AutoMirrored.Outlined.MenuBook),
    Rewards("Rewards", Icons.Outlined.CardGiftcard),
    DailyChallenge("Daily challenge", Icons.Outlined.Lightbulb)
}

@Composable
fun SilipApp(
    householdApi: HouseholdApi
) {
    val context = LocalContext.current
    val devicePreferences = remember(context) {
        context.getSharedPreferences("silip_demo_device", Context.MODE_PRIVATE)
    }
    var deviceId by rememberSaveable {
        mutableStateOf(devicePreferences.getString("clamp_id", "silip-esp32-test") ?: "silip-esp32-test")
    }
    var connectedDeviceId by rememberSaveable { mutableStateOf(deviceId) }
    var householdState by remember {
        mutableStateOf<HouseholdDashboardState>(HouseholdDashboardState.Loading)
    }
    var refreshCount by rememberSaveable { mutableIntStateOf(0) }
    val learningPrefs = remember(context) {
        context.getSharedPreferences("silip_learning_preview", Context.MODE_PRIVATE)
    }

    LaunchedEffect(connectedDeviceId, refreshCount) {
        householdState = HouseholdDashboardState.Loading
        householdState = try {
            HouseholdDashboardState.Loaded(householdApi.getDeviceUsage(connectedDeviceId))
        } catch (cancellation: CancellationException) {
            throw cancellation
        } catch (error: HouseholdApiException) {
            if (error.statusCode == 404) {
                HouseholdDashboardState.NotFound(connectedDeviceId)
            } else {
                HouseholdDashboardState.Error("SILIP could not load this device's readings.")
            }
        } catch (_: IOException) {
            HouseholdDashboardState.Error("Could not reach SILIP. Check your internet and try again.")
        } catch (_: Exception) {
            HouseholdDashboardState.Error("SILIP could not load this device's readings.")
        }
    }
    var selectedName by rememberSaveable { mutableStateOf(Destination.Home.name) }
    var learningXp by rememberSaveable {
        mutableIntStateOf(learningPrefs.getInt("xp", 0).coerceAtLeast(0))
    }
    var completedLessons by rememberSaveable {
        mutableIntStateOf(
            learningPrefs.getInt("completed_lessons", 0)
                .coerceIn(0, LessonCatalog.starterLessons.size)
        )
    }
    var streakDays by rememberSaveable {
        mutableIntStateOf(learningPrefs.getInt("streak_days", 0).coerceAtLeast(0))
    }
    var selectedLessonId by rememberSaveable {
        mutableStateOf(LessonCatalog.starterLessons.first().id)
    }
    val selected = Destination.valueOf(selectedName)
    val topLevel = if (selected == Destination.DailyChallenge) Destination.Learn else selected
    val scheme = MaterialTheme.colorScheme

    BackHandler(enabled = selected == Destination.DailyChallenge) {
        selectedName = Destination.Learn.name
    }

    Scaffold(
        containerColor = scheme.background,
        bottomBar = {
            NavigationBar(
                containerColor = scheme.surface,
                tonalElevation = 0.dp
            ) {
                listOf(Destination.Home, Destination.Usage, Destination.Learn, Destination.Rewards).forEach { destination ->
                    NavigationBarItem(
                        selected = topLevel == destination,
                        onClick = { selectedName = destination.name },
                        icon = {
                            Icon(
                                imageVector = destination.icon,
                                contentDescription = null
                            )
                        },
                        label = { Text(destination.label) },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = scheme.onPrimaryContainer,
                            selectedTextColor = scheme.primary,
                            indicatorColor = scheme.primaryContainer,
                            unselectedIconColor = scheme.onSurfaceVariant,
                            unselectedTextColor = scheme.onSurfaceVariant
                        )
                    )
                }
            }
        }
    ) { contentPadding ->
        when (selected) {
            Destination.Home -> HomeScreen(
                contentPadding = contentPadding,
                householdState = householdState,
                deviceId = deviceId,
                onDeviceIdChange = { deviceId = it },
                onConnectDevice = {
                    val normalizedId = deviceId.trim()
                    if (normalizedId.isNotEmpty()) {
                        deviceId = normalizedId
                        connectedDeviceId = normalizedId
                        devicePreferences.edit().putString("clamp_id", normalizedId).apply()
                        refreshCount += 1
                    }
                },
                onRefreshHousehold = { refreshCount += 1 },
                onOpenChallenge = {
                    val nextIndex = completedLessons.coerceAtMost(LessonCatalog.starterLessons.lastIndex)
                    selectedLessonId = LessonCatalog.starterLessons[nextIndex].id
                    selectedName = Destination.DailyChallenge.name
                }
            )
            Destination.Usage -> UsageScreen(
                contentPadding = contentPadding,
                householdState = householdState,
                deviceId = connectedDeviceId,
                onRefreshHousehold = { refreshCount += 1 }
            )
            Destination.Learn -> LearnScreen(
                contentPadding = contentPadding,
                streakDays = streakDays,
                learningXp = learningXp,
                completedLessons = completedLessons,
                onStartLesson = { lesson ->
                    selectedLessonId = lesson.id
                    selectedName = Destination.DailyChallenge.name
                }
            )
            Destination.Rewards -> RewardsScreen(contentPadding)
            Destination.DailyChallenge -> DailyChallengeScreen(
                contentPadding = contentPadding,
                lesson = LessonCatalog.starterLessons.firstOrNull { it.id == selectedLessonId }
                    ?: LessonCatalog.starterLessons.first(),
                onBack = { selectedName = Destination.Learn.name },
                onLessonCompleted = { lesson ->
                    val lessonIndex = LessonCatalog.starterLessons.indexOfFirst { it.id == lesson.id }
                    if (lessonIndex >= completedLessons) {
                        val nextCompletedLessons = lessonIndex + 1
                        val nextXp = learningXp + lesson.points
                        val nextStreakDays = maxOf(streakDays, 1)
                        completedLessons = nextCompletedLessons
                        learningXp = nextXp
                        streakDays = nextStreakDays
                        learningPrefs.edit()
                            .putInt("completed_lessons", nextCompletedLessons)
                            .putInt("xp", nextXp)
                            .putInt("streak_days", nextStreakDays)
                            .apply()
                    }
                }
            )
        }
    }
}

@Composable
private fun HomeScreen(
    contentPadding: PaddingValues,
    householdState: HouseholdDashboardState,
    deviceId: String,
    onDeviceIdChange: (String) -> Unit,
    onConnectDevice: () -> Unit,
    onRefreshHousehold: () -> Unit,
    onOpenChallenge: () -> Unit
) {
    AdaptivePage(contentPadding) {
        item {
            PageHeader(
                eyebrow = "HOME",
                title = "Welcome home.",
                subtitle = "Your household, at a glance.",
                pose = AliPose.Welcome
            )
        }
        item {
            HouseholdDataCard(
                state = householdState,
                deviceId = deviceId,
                onDeviceIdChange = onDeviceIdChange,
                showDeviceInput = true,
                onConnect = onConnectDevice,
                onRefresh = onRefreshHousehold,
            )
        }
        item {
            SectionHeading(
                title = "Home safety",
                subtitle = "Sensor sees total load."
            )
        }
        item { SafetyPreviewCard() }
        item { QuickLessonCard(onClick = onOpenChallenge) }
    }
}

@Composable
private fun UsageScreen(
    contentPadding: PaddingValues,
    householdState: HouseholdDashboardState,
    deviceId: String,
    onRefreshHousehold: () -> Unit
) {
    AdaptivePage(contentPadding) {
        item {
            PageHeader(
                eyebrow = "USAGE",
                title = "See what you use.",
                subtitle = "Whole-home readings from your registered device.",
                pose = AliPose.HouseholdCheck
            )
        }
        item {
            HouseholdDataCard(
                state = householdState,
                deviceId = deviceId,
                onDeviceIdChange = {},
                showDeviceInput = false,
                onConnect = onRefreshHousehold,
                onRefresh = onRefreshHousehold,
            )
        }
        if (householdState is HouseholdDashboardState.Loaded) {
            item { HouseholdUsageTrendCard(points = householdState.device.points) }
        }
        item {
            SectionHeading(
                title = "Energy clues",
                subtitle = "Preview concepts · not live yet"
            )
        }
        item {
            InsightPreviewCard(
                title = "Phantom load detective",
                label = "Example",
                description = "Spot standby use overnight. Sample estimate only.",
                icon = Icons.Outlined.Lightbulb,
                mascotPose = AliPose.Practice
            )
        }
        item {
            InsightPreviewCard(
                title = "Appliance health",
                label = "In development",
                description = "Total load only. No appliance diagnosis yet.",
                icon = Icons.Outlined.Bolt,
                mascotPose = AliPose.HouseholdCheck
            )
        }
    }
}

@Composable
private fun BillForecastCard() {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = androidx.compose.foundation.shape.RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp)
    ) {
        Column(
            modifier = Modifier.padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Projected month-end bill",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
                PreviewBadge(label = "Example")
            }
            Text(
                text = "₱3,480",
                style = MaterialTheme.typography.headlineLarge.copy(
                    fontFamily = FontFamily.Monospace,
                    fontWeight = FontWeight.Bold
                ),
                color = MaterialTheme.colorScheme.onSurface
            )
            Text(
                text = "Sample projection · actual bills may vary",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Text(
                text = "₱520 under the sample budget",
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.primary
            )
        }
    }
}

@Composable
private fun LearnScreen(
    contentPadding: PaddingValues,
    streakDays: Int,
    learningXp: Int,
    completedLessons: Int,
    onStartLesson: (Lesson) -> Unit
) {
    AdaptivePage(contentPadding, backgroundRes = R.drawable.learn_map_background) {
        item { LearningStatsRow(streak = streakDays, xp = learningXp) }
        item { LearningUnitBanner(completed = completedLessons, total = LessonCatalog.starterLessons.size) }
        item {
            LearningMap(
                lessons = LessonCatalog.starterLessons,
                completedLessons = completedLessons,
                onStart = onStartLesson
            )
        }
    }
}

@Composable
private fun DailyChallengeScreen(
    contentPadding: PaddingValues,
    lesson: Lesson,
    onBack: () -> Unit,
    onLessonCompleted: (Lesson) -> Unit
) {
    val questions = LessonQuizCatalog.questionsFor(lesson.id)
    var questionIndex by rememberSaveable(lesson.id) { mutableIntStateOf(0) }
    var selectedId by rememberSaveable(lesson.id) { mutableStateOf<String?>(null) }
    var submitted by rememberSaveable(lesson.id) { mutableStateOf(false) }
    val question = questions[questionIndex.coerceIn(questions.indices)]
    val answer = question.answers.firstOrNull { it.id == selectedId }
    val lessonNumber = LessonCatalog.starterLessons.indexOfFirst { it.id == lesson.id } + 1

    AdaptivePage(contentPadding) {
        item {
            if (submitted && answer != null) {
                ChallengeFeedbackCard(
                    isCorrect = answer.correct,
                    explanation = question.explanation
                )
            } else {
                PageHeader(
                    eyebrow = "UNIT $lessonNumber · QUICK PRACTICE",
                    title = lesson.title,
                    subtitle = "${questions.size} questions · +${lesson.points} XP",
                    pose = AliPose.Practice
                )
            }
        }
        item {
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text(
                    text = "QUESTION ${questionIndex + 1} OF ${questions.size}",
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary
                )
                Text(
                    text = question.prompt,
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.semantics { heading() }
                )
            }
        }
        items(question.answers, key = ChallengeAnswer::id) { option ->
            ChallengeAnswerCard(
                text = option.text,
                selected = selectedId == option.id,
                enabled = !submitted,
                onClick = { selectedId = option.id }
            )
        }
        if (!submitted) item {
            Button(
                onClick = { submitted = true },
                enabled = selectedId != null && !submitted,
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("Check answer")
            }
        }
        if (submitted && answer != null) {
            item {
                if (answer.correct) {
                    Button(
                        onClick = {
                            if (questionIndex == questions.lastIndex) {
                                onLessonCompleted(lesson)
                                questionIndex = 0
                                selectedId = null
                                submitted = false
                                onBack()
                            } else {
                                questionIndex += 1
                                selectedId = null
                                submitted = false
                            }
                        },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(if (questionIndex == questions.lastIndex) "Finish lesson" else "Next")
                    }
                } else {
                    OutlinedButton(
                        onClick = {
                            selectedId = null
                            submitted = false
                        },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Try again")
                    }
                }
            }
        }
        item {
            OutlinedButton(
                onClick = {
                    questionIndex = 0
                    selectedId = null
                    submitted = false
                    onBack()
                },
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("Back to lessons")
            }
        }
    }
}

@Composable
private fun RewardsScreen(contentPadding: PaddingValues) {
    AdaptivePage(contentPadding) {
        item {
            PageHeader(
                eyebrow = "GRID PARTNERSHIP",
                title = "Help your neighborhood.",
                subtitle = "Join a future peak event.",
                pose = AliPose.Success
            )
        }
        item { GridResponseCard() }
        item { GridParticipationSteps() }
        item {
            SectionHeading(
                title = "You’re in control",
                subtitle = "Events stay optional."
            )
        }
        item {
            InsightPreviewCard(
                title = "Your choice, every time",
                label = "Planned",
                description = "Review each event. Joining stays optional.",
                icon = Icons.Outlined.TipsAndUpdates,
                mascotPose = AliPose.Caution
            )
        }
        item {
            InsightPreviewCard(
                title = "Neighborhood leagues",
                label = "Planned",
                description = "Opt-in streaks and rewards · coming later",
                icon = Icons.Outlined.EmojiEvents,
                mascotPose = AliPose.Success
            )
        }
    }
}

@Composable
private fun AdaptivePage(
    contentPadding: PaddingValues,
    backgroundRes: Int? = null,
    content: LazyListScope.() -> Unit
) {
    BoxWithConstraints(modifier = Modifier.fillMaxSize()) {
        val horizontalGutter = if (maxWidth >= 600.dp) 32.dp else 20.dp
        if (backgroundRes != null && !isSystemInDarkTheme()) {
            Image(
                painter = painterResource(backgroundRes),
                contentDescription = null,
                contentScale = ContentScale.Crop,
                modifier = Modifier.fillMaxSize()
            )
        }
        LazyColumn(
            modifier = Modifier
                .widthIn(max = 720.dp)
                .fillMaxSize()
                .align(Alignment.TopCenter),
            contentPadding = PaddingValues(
                start = horizontalGutter,
                top = contentPadding.calculateTopPadding() + 20.dp,
                end = horizontalGutter,
                bottom = contentPadding.calculateBottomPadding() + 24.dp
            ),
            verticalArrangement = Arrangement.spacedBy(16.dp),
            content = content
        )
    }
}
