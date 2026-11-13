package com.alventur.silipapp.ui.learn

import androidx.compose.animation.core.tween
import androidx.compose.foundation.Image
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
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Lock
import androidx.compose.material.icons.rounded.ArrowDownward
import androidx.compose.material.icons.rounded.ArrowUpward
import androidx.compose.material.icons.rounded.CheckCircle
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.graphics.ColorMatrix
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import com.alventur.silipapp.R
import com.alventur.silipapp.data.demo.DemoHousehold
import com.alventur.silipapp.data.demo.DemoLabels
import com.alventur.silipapp.data.demo.LeaderboardEntry
import com.alventur.silipapp.data.local.ProgressStore
import com.alventur.silipapp.data.local.manilaToday
import com.alventur.silipapp.ui.AdaptivePage
import com.alventur.silipapp.ui.PreviewBadge
import com.alventur.silipapp.ui.design.SilipMotion
import com.alventur.silipapp.ui.design.formatNumber
import com.alventur.silipapp.ui.design.pressScale
import com.alventur.silipapp.ui.design.rememberHaptics
import com.alventur.silipapp.ui.design.rememberReduceMotion
import kotlinx.coroutines.delay

private enum class BoardTab(val label: String) { Xp("Weekly XP"), Kwh("kWh saved") }

/** A row as shown on one tab: position on that tab plus the value text. */
private data class BoardRow(val entry: LeaderboardEntry, val rank: Int, val value: String, val spokenValue: String)

/** One badge on the shelf. [art] is a drawable in res/drawable-nodpi. */
private data class BadgeInfo(val id: String, val name: String, val howToEarn: String, val art: Int)

private val Badges = listOf(
    BadgeInfo(ProgressStore.BADGE_FIRST_DAY, "First day", "Finish the intro.", R.drawable.silip_energy_token),
    BadgeInfo(ProgressStore.BADGE_FIRST_QUIZ, "First quiz", "Answer one daily quiz.", R.drawable.silip_energy_token),
    BadgeInfo(ProgressStore.BADGE_WEEK_STREAK, "7-day streak", "Keep your Eco-Streak for 7 days.", R.drawable.silip_reward_chest),
    BadgeInfo(ProgressStore.BADGE_ALERT_CHECKED, "Home checker", "Respond to a safety alert.", R.drawable.silip_reward_chest),
    BadgeInfo(ProgressStore.BADGE_GRID_HELPER, "Grid helper", "Finish a grid event (pilot preview).", R.drawable.silip_trophy)
)

/**
 * Neighborhood leaderboard. The neighbors are demo data, so "Demo neighborhood" stays pinned on
 * screen. "You" uses this phone's weekly XP (resets Monday, Manila) and the estimated kWh saved in
 * finished grid events this week. On entry the XP list starts in last week's order and settles into
 * this week's, so a climb is visible.
 */
