package com.alventur.silipapp.ui

import android.content.Context
import androidx.activity.compose.BackHandler
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.Crossfade
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.Image
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.MenuBook
import androidx.compose.material.icons.automirrored.outlined.ArrowForward
import androidx.compose.material.icons.automirrored.outlined.MenuBook
import androidx.compose.material.icons.filled.Bolt
import androidx.compose.material.icons.filled.CardGiftcard
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.outlined.Bolt
import androidx.compose.material.icons.outlined.CardGiftcard
import androidx.compose.material.icons.outlined.EmojiEvents
import androidx.compose.material.icons.outlined.Home
import androidx.compose.material.icons.outlined.Lightbulb
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.graphics.luminance
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.alventur.silipapp.R
import com.alventur.silipapp.data.demo.DemoHousehold
import com.alventur.silipapp.data.local.ProgressStore
import com.alventur.silipapp.data.local.manilaToday
import com.alventur.silipapp.data.remote.HouseholdApi
import com.alventur.silipapp.data.remote.HouseholdApiException
import com.alventur.silipapp.data.remote.HouseholdDashboardState
import com.alventur.silipapp.education.ChallengeAnswer
import com.alventur.silipapp.education.Lesson
import com.alventur.silipapp.education.LessonCatalog
import com.alventur.silipapp.education.LessonQuizCatalog
import com.alventur.silipapp.notifications.AwayMonitor
import com.alventur.silipapp.ui.design.SilipMotion
import com.alventur.silipapp.ui.design.StreakFlame
import com.alventur.silipapp.ui.design.orSnap
import com.alventur.silipapp.ui.design.pressScale
import com.alventur.silipapp.ui.design.rememberHaptics
import com.alventur.silipapp.ui.design.rememberReduceMotion
import com.alventur.silipapp.ui.grid.GridEventScreen
import com.alventur.silipapp.ui.home.HomeScreen
import com.alventur.silipapp.ui.learn.DailyQuizScreen
import com.alventur.silipapp.ui.learn.LeaderboardScreen
import com.alventur.silipapp.ui.onboarding.OnboardingFlow
import com.alventur.silipapp.ui.theme.SilipTheme
import java.io.IOException
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch

/**
 * App destinations. The first four are the bottom bar; the rest are sub-screens whose
 * bottom-bar owner is [parent]. Settings opens from the top bar.
 */
private enum class Destination(
    val label: String,
    val icon: ImageVector,
    val selectedIcon: ImageVector = icon,
    val parent: Destination? = null
) {
    Home("Home", Icons.Outlined.Home, Icons.Filled.Home),
    Usage("Usage", Icons.Outlined.Bolt, Icons.Filled.Bolt),
    Learn("Learn", Icons.AutoMirrored.Outlined.MenuBook, Icons.AutoMirrored.Filled.MenuBook),
    Rewards("Grid events", Icons.Outlined.CardGiftcard, Icons.Filled.CardGiftcard),
    Settings("Settings", Icons.Outlined.Settings),
    Solar("Solar", Icons.Outlined.Lightbulb, parent = Home),
    DailyChallenge("Lesson", Icons.Outlined.Lightbulb, parent = Learn),
    DailyQuiz("Today's quiz", Icons.Outlined.Lightbulb, parent = Learn),
    Leaderboard("Leaderboard", Icons.Outlined.EmojiEvents, parent = Learn)
}

private val BottomDestinations = listOf(Destination.Home, Destination.Usage, Destination.Learn, Destination.Rewards)

