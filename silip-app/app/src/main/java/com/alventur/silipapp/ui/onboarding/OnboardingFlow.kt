@file:OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class, ExperimentalFoundationApi::class)

package com.alventur.silipapp.ui.onboarding

import android.Manifest
import android.os.Build
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.ContentTransform
import androidx.compose.animation.EnterTransition
import androidx.compose.animation.ExitTransition
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.ArrowBack
import androidx.compose.material.icons.outlined.Check
import androidx.compose.material.icons.outlined.LocationOn
import androidx.compose.material.icons.outlined.NotificationsActive
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
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
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.alventur.silipapp.data.local.BillRange
import com.alventur.silipapp.data.local.HouseholdProfile
import com.alventur.silipapp.data.local.HouseholdSize
import com.alventur.silipapp.data.local.ProgressStore
import com.alventur.silipapp.notifications.AwayMonitor
import com.alventur.silipapp.ui.AliPose
import com.alventur.silipapp.ui.PreviewBadge
import com.alventur.silipapp.ui.design.AliGlow
import com.alventur.silipapp.ui.design.AnimatedAli
import com.alventur.silipapp.ui.design.AnimatedNumber
import com.alventur.silipapp.ui.design.AnimatedPesos
import com.alventur.silipapp.ui.design.ConfettiBurst
import com.alventur.silipapp.ui.design.SilipMotion
import com.alventur.silipapp.ui.design.StreakFlame
import com.alventur.silipapp.ui.design.orSnap
import com.alventur.silipapp.ui.design.pressScale
import com.alventur.silipapp.ui.design.rememberHaptics
import com.alventur.silipapp.ui.design.rememberReduceMotion
import kotlin.math.absoluteValue
import kotlinx.coroutines.launch

private enum class Step { Splash, Values, Personalize, Connect, Permissions, Celebrate }

/** Steps that show the progress bar, in order. */
private val ProgressSteps = listOf(Step.Values, Step.Personalize, Step.Connect, Step.Permissions)

private const val ONBOARDING_XP = 10

/**
 * First-run flow, about 60 seconds, skippable at every step:
 * splash → three value cards → personalization chips → connect the clamp or explore Rosa's
 * demo home → permission priming → celebration (Day 1 of the Eco-Streak, +10 XP).
 *
 * Everything is saved through [ProgressStore]. "Skip" saves the answers so far, fills the rest
 * with [HouseholdProfile.SkipDefaults], and opens the demo home (first run) or keeps the
 * current home (replay). [onFinished] is called when the user lands on Home; the caller should
 * re-read the device ID and demo-home flag from the store.
 */
