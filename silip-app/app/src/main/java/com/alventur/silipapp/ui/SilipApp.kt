package com.alventur.silipapp.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.MenuBook
import androidx.compose.material.icons.outlined.Bolt
import androidx.compose.material.icons.outlined.Home
import androidx.compose.material.icons.outlined.PowerSettingsNew
import androidx.compose.material.icons.outlined.Quiz
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.alventur.silipapp.education.Lesson
import com.alventur.silipapp.education.LessonCatalog

private enum class Destination(
    val label: String,
    val icon: ImageVector
) {
    Home("Home", Icons.Outlined.Home),
    Learn("Learn", Icons.AutoMirrored.Outlined.MenuBook),
    Practice("Practice", Icons.Outlined.Quiz),
    Household("My home", Icons.Outlined.PowerSettingsNew)
}

private data class PracticeAnswer(
    val id: String,
    val text: String,
    val isCorrect: Boolean
)

private val leaveHomeAnswers = listOf(
    PracticeAnswer(
        id = "switch-off-nonessential",
        text = "Switch off non-essential appliances and keep essential items, such as the refrigerator, powered.",
        isCorrect = true
    ),
    PracticeAnswer(
        id = "unplug-everything",
        text = "Unplug every appliance before leaving, including the refrigerator.",
        isCorrect = false
    ),
    PracticeAnswer(
        id = "leave-standby",
        text = "Leave appliances on standby so they are ready when you return.",
        isCorrect = false
    )
)

@Composable
fun SilipApp() {
    var selectedName by rememberSaveable { mutableStateOf(Destination.Home.name) }
    val selected = Destination.valueOf(selectedName)
    val scheme = MaterialTheme.colorScheme

    Scaffold(
        bottomBar = {
            NavigationBar(
                containerColor = scheme.primary,
                tonalElevation = 0.dp
            ) {
                Destination.entries.forEach { destination ->
                    NavigationBarItem(
                        selected = selected == destination,
                        onClick = { selectedName = destination.name },
                        icon = {
                            androidx.compose.material3.Icon(
                                imageVector = destination.icon,
                                contentDescription = null
                            )
                        },
                        label = { Text(destination.label) },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = scheme.onSecondaryContainer,
                            selectedTextColor = scheme.onPrimary,
                            indicatorColor = scheme.secondaryContainer,
                            unselectedIconColor = scheme.onPrimary.copy(alpha = 0.88f),
                            unselectedTextColor = scheme.onPrimary.copy(alpha = 0.88f)
                        )
                    )
                }
            }
        }
    ) { innerPadding ->
        when (selected) {
            Destination.Home -> HomeScreen(
                contentPadding = innerPadding,
                onOpenLearn = { selectedName = Destination.Learn.name },
                onOpenPractice = { selectedName = Destination.Practice.name },
                onOpenHousehold = { selectedName = Destination.Household.name }
            )

            Destination.Learn -> LearnScreen(contentPadding = innerPadding)
            Destination.Practice -> PracticeScreen(contentPadding = innerPadding)
            Destination.Household -> HouseholdScreen(contentPadding = innerPadding)
        }
    }
}

@Composable
private fun HomeScreen(
    contentPadding: PaddingValues,
    onOpenLearn: () -> Unit,
    onOpenPractice: () -> Unit,
    onOpenHousehold: () -> Unit
) {
    val scheme = MaterialTheme.colorScheme
    val actions = listOf(
        HomeAction(
            title = "Learn",
            supportingText = "Build safer energy habits, one short lesson at a time.",
            icon = Icons.AutoMirrored.Outlined.MenuBook,
            containerColor = scheme.primaryContainer,
            contentColor = scheme.onPrimaryContainer,
            onClick = onOpenLearn
        ),
        HomeAction(
            title = "Practice",
            supportingText = "Try a quick home-safety check.",
            icon = Icons.Outlined.Quiz,
            containerColor = scheme.secondaryContainer,
            contentColor = scheme.onSecondaryContainer,
            onClick = onOpenPractice
        ),
        HomeAction(
            title = "My home",
            supportingText = "See how household readings will appear.",
            icon = Icons.Outlined.Home,
            containerColor = scheme.tertiaryContainer,
            contentColor = scheme.onTertiaryContainer,
            onClick = onOpenHousehold
        ),
        HomeAction(
            title = "Leaving-home check",
            supportingText = "Practice a quick safety check before you head out.",
            icon = Icons.Outlined.PowerSettingsNew,
            containerColor = scheme.surfaceVariant,
            contentColor = scheme.onSurfaceVariant,
            onClick = onOpenPractice
        )
    )

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = screenPadding(contentPadding),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            AliSectionHeader(
                eyebrow = "SILIP HOME GUIDE",
                title = "Your home, in sight.",
                message = "I’ll help you understand your household energy and build safer everyday habits.",
                pose = AliPose.Welcome
            )
        }
        item {
            HouseholdStatusCard(onOpenHousehold = onOpenHousehold)
        }
        item {
            SectionHeading(
                title = "A small step for today",
                subtitle = "Start with a short lesson on everyday electricity."
            )
            Spacer(modifier = Modifier.height(4.dp))
            LearningPathCard(
                title = "Home energy basics",
                completedLessons = 0,
                totalLessons = LessonCatalog.starterLessons.size,
                onClick = onOpenLearn
            )
        }
        item {
            SectionHeading(
                title = "Explore SILIP",
                subtitle = "Learn, practice, and check in on your home."
            )
        }
        items(actions.chunked(2), key = { row -> row.first().title }) { row ->
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                row.forEach { action ->
                    HomeActionTile(
                        action = action,
                        modifier = Modifier.weight(1f)
                    )
                }
                if (row.size == 1) Spacer(modifier = Modifier.weight(1f))
            }
        }
    }
}