@Composable
fun SilipApp(
    householdApi: HouseholdApi
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val store = remember(context) { ProgressStore.get(context) }
    val progress by store.progress.collectAsState()
    val demoEvents = remember { DemoEventBus() }
    val settingsPreferences = remember(context) {
        context.getSharedPreferences("silip_demo_device", Context.MODE_PRIVATE)
    }
    var showOnboarding by rememberSaveable { mutableStateOf(!store.progress.value.onboarded) }
    var deviceId by rememberSaveable { mutableStateOf(store.deviceId()) }
    var connectedDeviceId by rememberSaveable { mutableStateOf(deviceId) }
    var userName by rememberSaveable {
        mutableStateOf(settingsPreferences.getString("user_name", "") ?: "")
    }
    var themeMode by rememberSaveable {
        mutableStateOf(settingsPreferences.getString("theme_mode", "system") ?: "system")
    }
    var householdState by remember {
        mutableStateOf<HouseholdDashboardState>(HouseholdDashboardState.Loading)
    }
    var refreshCount by rememberSaveable { mutableIntStateOf(0) }

    LaunchedEffect(connectedDeviceId, refreshCount, progress.usingDemoHome) {
        householdState = HouseholdDashboardState.Loading
        if (progress.usingDemoHome) {
            // Rosa's demo home: simulated readings, labeled "Simulated" by every existing card.
            householdState = HouseholdDashboardState.Loaded(DemoHousehold.deviceUsage())
            return@LaunchedEffect
        }
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
    var beforeSettings by rememberSaveable { mutableStateOf(Destination.Home.name) }
    var selectedLessonId by rememberSaveable {
        mutableStateOf(LessonCatalog.starterLessons.first().id)
    }
    val selected = Destination.valueOf(selectedName)
    val topLevel = selected.parent ?: selected
    val completedLessons = progress.completedLessons.coerceIn(0, LessonCatalog.starterLessons.size)

    BackHandler(enabled = !showOnboarding && (selected.parent != null || selected == Destination.Settings)) {
        selectedName = if (selected == Destination.Settings) beforeSettings else topLevel.name
    }

    val darkTheme = when (themeMode) {
        "light" -> false
        "dark" -> true
        else -> isSystemInDarkTheme()
    }
    val reduceMotion = rememberReduceMotion()

    SilipTheme(
        darkTheme = darkTheme,
        originalPalette = !showOnboarding && topLevel == Destination.Learn
    ) {
        AnimatedContent(
            targetState = showOnboarding,
            transitionSpec = {
                if (reduceMotion) fadeIn(SilipMotion.short()) togetherWith fadeOut(SilipMotion.short())
                else fadeIn(SilipMotion.enter()) togetherWith fadeOut(SilipMotion.standard())
            },
            label = "onboarding-or-app"
        ) { onboarding ->
            if (onboarding) {
                OnboardingFlow(onFinished = {
                    // Onboarding may have saved a device ID or switched to the demo home.
                    deviceId = store.deviceId()
                    connectedDeviceId = deviceId
                    refreshCount += 1
                    selectedName = Destination.Home.name
                    showOnboarding = false
                })
                return@AnimatedContent
            }
            val scheme = MaterialTheme.colorScheme
            Scaffold(
                containerColor = scheme.background,
                topBar = {
                    Surface(color = scheme.background) {
                        Row(Modifier.fillMaxWidth().statusBarsPadding().padding(start = 20.dp, end = 12.dp),
                            verticalAlignment = Alignment.CenterVertically) {
                            Text("silip", style = MaterialTheme.typography.titleLarge,
                                color = scheme.primary, modifier = Modifier.weight(1f))
                            IconButton(onClick = {
                                if (selected != Destination.Settings) beforeSettings = selectedName
                                selectedName = if (selected == Destination.Settings) beforeSettings else Destination.Settings.name
                            }) {
                                Icon(Icons.Outlined.Settings, contentDescription = if (selected == Destination.Settings) "Return to previous screen" else "Open settings")
                            }
                        }
                    }
                },
                bottomBar = {
                    SilipBottomBar(
                        current = topLevel,
                        onSelect = { selectedName = it.name }
                    )
                }
            ) { contentPadding ->
                when (selected) {
                    Destination.Home -> HomeScreen(
                        contentPadding = contentPadding,
                        householdState = householdState,
                        progress = progress,
                        userName = userName,
                        nextLesson = LessonCatalog.starterLessons[completedLessons.coerceAtMost(LessonCatalog.starterLessons.lastIndex)],
                        demoEvents = demoEvents,
                        onOpenUsage = { selectedName = Destination.Usage.name },
                        onOpenSolar = { selectedName = Destination.Solar.name },
                        onOpenLesson = {
                            val nextIndex = completedLessons.coerceAtMost(LessonCatalog.starterLessons.lastIndex)
                            selectedLessonId = LessonCatalog.starterLessons[nextIndex].id
                            selectedName = Destination.DailyChallenge.name
                        },
                        onOpenQuiz = { selectedName = Destination.DailyQuiz.name },
                        onOpenGridEvent = { selectedName = Destination.Rewards.name },
                        onRefreshHousehold = { refreshCount += 1 }
                    )
                    Destination.Usage -> UsageScreen(
                        contentPadding = contentPadding,
                        householdState = householdState,
                        onRefreshHousehold = { refreshCount += 1 }
                    )
                    Destination.Learn -> LearnScreen(
                        contentPadding = contentPadding,
                        streakDays = progress.streak.displayCount(manilaToday()),
                        streakLitToday = progress.streak.isLitToday(manilaToday()),
                        quizDoneToday = progress.quizDoneToday(),
                        learningXp = progress.xp,
                        completedLessons = completedLessons,
                        onStartLesson = { lesson ->
                            selectedLessonId = lesson.id
                            selectedName = Destination.DailyChallenge.name
                        },
                        onOpenQuiz = { selectedName = Destination.DailyQuiz.name },
                        onOpenLeaderboard = { selectedName = Destination.Leaderboard.name }
                    )
                    Destination.Solar -> SolarScreen(contentPadding, householdState, onBack = { selectedName = Destination.Home.name })
                    Destination.Rewards -> GridEventScreen(contentPadding, demoEvents)
                    Destination.DailyQuiz -> DailyQuizScreen(contentPadding, onBack = { selectedName = Destination.Learn.name })
                    Destination.Leaderboard -> LeaderboardScreen(contentPadding, onBack = { selectedName = Destination.Learn.name })
                    Destination.Settings -> SettingsScreen(
                        contentPadding = contentPadding,
                        userName = userName,
                        onUserNameChange = { userName = it },
                        deviceId = deviceId,
                        onDeviceIdChange = { deviceId = it },
                        connectedDeviceId = connectedDeviceId,
                        connectionState = householdState,
                        themeMode = themeMode,
                        onThemeModeChange = { newThemeMode ->
                            themeMode = newThemeMode
                            settingsPreferences.edit().putString("theme_mode", newThemeMode).apply()
                        },
                        onSaveAndConnect = {
                            val normalizedId = deviceId.trim()
                            if (normalizedId.isNotEmpty()) {
                                val normalizedName = userName.trim()
                                userName = normalizedName
                                if (normalizedId != connectedDeviceId) {
                                    AwayMonitor.prefs(context).edit().putBoolean("auto", false).remove("lat").remove("lon").apply()
                                    AwayMonitor.setAway(context, false)
                                    scope.launch { AwayMonitor.disable(context) }
                                }
                                deviceId = normalizedId
                                connectedDeviceId = normalizedId
                                settingsPreferences.edit()
                                    .putString("clamp_id", normalizedId)
                                    .putString("user_name", normalizedName)
                                    .apply()
                                store.setUsingDemoHome(false)
                                refreshCount += 1
                            }
                        },
                        usingDemoHome = progress.usingDemoHome,
                        onUseDemoHome = {
                            store.setUsingDemoHome(true)
                            refreshCount += 1
                        },
                        onReplayIntro = {
                            store.replayOnboarding()
                            showOnboarding = true
                        },
                        onShowSampleAlert = {
                            store.clearAlert(DemoHousehold.safetyAlert.id)
                            demoEvents.send(DemoEvent.ShowSafetyAlert)
                            selectedName = Destination.Home.name
                        }
                    )
                    Destination.DailyChallenge -> DailyChallengeScreen(
                        contentPadding = contentPadding,
                        lesson = LessonCatalog.starterLessons.firstOrNull { it.id == selectedLessonId }
                            ?: LessonCatalog.starterLessons.first(),
                        onBack = { selectedName = Destination.Learn.name },
                        onLessonCompleted = { lesson ->
                            val lessonIndex = LessonCatalog.starterLessons.indexOfFirst { it.id == lesson.id }
                            if (lessonIndex >= 0) store.completeLesson(lessonIndex, lesson.points)
                        }
                    )
                }
            }
        }
    }
}

/** Bottom bar: the selected icon fills and springs up; the label turns bold. */
@Composable
private fun SilipBottomBar(current: Destination, onSelect: (Destination) -> Unit) {
    val scheme = MaterialTheme.colorScheme
    val haptics = rememberHaptics()
    val reduceMotion = rememberReduceMotion()
    NavigationBar(
        containerColor = scheme.surface,
        tonalElevation = 0.dp
    ) {
        BottomDestinations.forEach { destination ->
            val isSelected = current == destination
            val scale by animateFloatAsState(
                targetValue = if (isSelected) 1.12f else 1f,
                animationSpec = SilipMotion.playful<Float>().orSnap(reduceMotion),
                label = "nav-icon-scale"
            )
            NavigationBarItem(
                selected = isSelected,
                onClick = {
                    if (!isSelected) haptics.select()
                    onSelect(destination)
                },
                icon = {
                    Crossfade(
                        targetState = isSelected,
                        animationSpec = SilipMotion.short(),
                        label = "nav-icon-fill",
                        modifier = Modifier.graphicsLayer {
                            scaleX = scale
                            scaleY = scale
                        }
                    ) { filled ->
                        Icon(
                            imageVector = if (filled) destination.selectedIcon else destination.icon,
                            contentDescription = null
                        )
                    }
                },
                label = {
                    Text(
                        destination.label,
                        fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium
                    )
                },
                alwaysShowLabel = true,
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

@Composable
private fun SolarScreen(contentPadding: PaddingValues, householdState: HouseholdDashboardState, onBack: () -> Unit) {
    AdaptivePage(contentPadding) {
        item { SolarIntroduction(onBack) }
        item { SolarDaytimeCard(householdState) }
        item { SolarHowItWorks() }
        item { SolarPreparationCard() }
    }
}

@Composable
private fun UsageScreen(
    contentPadding: PaddingValues,
    householdState: HouseholdDashboardState,
    onRefreshHousehold: () -> Unit
) {
    AdaptivePage(contentPadding) {
        item { SectionHeading("Usage", "Understand when your energy adds up.") }
        if (householdState is HouseholdDashboardState.Loaded) {
            item { UsageExplorer(householdState.device, onRefreshHousehold) }
            item { ForecastAndInsights(householdState.device) }
            item { SectionHeading("Cost & calculation") }
            item { PriceEstimateCard(householdState.device) }
            item { ReadingDetails(householdState.device) }
        } else {
            item { HouseholdSnapshot(householdState, onRefreshHousehold) }
        }
        item { SectionHeading("Get to know your numbers") }
        item { UsageMeaningCard() }
    }
}

@Composable
private fun SettingsScreen(
    contentPadding: PaddingValues,
    userName: String,
    onUserNameChange: (String) -> Unit,
    deviceId: String,
    onDeviceIdChange: (String) -> Unit,
    connectedDeviceId: String,
    connectionState: HouseholdDashboardState,
    themeMode: String,
    onThemeModeChange: (String) -> Unit,
    onSaveAndConnect: () -> Unit,
    usingDemoHome: Boolean,
    onUseDemoHome: () -> Unit,
    onReplayIntro: () -> Unit,
    onShowSampleAlert: () -> Unit
) {
    AdaptivePage(contentPadding) {
        item {
            PageHeader(
                eyebrow = "SETTINGS",
                title = "Make it yours.",
                subtitle = "Set your name and connect your home device.",
                pose = AliPose.Welcome
            )
        }
        item {
            HouseholdSettingsCard(
                userName = userName,
                onUserNameChange = onUserNameChange,
                deviceId = deviceId,
                onDeviceIdChange = onDeviceIdChange,
                connectedDeviceId = if (usingDemoHome) DemoHousehold.HOUSEHOLD_NAME else connectedDeviceId,
                connectionState = connectionState,
                themeMode = themeMode,
                onThemeModeChange = onThemeModeChange,
                onSaveAndConnect = onSaveAndConnect
            )
        }
        item {
            DemoToolsCard(
                usingDemoHome = usingDemoHome,
                onUseDemoHome = onUseDemoHome,
                onReplayIntro = onReplayIntro,
                onShowSampleAlert = onShowSampleAlert
            )
        }
    }
}

/** Demo and intro controls. The sample alert opens on Home. */
@Composable
private fun DemoToolsCard(
    usingDemoHome: Boolean,
    onUseDemoHome: () -> Unit,
    onReplayIntro: () -> Unit,
    onShowSampleAlert: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp)
    ) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("Intro and demo", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Text(
                if (usingDemoHome) "You're exploring Rosa's demo home. Its readings are simulated."
                else "Try Rosa's demo home to see every feature with simulated readings.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            if (!usingDemoHome) {
                OutlinedButton(onClick = onUseDemoHome, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) {
                    Text("Explore the demo home (Rosa's)")
                }
            }
            OutlinedButton(onClick = onShowSampleAlert, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) {
                Text("Show a sample safety alert")
            }
            OutlinedButton(onClick = onReplayIntro, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) {
                Text("Replay intro")
            }
        }
    }
}

@Composable
private fun LearnScreen(
    contentPadding: PaddingValues,
    streakDays: Int,
    streakLitToday: Boolean,
    quizDoneToday: Boolean,
    learningXp: Int,
    completedLessons: Int,
    onStartLesson: (Lesson) -> Unit,
    onOpenQuiz: () -> Unit,
    onOpenLeaderboard: () -> Unit
) {
    AdaptivePage(contentPadding, backgroundRes = R.drawable.learn_map_background) {
        item { LearningStatsRow(streak = streakDays, xp = learningXp) }
        item {
            // WAVE 2: Learn/engagement owner restyles this entry row (quiz card, leaderboard, badges shelf).
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(24.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                border = CardDefaults.outlinedCardBorder()
            ) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        StreakFlame(days = streakDays, litToday = streakLitToday)
                        Column(Modifier.weight(1f)) {
                            Text("Today's quiz", style = MaterialTheme.typography.titleMedium,
                                modifier = Modifier.semantics { heading() })
                            Text(
                                if (quizDoneToday) "Done for today." else "15 seconds keeps your streak going.",
                                style = MaterialTheme.typography.bodySmall
                            )
                        }
                    }
                    if (!quizDoneToday) {
                        Button(onClick = onOpenQuiz, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp).pressScale()) {
                            Text("Take today's quiz")
                        }
                    }
                    OutlinedButton(onClick = onOpenLeaderboard, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) {
                        Text("Leaderboard and badges", Modifier.weight(1f))
                        Icon(Icons.AutoMirrored.Outlined.ArrowForward, contentDescription = null)
                    }
                }
            }
        }
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

/**
 * Standard page: a centered LazyColumn (max 720 dp) with 20 dp phone gutters (32 dp on tablets),
 * padding for the top and bottom bars, and 16 dp between items. Use it for every tab and sub-screen.
 */
@Composable
internal fun AdaptivePage(
    contentPadding: PaddingValues,
    backgroundRes: Int? = null,
    content: LazyListScope.() -> Unit
) {
    BoxWithConstraints(modifier = Modifier.fillMaxSize()) {
        val horizontalGutter = if (maxWidth >= 600.dp) 32.dp else 20.dp
        if (backgroundRes != null && MaterialTheme.colorScheme.background.luminance() > 0.5f) {
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