@Composable
internal fun OnboardingFlow(
    onFinished: () -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val store = remember(context) { ProgressStore.get(context) }
    val initial = remember { store.progress.value }
    val returning = initial.profile != HouseholdProfile()
    val reduceMotion = rememberReduceMotion()

    var step by rememberSaveable { mutableStateOf(Step.Splash) }
    var size by rememberSaveable { mutableStateOf(initial.profile.householdSize) }
    var aircons by rememberSaveable { mutableStateOf(initial.profile.aircons) }
    var bill by rememberSaveable { mutableStateOf(initial.profile.lastBill) }
    var deviceInput by rememberSaveable { mutableStateOf("") }
    var useDemoHome by rememberSaveable { mutableStateOf(if (returning) initial.usingDemoHome else true) }

    fun profile() = HouseholdProfile(size, aircons, bill)

    fun skip() {
        val defaults = HouseholdProfile.SkipDefaults
        store.completeOnboarding(
            profile = HouseholdProfile(
                householdSize = size ?: defaults.householdSize,
                aircons = aircons ?: defaults.aircons,
                lastBill = bill ?: defaults.lastBill
            ),
            useDemoHome = if (returning) initial.usingDemoHome else true
        )
        onFinished()
    }

    fun go(next: Step) {
        step = next
    }

    BackHandler(enabled = step != Step.Splash && step != Step.Celebrate) {
        step = Step.entries[(step.ordinal - 1).coerceAtLeast(0)]
    }

    Box(
        modifier = modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .safeDrawingPadding()
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .widthIn(max = 560.dp)
                .align(Alignment.TopCenter)
        ) {
            TopRow(
                step = step,
                onBack = { step = Step.entries[(step.ordinal - 1).coerceAtLeast(0)] },
                onSkip = ::skip
            )
            AnimatedContent(
                targetState = step,
                transitionSpec = { stepTransition(initialState, targetState, reduceMotion) },
                label = "onboarding-step",
                modifier = Modifier.weight(1f)
            ) { current ->
                when (current) {
                    Step.Splash -> SplashStep(onStart = { go(Step.Values) })
                    Step.Values -> ValuesStep(onContinue = { go(Step.Personalize) })
                    Step.Personalize -> PersonalizeStep(
                        size = size,
                        onSize = { size = it },
                        aircons = aircons,
                        onAircons = { aircons = it },
                        bill = bill,
                        onBill = { bill = it },
                        onContinue = { go(Step.Connect) }
                    )
                    Step.Connect -> ConnectStep(
                        deviceInput = deviceInput,
                        onDeviceInput = { deviceInput = it },
                        onConnect = {
                            useDemoHome = false
                            go(Step.Permissions)
                        },
                        onExploreDemo = {
                            deviceInput = ""
                            useDemoHome = true
                            go(Step.Permissions)
                        }
                    )
                    Step.Permissions -> PermissionsStep(onContinue = {
                        store.completeOnboarding(profile(), useDemoHome, deviceInput.takeIf { !useDemoHome })
                        go(Step.Celebrate)
                    })
                    Step.Celebrate -> CelebrateStep(store = store, onDone = onFinished)
                }
            }
        }
    }
}

private fun stepTransition(from: Step, to: Step, reduceMotion: Boolean): ContentTransform {
    if (reduceMotion) return EnterTransition.None togetherWith ExitTransition.None
    val forward = to.ordinal > from.ordinal
    val enter = slideInHorizontally(SilipMotion.enter<IntOffset>()) { w -> if (forward) w / 4 else -w / 4 } +
        fadeIn(SilipMotion.standard())
    val exit = slideOutHorizontally(SilipMotion.short<IntOffset>()) { w -> if (forward) -w / 4 else w / 4 } +
        fadeOut(SilipMotion.short())
    return enter togetherWith exit
}

@Composable
private fun TopRow(step: Step, onBack: () -> Unit, onSkip: () -> Unit) {
    val reduceMotion = rememberReduceMotion()
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 56.dp)
            .padding(horizontal = 8.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(Modifier.size(48.dp)) {
            if (step in ProgressSteps && step != Step.Values) {
                IconButton(onClick = onBack) {
                    Icon(Icons.AutoMirrored.Outlined.ArrowBack, contentDescription = "Back")
                }
            }
        }
        Box(Modifier.weight(1f).padding(horizontal = 8.dp), contentAlignment = Alignment.Center) {
            val index = ProgressSteps.indexOf(step)
            if (index >= 0) {
                val fraction by animateFloatAsState(
                    targetValue = (index + 1f) / ProgressSteps.size,
                    animationSpec = SilipMotion.gentle<Float>().orSnap(reduceMotion),
                    label = "onboarding-progress"
                )
                LinearProgressIndicator(
                    progress = { fraction },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(8.dp)
                        .semantics { contentDescription = "Step ${index + 1} of ${ProgressSteps.size}" },
                    color = MaterialTheme.colorScheme.primary,
                    trackColor = MaterialTheme.colorScheme.primaryContainer,
                    strokeCap = androidx.compose.ui.graphics.StrokeCap.Round
                )
            }
        }
        Box(Modifier.widthIn(min = 64.dp), contentAlignment = Alignment.CenterEnd) {
            if (step != Step.Celebrate) {
                TextButton(onClick = onSkip, modifier = Modifier.heightIn(min = 48.dp)) { Text("Skip") }
            }
        }
    }
}

/** Scrollable content with actions pinned at the bottom. */
@Composable
private fun StepLayout(
    actions: @Composable ColumnScope.() -> Unit,
    content: @Composable ColumnScope.() -> Unit
) {
    Column(Modifier.fillMaxSize()) {
        Column(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 24.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
            content = content
        )
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 24.dp, vertical = 16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
            content = actions
        )
    }
}