private data class HomeAction(
    val title: String,
    val supportingText: String,
    val icon: ImageVector,
    val containerColor: androidx.compose.ui.graphics.Color,
    val contentColor: androidx.compose.ui.graphics.Color,
    val onClick: () -> Unit
)

@Composable
private fun HomeActionTile(
    action: HomeAction,
    modifier: Modifier = Modifier
) {
    ActionTile(
        title = action.title,
        supportingText = action.supportingText,
        icon = action.icon,
        containerColor = action.containerColor,
        contentColor = action.contentColor,
        onClick = action.onClick,
        modifier = modifier
    )
}

@Composable
private fun LearnScreen(contentPadding: PaddingValues) {
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = screenPadding(contentPadding),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            AliSectionHeader(
                eyebrow = "YOUR LEARNING PATH",
                title = "Small lessons. Safer habits.",
                message = "Let’s learn one practical electricity habit at a time.",
                pose = AliPose.Learning
            )
        }
        item {
            LearningPathCard(
                title = "Home energy basics",
                completedLessons = 0,
                totalLessons = LessonCatalog.starterLessons.size
            )
        }
        item {
            SectionHeading(
                title = "Unit 1 · Everyday electricity",
                subtitle = "Start here and learn at your own pace."
            )
        }
        items(LessonCatalog.starterLessons, key = Lesson::id) { lesson ->
            EnergyLessonCard(lesson)
        }
        item {
            InformationCard(
                title = "Learn at your own pace",
                description = "Learning content is available on this device. Live household readings need an internet connection and a linked SILIP account.",
                icon = Icons.Outlined.Bolt,
                containerColor = MaterialTheme.colorScheme.secondaryContainer,
                contentColor = MaterialTheme.colorScheme.onSecondaryContainer
            )
        }
    }
}

@Composable
private fun PracticeScreen(contentPadding: PaddingValues) {
    var selectedAnswerId by rememberSaveable { mutableStateOf<String?>(null) }
    var isSubmitted by rememberSaveable { mutableStateOf(false) }
    val selectedAnswer = leaveHomeAnswers.firstOrNull { it.id == selectedAnswerId }

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = screenPadding(contentPadding),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            AliSectionHeader(
                eyebrow = "PRACTICE",
                title = "Ready for a quick check?",
                message = "Take a moment and choose what you think is safest.",
                pose = AliPose.Practice
            )
        }
        item {
            StepProgressCard(
                label = "Home safety quick check",
                step = 1,
                total = 1
            )
        }
        item {
            Text(
                text = "You are heading out for the day. What is the safer energy habit?",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.semantics { heading() }
            )
        }
        items(leaveHomeAnswers, key = PracticeAnswer::id) { answer ->
            AnswerOptionCard(
                text = answer.text,
                selected = selectedAnswerId == answer.id,
                enabled = !isSubmitted,
                onClick = { selectedAnswerId = answer.id }
            )
        }
        item {
            Button(
                onClick = { isSubmitted = true },
                enabled = selectedAnswerId != null && !isSubmitted,
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(if (isSubmitted) "Answer checked" else "Check answer")
            }
        }
        if (isSubmitted && selectedAnswer != null) {
            item {
                AnswerFeedbackCard(isCorrect = selectedAnswer.isCorrect)
            }
            item {
                androidx.compose.material3.TextButton(
                    onClick = {
                        selectedAnswerId = null
                        isSubmitted = false
                    },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Try again")
                }
            }
        }
    }
}