@Composable
internal fun LeaderboardScreen(
    contentPadding: PaddingValues,
    onBack: () -> Unit
) {
    val context = LocalContext.current
    val store = remember(context) { ProgressStore.get(context) }
    val progress by store.progress.collectAsState()
    val haptics = rememberHaptics()
    val reduceMotion = rememberReduceMotion()
    val today = manilaToday()
    val weeklyXp = progress.weeklyXp(today)
    val weeklyKwh = progress.weeklyKwhSaved(today)
    val entries = remember(weeklyXp, weeklyKwh) { DemoHousehold.leaderboard(weeklyXp, weeklyKwh) }

    var tabName by rememberSaveable { mutableStateOf(BoardTab.Xp.name) }
    val tab = BoardTab.valueOf(tabName)
    // false = last week's order, true = this week's. Flips once after entry.
    var settled by rememberSaveable { mutableStateOf(false) }
    LaunchedEffect(reduceMotion) {
        if (settled) return@LaunchedEffect
        if (!reduceMotion) delay(650)
        settled = true
    }

    val rows: List<BoardRow> = when (tab) {
        BoardTab.Xp -> {
            val ordered = if (settled) entries.sortedBy { it.rank } else entries.sortedBy { it.previousRank ?: it.rank }
            ordered.map { e ->
                val rank = if (settled) e.rank else (e.previousRank ?: e.rank)
                BoardRow(e, rank, "${e.weeklyXp} XP", "${e.weeklyXp} XP")
            }
        }
        BoardTab.Kwh -> entries
            .sortedWith(compareByDescending<LeaderboardEntry> { it.kwhSaved }.thenBy { if (it.isYou) 0 else 1 })
            .mapIndexed { i, e ->
                BoardRow(e, i + 1, "${formatNumber(e.kwhSaved, 1)} kWh", "${formatNumber(e.kwhSaved, 1)} kilowatt hours saved")
            }
    }
    val podium = when (tab) {
        BoardTab.Xp -> entries.sortedBy { it.rank }.take(3).mapIndexed { i, e -> BoardRow(e, i + 1, "${e.weeklyXp} XP", "${e.weeklyXp} XP") }
        BoardTab.Kwh -> rows.take(3)
    }
    val you = entries.firstOrNull { it.isYou }

    Box(Modifier.fillMaxSize()) {
        AdaptivePage(contentPadding) {
            item {
                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(
                        "Neighborhood",
                        style = MaterialTheme.typography.headlineSmall,
                        modifier = Modifier.semantics { heading() }
                    )
                    Text(
                        "This week's ranks. They reset every Monday.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
            item {
                BoardTabs(
                    selected = tab,
                    onSelect = {
                        if (it != tab) haptics.select()
                        tabName = it.name
                    }
                )
            }
            item { Podium(podium) }
            if (you != null && tab == BoardTab.Xp) {
                item { YouSummary(you = you, weeklyXp = weeklyXp) }
            }
            if (tab == BoardTab.Kwh) {
                item {
                    Text(
                        "kWh saved is an estimate from grid events you finished this week. Neighbors' numbers are demo data.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
            items(rows, key = { "${tab.name}-${it.entry.name}" }) { row ->
                BoardRowCard(
                    row = row,
                    showChange = tab == BoardTab.Xp && settled,
                    modifier = Modifier.animateItem(
                        placementSpec = if (reduceMotion) null else tween<IntOffset>(700, easing = SilipMotion.StandardEasing)
                    )
                )
            }
            item { BadgeShelf(earned = progress.badges) }
            item {
                OutlinedButton(
                    onClick = onBack,
                    modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp).pressScale()
                ) { Text("Back to Learn") }
            }
            // Room for the pinned label.
            item { Spacer(Modifier.height(40.dp)) }
        }
        PinnedDemoLabel(
            label = DemoLabels.NEIGHBORHOOD,
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .padding(bottom = contentPadding.calculateBottomPadding() + 12.dp)
        )
    }
}

/** The demo label that never scrolls away. */
@Composable
internal fun PinnedDemoLabel(label: String, modifier: Modifier = Modifier) {
    Surface(
        shape = RoundedCornerShape(50),
        color = MaterialTheme.colorScheme.inverseSurface,
        shadowElevation = 4.dp,
        modifier = modifier
    ) {
        Text(
            label,
            style = MaterialTheme.typography.labelLarge,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.inverseOnSurface,
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp)
        )
    }
}

@Composable
private fun BoardTabs(selected: BoardTab, onSelect: (BoardTab) -> Unit) {
    val scheme = MaterialTheme.colorScheme
    Surface(shape = RoundedCornerShape(50), color = scheme.surfaceVariant, modifier = Modifier.fillMaxWidth()) {
        Row(Modifier.padding(4.dp)) {
            BoardTab.entries.forEach { tab ->
                val isSelected = tab == selected
                Surface(
                    shape = RoundedCornerShape(50),
                    color = if (isSelected) scheme.primary else scheme.surfaceVariant,
                    modifier = Modifier
                        .weight(1f)
                        .heightIn(min = 48.dp)
                        .clip(RoundedCornerShape(50))
                        .selectable(selected = isSelected, role = Role.Tab, onClick = { onSelect(tab) })
                ) {
                    Box(contentAlignment = Alignment.Center, modifier = Modifier.padding(vertical = 12.dp)) {
                        Text(
                            tab.label,
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
                            color = if (isSelected) scheme.onPrimary else scheme.onSurfaceVariant
                        )
                    }
                }
            }
        }
    }
}

/** Top three: 2nd, 1st, 3rd, with the trophy art sized by place. */
@Composable
private fun Podium(top: List<BoardRow>) {
    if (top.isEmpty()) return
    val order = listOfNotNull(top.getOrNull(1), top.getOrNull(0), top.getOrNull(2))
    Card(
        shape = RoundedCornerShape(28.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 16.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.Bottom
        ) {
            order.forEach { row ->
                val (trophy, block) = when (row.rank) {
                    1 -> 64.dp to 84.dp
                    2 -> 48.dp to 60.dp
                    else -> 42.dp to 44.dp
                }
                PodiumPlace(row, trophy, block, Modifier.weight(1f))
            }
        }
    }
}

@Composable
private fun PodiumPlace(row: BoardRow, trophy: Dp, block: Dp, modifier: Modifier) {
    val scheme = MaterialTheme.colorScheme
    val isYou = row.entry.isYou
    Column(
        modifier = modifier.clearAndSetSemantics {
            contentDescription = "Place ${row.rank}, ${if (isYou) "you" else row.entry.name}, ${row.spokenValue}"
        },
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(6.dp)
    ) {
        Image(
            painter = painterResource(R.drawable.silip_trophy),
            contentDescription = null,
            contentScale = ContentScale.Fit,
            modifier = Modifier.size(trophy)
        )
        Text(
            if (isYou) "You" else row.entry.name,
            style = MaterialTheme.typography.titleSmall,
            fontWeight = FontWeight.Bold,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            textAlign = TextAlign.Center
        )
        Text(
            row.value,
            style = MaterialTheme.typography.bodySmall.copy(fontFamily = FontFamily.Monospace),
            textAlign = TextAlign.Center
        )
        Surface(
            shape = RoundedCornerShape(topStart = 14.dp, topEnd = 14.dp),
            color = if (isYou) scheme.primary else scheme.surface,
            modifier = Modifier.fillMaxWidth().height(block)
        ) {
            Box(contentAlignment = Alignment.Center) {
                Text(
                    row.rank.toString(),
                    style = MaterialTheme.typography.headlineSmall.copy(fontFamily = FontFamily.Monospace),
                    color = if (isYou) scheme.onPrimary else scheme.onSurface
                )
            }
        }
    }
}

@Composable
private fun YouSummary(you: LeaderboardEntry, weeklyXp: Int) {
    val change = you.rankChange
    val line = when {
        weeklyXp == 0 -> "Earn XP this week with a lesson or today's quiz to climb."
        change > 0 -> "You're #${you.rank}, up ${places(change)} from last week."
        change < 0 -> "You're #${you.rank}. A lesson or quiz can move you up."
        else -> "You're #${you.rank} this week."
    }
    Text(line, style = MaterialTheme.typography.titleMedium)
}

private fun places(n: Int) = if (n == 1) "1 place" else "$n places"

@Composable
private fun BoardRowCard(row: BoardRow, showChange: Boolean, modifier: Modifier = Modifier) {
    val scheme = MaterialTheme.colorScheme
    val entry = row.entry
    val change = entry.rankChange
    val changeText = when {
        !showChange || change == 0 -> null
        change > 0 -> "up ${places(change)}"
        else -> "down ${places(-change)}"
    }
    Surface(
        shape = RoundedCornerShape(20.dp),
        color = if (entry.isYou) scheme.primaryContainer else scheme.surface,
        border = if (entry.isYou) androidx.compose.foundation.BorderStroke(2.dp, scheme.primary) else null,
        modifier = modifier
            .fillMaxWidth()
            .clearAndSetSemantics {
                contentDescription = buildString {
                    append("Rank ${row.rank}, ")
                    append(if (entry.isYou) "you" else entry.name)
                    append(", ${row.spokenValue}")
                    if (changeText != null) append(", $changeText from last week")
                }
            }
    ) {
        Row(
            Modifier.padding(horizontal = 16.dp, vertical = 12.dp).heightIn(min = 40.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Text(
                row.rank.toString(),
                style = MaterialTheme.typography.titleMedium.copy(fontFamily = FontFamily.Monospace),
                fontWeight = FontWeight.Bold,
                modifier = Modifier.widthIn(min = 24.dp)
            )
            Surface(
                shape = CircleShape,
                color = if (entry.isYou) scheme.primary else scheme.surfaceVariant,
                modifier = Modifier.size(36.dp)
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Text(
                        entry.name.split(" ").last().take(1),
                        fontWeight = FontWeight.Bold,
                        color = if (entry.isYou) scheme.onPrimary else scheme.onSurfaceVariant
                    )
                }
            }
            Column(Modifier.weight(1f)) {
                Text(
                    entry.name,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = if (entry.isYou) FontWeight.ExtraBold else FontWeight.SemiBold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                if (changeText != null) {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(2.dp)) {
                        Icon(
                            if (change > 0) Icons.Rounded.ArrowUpward else Icons.Rounded.ArrowDownward,
                            contentDescription = null,
                            tint = if (change > 0) scheme.primary else scheme.onSurfaceVariant,
                            modifier = Modifier.size(14.dp)
                        )
                        Text(
                            changeText.replaceFirstChar { it.uppercase() },
                            style = MaterialTheme.typography.bodySmall,
                            color = scheme.onSurfaceVariant
                        )
                    }
                }
            }
            Text(
                row.value,
                style = MaterialTheme.typography.titleMedium.copy(fontFamily = FontFamily.Monospace)
            )
        }
    }
}

@Composable
private fun BadgeShelf(earned: Set<String>) {
    val count = Badges.count { it.id in earned }
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                "Badges",
                style = MaterialTheme.typography.titleLarge,
                modifier = Modifier.weight(1f).semantics { heading() }
            )
            Text(
                "$count of ${Badges.size} earned",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        LazyRow(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            items(Badges, key = { it.id }) { badge -> BadgeCard(badge, badge.id in earned) }
        }
    }
}

@Composable
private fun BadgeCard(badge: BadgeInfo, isEarned: Boolean) {
    val scheme = MaterialTheme.colorScheme
    val grayscale = remember { ColorFilter.colorMatrix(ColorMatrix().apply { setToSaturation(0f) }) }
    Surface(
        shape = RoundedCornerShape(22.dp),
        color = if (isEarned) scheme.primaryContainer else scheme.surface,
        border = if (isEarned) null else androidx.compose.foundation.BorderStroke(1.dp, scheme.outlineVariant),
        modifier = Modifier
            .width(148.dp)
            .clearAndSetSemantics {
                contentDescription = if (isEarned) "${badge.name} badge, earned"
                else "${badge.name} badge, locked. ${badge.howToEarn}"
            }
    ) {
        Column(
            Modifier.padding(14.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            Image(
                painter = painterResource(badge.art),
                contentDescription = null,
                contentScale = ContentScale.Fit,
                colorFilter = if (isEarned) null else grayscale,
                modifier = Modifier
                    .size(64.dp)
                    .graphicsLayer { alpha = if (isEarned) 1f else 0.45f }
            )
            Text(badge.name, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold, textAlign = TextAlign.Center)
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                Icon(
                    if (isEarned) Icons.Rounded.CheckCircle else Icons.Outlined.Lock,
                    contentDescription = null,
                    tint = if (isEarned) scheme.primary else scheme.onSurfaceVariant,
                    modifier = Modifier.size(16.dp)
                )
                Text(
                    if (isEarned) "Earned" else "Locked",
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.Bold
                )
            }
            if (!isEarned) {
                Text(
                    badge.howToEarn,
                    style = MaterialTheme.typography.bodySmall,
                    color = scheme.onSurfaceVariant,
                    textAlign = TextAlign.Center
                )
            }
        }
    }
}