@Composable
private fun StepTitle(text: String, modifier: Modifier = Modifier, center: Boolean = false) {
    Text(
        text = text,
        style = MaterialTheme.typography.headlineMedium,
        color = MaterialTheme.colorScheme.onBackground,
        textAlign = if (center) TextAlign.Center else TextAlign.Start,
        modifier = modifier.semantics { heading() }
    )
}

// region Splash

@Composable
private fun SplashStep(onStart: () -> Unit) {
    StepLayout(
        actions = {
            Button(
                onClick = onStart,
                modifier = Modifier.fillMaxWidth().heightIn(min = 56.dp).pressScale()
            ) { Text("Get started") }
        }
    ) {
        Spacer(Modifier.height(24.dp))
        AnimatedAli(
            pose = AliPose.Welcome,
            size = 220.dp,
            flyIn = true,
            modifier = Modifier.align(Alignment.CenterHorizontally)
        )
        Text(
            text = "silip",
            style = MaterialTheme.typography.displaySmall.copy(fontSize = 44.sp, letterSpacing = (-1).sp),
            color = MaterialTheme.colorScheme.primary,
            modifier = Modifier.align(Alignment.CenterHorizontally)
        )
        StepTitle("Hi, I'm Ali.", Modifier.align(Alignment.CenterHorizontally), center = true)
        Text(
            text = "I turn your home's electricity into pesos you can follow, hour by hour.",
            style = MaterialTheme.typography.bodyLarge,
            textAlign = TextAlign.Center,
            color = MaterialTheme.colorScheme.onBackground,
            modifier = Modifier.fillMaxWidth()
        )
    }
}

// endregion

// region Value cards

private class ValueCard(
    val pose: AliPose,
    val glow: AliGlow,
    val title: String,
    val body: String,
    val badge: String? = null
)

private val ValueCards = listOf(
    ValueCard(
        AliPose.HouseholdCheck, AliGlow.Green,
        "Know your bill in pesos",
        "See what your home costs per hour while it runs. Turn on the aircon and watch the peso rate change. Figures are estimates from your rate."
    ),
    ValueCard(
        AliPose.Caution, AliGlow.Orange,
        "A guardian for your home",
        "If a steady load stays on while you're away, Ali asks you to check. The clamp sees whole-home power, so Ali asks instead of guessing."
    ),
    ValueCard(
        AliPose.Success, AliGlow.Green,
        "Earn by helping the grid",
        "When your street's transformer runs hot, neighbors can ease the load together for one hour. Rewards are not live yet.",
        badge = "Pilot preview"
    )
)

@Composable
private fun ValuesStep(onContinue: () -> Unit) {
    val pagerState = rememberPagerState(pageCount = { ValueCards.size })
    val scope = rememberCoroutineScope()
    val reduceMotion = rememberReduceMotion()
    val last = pagerState.currentPage == ValueCards.lastIndex

    Column(Modifier.fillMaxSize()) {
        HorizontalPager(
            state = pagerState,
            modifier = Modifier.weight(1f).fillMaxWidth()
        ) { page ->
            val card = ValueCards[page]
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .verticalScroll(rememberScrollState())
                    .padding(horizontal = 24.dp, vertical = 8.dp)
                    .graphicsLayer {
                        val offset = ((pagerState.currentPage - page) + pagerState.currentPageOffsetFraction)
                            .absoluteValue.coerceIn(0f, 1f)
                        alpha = 1f - 0.5f * offset
                        val scale = 1f - 0.08f * offset
                        scaleX = scale
                        scaleY = scale
                    },
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                AnimatedAli(
                    pose = card.pose,
                    glow = card.glow,
                    size = 200.dp,
                    animate = page == pagerState.currentPage,
                    modifier = Modifier.align(Alignment.CenterHorizontally)
                )
                if (card.badge != null) PreviewBadge(label = card.badge)
                StepTitle(card.title)
                Text(card.body, style = MaterialTheme.typography.bodyLarge, color = MaterialTheme.colorScheme.onBackground)
            }
        }
        PageIndicator(
            count = ValueCards.size,
            current = pagerState.currentPage,
            modifier = Modifier.align(Alignment.CenterHorizontally).padding(vertical = 8.dp)
        )
        Column(Modifier.fillMaxWidth().padding(horizontal = 24.dp, vertical = 16.dp)) {
            Button(
                onClick = {
                    if (last) onContinue()
                    else scope.launch {
                        val target = pagerState.currentPage + 1
                        if (reduceMotion) pagerState.scrollToPage(target)
                        else pagerState.animateScrollToPage(target, animationSpec = SilipMotion.snappy())
                    }
                },
                modifier = Modifier.fillMaxWidth().heightIn(min = 56.dp).pressScale()
            ) { Text(if (last) "Continue" else "Next") }
        }
    }
}