@Composable
private fun HouseholdScreen(contentPadding: PaddingValues) {
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = screenPadding(contentPadding),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            AliSectionHeader(
                eyebrow = "MY HOME",
                title = "Your household at a glance.",
                message = "I can’t read your home status yet. Link your account to see household readings.",
                pose = AliPose.Caution
            )
        }
        item {
            HouseholdStatusCard()
        }
        item {
            InformationCard(
                title = "What the sensor can tell us",
                description = "The current sensor measures total household electrical demand. It cannot identify which individual appliance is on.",
                icon = Icons.Outlined.Bolt,
                containerColor = MaterialTheme.colorScheme.primaryContainer,
                contentColor = MaterialTheme.colorScheme.onPrimaryContainer
            )
        }
        item {
            InformationCard(
                title = "A reminder when you leave",
                description = "An optional home-exit reminder can open a checklist for non-essential appliances. It is a prompt to check, not a sensor-based appliance alert.",
                icon = Icons.Outlined.PowerSettingsNew,
                containerColor = MaterialTheme.colorScheme.tertiaryContainer,
                contentColor = MaterialTheme.colorScheme.onTertiaryContainer
            )
        }
        item {
            Text(
                text = "An internet connection is needed to refresh household readings. Learning content can remain available on this device.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(horizontal = 4.dp)
            )
        }
    }
}

@Composable
private fun HouseholdStatusCard(onOpenHousehold: (() -> Unit)? = null) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = androidx.compose.foundation.shape.RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        androidx.compose.foundation.layout.Column(
            modifier = Modifier.padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = androidx.compose.ui.Alignment.CenterVertically
            ) {
                Text(
                    text = "Household status",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.weight(1f)
                )
                StatusPill(
                    label = "Not connected",
                    containerColor = MaterialTheme.colorScheme.tertiaryContainer,
                    contentColor = MaterialTheme.colorScheme.onTertiaryContainer
                )
            }
            Text(
                text = "Sign in and link your home to load its latest readings.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            if (onOpenHousehold != null) {
                Button(onClick = onOpenHousehold) {
                    Text("View my home")
                }
            }
        }
    }
}

@Composable
private fun LearningPathCard(
    title: String,
    completedLessons: Int,
    totalLessons: Int,
    onClick: (() -> Unit)? = null
) {
    val progress = if (totalLessons == 0) 0f else completedLessons.toFloat() / totalLessons
    val cardModifier = Modifier.fillMaxWidth()

    val contents: @Composable () -> Unit = {
        androidx.compose.foundation.layout.Column(
            modifier = Modifier.padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                androidx.compose.foundation.layout.Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = title,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = "Everyday electricity",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                Text(
                    text = "$completedLessons of $totalLessons",
                    style = MaterialTheme.typography.labelLarge,
                    color = MaterialTheme.colorScheme.primary
                )
            }
            LinearProgressIndicator(
                progress = { progress },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(8.dp),
                color = MaterialTheme.colorScheme.primary,
                trackColor = MaterialTheme.colorScheme.surfaceVariant
            )
            if (onClick != null) {
                Text(
                    text = "View learning path",
                    style = MaterialTheme.typography.labelLarge,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.primary
                )
            }
        }
    }

    if (onClick == null) {
        Card(
            modifier = cardModifier,
            shape = androidx.compose.foundation.shape.RoundedCornerShape(22.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
        ) { contents() }
    } else {
        Card(
            onClick = onClick,
            modifier = cardModifier,
            shape = androidx.compose.foundation.shape.RoundedCornerShape(22.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
        ) { contents() }
    }
}

@Composable
private fun EnergyLessonCard(lesson: Lesson) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = androidx.compose.foundation.shape.RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        androidx.compose.foundation.layout.Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = lesson.title,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                    modifier = Modifier.weight(1f)
                )
                Text(
                    text = "+${lesson.points} XP",
                    style = MaterialTheme.typography.labelLarge,
                    color = MaterialTheme.colorScheme.primary
                )
            }
            Text(
                text = lesson.description,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Text(
                text = "${lesson.estimatedMinutes} min lesson",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

private fun screenPadding(insetPadding: PaddingValues) = PaddingValues(
    start = 20.dp,
    top = insetPadding.calculateTopPadding() + 16.dp,
    end = 20.dp,
    bottom = insetPadding.calculateBottomPadding() + 24.dp
)