/** Dots where the active one stretches into a pill with a spring. */
@Composable
private fun PageIndicator(count: Int, current: Int, modifier: Modifier = Modifier) {
    val reduceMotion = rememberReduceMotion()
    Row(
        modifier = modifier.clearAndSetSemantics { contentDescription = "Card ${current + 1} of $count" },
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        repeat(count) { index ->
            val selected = index == current
            val width by animateDpAsState(
                targetValue = if (selected) 28.dp else 8.dp,
                animationSpec = SilipMotion.playful<androidx.compose.ui.unit.Dp>().orSnap(reduceMotion),
                label = "dot-width"
            )
            val color by animateColorAsState(
                targetValue = if (selected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outline.copy(alpha = 0.45f),
                animationSpec = SilipMotion.standard<androidx.compose.ui.graphics.Color>().orSnap(reduceMotion),
                label = "dot-color"
            )
            Box(
                Modifier
                    .height(8.dp)
                    .width(width)
                    .background(color, CircleShape)
            )
        }
    }
}

// endregion

// region Personalize

private fun sizeReaction(size: HouseholdSize) = when (size) {
    HouseholdSize.OneToTwo -> "A small home. Easy to keep an eye on."
    HouseholdSize.ThreeToFour -> "A busy house! Let's keep it comfy and cheaper."
    HouseholdSize.FivePlus -> "Big family. Every kWh counts here."
}

private fun airconReaction(count: Int) = when (count) {
    0 -> "No aircon. Fans and good airflow, nice."
    1 -> "One aircon. I'll show you what it costs while it runs."
    2 -> "Two aircons. Cooling is often the biggest part of a bill."
    else -> "Three or more. Small changes in cooling add up fast."
}

private fun airconLabel(count: Int) = when (count) {
    0 -> "None"
    3 -> "3+"
    else -> count.toString()
}

@Composable
private fun PersonalizeStep(
    size: HouseholdSize?,
    onSize: (HouseholdSize) -> Unit,
    aircons: Int?,
    onAircons: (Int) -> Unit,
    bill: BillRange?,
    onBill: (BillRange) -> Unit,
    onContinue: () -> Unit
) {
    val haptics = rememberHaptics()
    var reaction by rememberSaveable { mutableStateOf("Three quick taps and I'll know your home.") }
    var reactionCount by remember { mutableIntStateOf(0) }
    val budget = HouseholdProfile(lastBill = bill).monthlyBudgetPhp

    StepLayout(
        actions = {
            Button(
                onClick = onContinue,
                modifier = Modifier.fillMaxWidth().heightIn(min = 56.dp).pressScale()
            ) { Text("Continue") }
        }
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            AnimatedAli(
                pose = if (reactionCount == 0) AliPose.Practice else AliPose.Success,
                size = 88.dp
            )
            Surface(
                shape = RoundedCornerShape(topStart = 4.dp, topEnd = 20.dp, bottomEnd = 20.dp, bottomStart = 20.dp),
                color = MaterialTheme.colorScheme.primaryContainer,
                modifier = Modifier.weight(1f)
            ) {
                AnimatedContent(
                    targetState = reaction,
                    transitionSpec = { fadeIn(SilipMotion.standard()) togetherWith fadeOut(SilipMotion.short()) },
                    label = "ali-reaction"
                ) { line ->
                    Text(
                        text = line,
                        style = MaterialTheme.typography.bodyLarge,
                        color = MaterialTheme.colorScheme.onPrimaryContainer,
                        modifier = Modifier
                            .padding(horizontal = 14.dp, vertical = 12.dp)
                            .semantics { liveRegion = LiveRegionMode.Polite }
                    )
                }
            }
        }
        StepTitle("Tell Ali about your home")

        ChipQuestion("How many people live with you?") {
            HouseholdSize.entries.forEach { option ->
                AnswerChip(option.label, selected = size == option) {
                    onSize(option); reaction = sizeReaction(option); reactionCount++; haptics.select()
                }
            }
        }
        ChipQuestion("How many aircons do you have?") {
            (0..3).forEach { option ->
                AnswerChip(airconLabel(option), selected = aircons == option) {
                    onAircons(option); reaction = airconReaction(option); reactionCount++; haptics.select()
                }
            }
        }
        ChipQuestion("About how much was your last Meralco bill?") {
            BillRange.entries.forEach { option ->
                AnswerChip(option.label, selected = bill == option) {
                    onBill(option)
                    val goal = HouseholdProfile(lastBill = option).monthlyBudgetPhp ?: 0
                    reaction = "Got it. Let's aim for about ₱%,d a month.".format(goal)
                    reactionCount++
                    haptics.select()
                }
            }
        }
        AnimatedVisibility(visible = budget != null, enter = fadeIn() + expandVertically()) {
            Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Row(verticalAlignment = Alignment.Bottom, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Monthly budget goal", style = MaterialTheme.typography.titleMedium)
                    AnimatedPesos(
                        amount = (budget ?: 0).toDouble(),
                        decimals = 0,
                        style = MaterialTheme.typography.titleLarge,
                        color = MaterialTheme.colorScheme.primary
                    )
                }
                Text(
                    "10% below your last bill. A goal you set, not a forecast.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

@Composable
private fun ChipQuestion(question: String, chips: @Composable () -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(question, style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.onBackground)
        FlowRow(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalArrangement = Arrangement.spacedBy(4.dp)
        ) { chips() }
    }
}

@Composable
private fun AnswerChip(label: String, selected: Boolean, onClick: () -> Unit) {
    FilterChip(
        selected = selected,
        onClick = onClick,
        label = { Text(label, style = MaterialTheme.typography.bodyLarge) },
        leadingIcon = if (selected) {
            { Icon(Icons.Outlined.Check, contentDescription = null, modifier = Modifier.size(18.dp)) }
        } else {
            null
        },
        shape = RoundedCornerShape(50),
        colors = FilterChipDefaults.filterChipColors(
            selectedContainerColor = MaterialTheme.colorScheme.primary,
            selectedLabelColor = MaterialTheme.colorScheme.onPrimary,
            selectedLeadingIconColor = MaterialTheme.colorScheme.onPrimary
        ),
        modifier = Modifier.heightIn(min = 48.dp).pressScale()
    )
}

// endregion

// region Connect

@Composable
private fun ConnectStep(
    deviceInput: String,
    onDeviceInput: (String) -> Unit,
    onConnect: () -> Unit,
    onExploreDemo: () -> Unit
) {
    val hasId = deviceInput.isNotBlank()
    StepLayout(
        actions = {
            if (hasId) {
                Button(onClick = onConnect, modifier = Modifier.fillMaxWidth().heightIn(min = 56.dp).pressScale()) {
                    Text("Connect this clamp")
                }
                OutlinedButton(onClick = onExploreDemo, modifier = Modifier.fillMaxWidth().heightIn(min = 56.dp).pressScale()) {
                    Text("Explore the demo home (Rosa's)")
                }
            } else {
                Button(onClick = onExploreDemo, modifier = Modifier.fillMaxWidth().heightIn(min = 56.dp).pressScale()) {
                    Text("Explore the demo home (Rosa's)")
                }
                Text(
                    "Rosa's home uses simulated readings so you can try everything first.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.fillMaxWidth()
                )
            }
        }
    ) {
        StepTitle("Connect your SILIP clamp")
        Text(
            "Have a clamp? Enter its device ID. No clamp yet? Explore Rosa's demo home.",
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onBackground
        )
        OutlinedTextField(
            value = deviceInput,
            onValueChange = onDeviceInput,
            label = { Text("Device ID") },
            supportingText = { Text("Use the ID assigned to your sensor in the SILIP dashboard. You can paste it.") },
            singleLine = true,
            keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done),
            modifier = Modifier.fillMaxWidth()
        )
        InstallCard()
    }
}

/** How the clamp is installed: meter → main wire with the clamp → your panel. */
@Composable
private fun InstallCard() {
    val scheme = MaterialTheme.colorScheme
    Card(
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = scheme.surface),
        border = CardDefaults.outlinedCardBorder(),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("How the clamp is installed", style = MaterialTheme.typography.titleMedium)
            Box(
                Modifier
                    .fillMaxWidth()
                    .height(72.dp)
                    .clearAndSetSemantics {
                        contentDescription = "Diagram: Meralco meter, then the main wire with the SILIP clamp around it, then your panel."
                    }
            ) {
                val outline = scheme.outline
                val primary = scheme.primary
                val wire = scheme.onSurfaceVariant
                Canvas(Modifier.matchParentSize()) {
                    val boxW = size.width * 0.22f
                    val boxH = size.height * 0.8f
                    val top = (size.height - boxH) / 2f
                    val midY = size.height / 2f
                    val stroke = 2.dp.toPx()
                    // Meter (left) and panel (right).
                    drawRoundRect(outline, Offset(0f, top), Size(boxW, boxH), CornerRadius(12.dp.toPx()), style = Stroke(stroke))
                    drawCircle(outline, radius = boxH * 0.22f, center = Offset(boxW / 2f, midY), style = Stroke(stroke))
                    val panelX = size.width - boxW
                    drawRoundRect(primary, Offset(panelX, top), Size(boxW, boxH), CornerRadius(12.dp.toPx()), style = Stroke(stroke))
                    // Main wire.
                    drawLine(wire, Offset(boxW, midY), Offset(panelX, midY), strokeWidth = 3.dp.toPx())
                    // Clamp ring on the wire, close to the panel (after the meter).
                    val clampX = panelX - (panelX - boxW) * 0.3f
                    drawCircle(primary, radius = 12.dp.toPx(), center = Offset(clampX, midY), style = Stroke(5.dp.toPx()))
                }
            }
            Row(Modifier.fillMaxWidth()) {
                Text("Meralco meter", style = MaterialTheme.typography.labelMedium, modifier = Modifier.weight(1f))
                Text("SILIP clamp", style = MaterialTheme.typography.labelMedium, color = scheme.primary,
                    textAlign = TextAlign.Center, modifier = Modifier.weight(1f))
                Text("Your panel", style = MaterialTheme.typography.labelMedium, textAlign = TextAlign.End,
                    modifier = Modifier.weight(1f))
            }
            Text(
                "A licensed electrician clips the clamp around your main wire after the meter, inside your panel. " +
                    "It never touches Meralco's meter, seal or service drop.",
                style = MaterialTheme.typography.bodyMedium,
                color = scheme.onSurfaceVariant
            )
        }
    }
}

// endregion

// region Permissions

@Composable
private fun PermissionsStep(onContinue: () -> Unit) {
    val context = LocalContext.current
    val haptics = rememberHaptics()
    var revision by remember { mutableIntStateOf(0) }
    val notificationsOn = remember(revision) { AwayMonitor.notificationsAllowed(context) }
    val locationOn = remember(revision) {
        context.checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) ==
            android.content.pm.PackageManager.PERMISSION_GRANTED
    }
    // Same permission paths as the away-mode card on Home; background location is asked there.
    val notificationLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        revision++
        if (granted) haptics.confirm()
    }
    val locationLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { grants ->
        revision++
        if (grants.values.any { it }) haptics.confirm()
    }

    StepLayout(
        actions = {
            Button(onClick = onContinue, modifier = Modifier.fillMaxWidth().heightIn(min = 56.dp).pressScale()) {
                Text("Continue")
            }
            Text(
                "Both are optional. You can change them anytime in Android settings.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center,
                modifier = Modifier.fillMaxWidth()
            )
        }
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            AnimatedAli(pose = AliPose.Welcome, size = 88.dp)
            StepTitle("Let Ali reach you", Modifier.weight(1f))
        }
        PermissionCard(
            icon = { Icon(Icons.Outlined.NotificationsActive, contentDescription = null) },
            title = "Notifications",
            body = "Ali tells you if a steady load stays on while you're away, or when your street's transformer needs help.",
            granted = notificationsOn,
            grantedText = "Notifications are on",
            actionText = "Allow notifications",
            onAction = {
                if (Build.VERSION.SDK_INT >= 33) notificationLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
                else revision++
            }
        )
        PermissionCard(
            icon = { Icon(Icons.Outlined.LocationOn, contentDescription = null) },
            title = "Away mode (optional)",
            body = "To notice when you leave home, Ali needs your location. It stays on this phone. You finish away-mode setup on Home.",
            granted = locationOn,
            grantedText = "Location allowed",
            actionText = "Allow location",
            onAction = {
                locationLauncher.launch(
                    arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION)
                )
            }
        )
    }
}

@Composable
private fun PermissionCard(
    icon: @Composable () -> Unit,
    title: String,
    body: String,
    granted: Boolean,
    grantedText: String,
    actionText: String,
    onAction: () -> Unit
) {
    Card(
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = CardDefaults.outlinedCardBorder(),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                icon()
                Text(title, style = MaterialTheme.typography.titleMedium)
            }
            Text(body, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            if (granted) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Icon(Icons.Outlined.Check, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                    Text(grantedText, style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.primary)
                }
            } else {
                OutlinedButton(onClick = onAction, modifier = Modifier.heightIn(min = 48.dp).pressScale()) {
                    Text(actionText)
                }
            }
        }
    }
}

// endregion

// region Celebrate

@Composable
private fun CelebrateStep(store: ProgressStore, onDone: () -> Unit) {
    val haptics = rememberHaptics()
    val progress by store.progress.collectAsState()
    var awardedXp by rememberSaveable { mutableIntStateOf(-1) }
    var burst by remember { mutableStateOf<Int?>(null) }

    LaunchedEffect(Unit) {
        if (awardedXp < 0) {
            // XP for finishing onboarding is given once per install, not on replays.
            awardedXp = if (store.earnBadge(ProgressStore.BADGE_FIRST_DAY)) {
                store.addXp(ONBOARDING_XP); ONBOARDING_XP
            } else 0
            store.recordActivity()
        }
        burst = 1
        haptics.confirm()
    }
    val days = progress.streak.displayCount(com.alventur.silipapp.data.local.manilaToday()).coerceAtLeast(1)

    Box(Modifier.fillMaxSize()) {
        StepLayout(
            actions = {
                Button(onClick = onDone, modifier = Modifier.fillMaxWidth().heightIn(min = 56.dp).pressScale()) {
                    Text("Go to Home")
                }
            }
        ) {
            Spacer(Modifier.height(16.dp))
            AnimatedAli(pose = AliPose.Success, size = 180.dp, modifier = Modifier.align(Alignment.CenterHorizontally))
            StreakFlame(
                days = days,
                size = 56.dp,
                countStyle = MaterialTheme.typography.headlineMedium,
                celebrateKey = burst,
                modifier = Modifier.align(Alignment.CenterHorizontally)
            )
            StepTitle(
                "Day $days of your Eco-Streak",
                Modifier.align(Alignment.CenterHorizontally),
                center = true
            )
            if (awardedXp > 0) {
                AnimatedNumber(
                    value = awardedXp.toDouble(),
                    countFrom = 0.0,
                    format = { "+${it.toInt()} XP" },
                    style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold),
                    color = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.align(Alignment.CenterHorizontally)
                )
            }
            Text(
                "Come back tomorrow for a 15-second quiz to keep your streak going.",
                style = MaterialTheme.typography.bodyLarge,
                textAlign = TextAlign.Center,
                color = MaterialTheme.colorScheme.onBackground,
                modifier = Modifier.fillMaxWidth()
            )
        }
        ConfettiBurst(trigger = burst, modifier = Modifier.matchParentSize())
    }
}

// endregion
