package com.alventur.silipapp.ui.learn

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.alventur.silipapp.data.demo.DemoHousehold
import com.alventur.silipapp.data.demo.DemoLabels
import com.alventur.silipapp.data.local.ProgressStore
import com.alventur.silipapp.ui.AdaptivePage
import com.alventur.silipapp.ui.PreviewBadge
import com.alventur.silipapp.ui.SectionHeading
import com.alventur.silipapp.ui.design.formatNumber

// WAVE 2: Learn/engagement owner expands this.
// Target (pillar 5): weekly XP and kWh saved; "You" highlighted; animated rank change
// (LeaderboardEntry.rankChange, animateItem in LazyColumn); badges shelf with chest/trophy art.
// Note: ProgressStore keeps total XP only; add weekly XP tracking if the board should reset weekly.

/** Neighborhood leaderboard (Demo neighborhood). Neighbors are demo data; "You" uses your XP. */
@Composable
internal fun LeaderboardScreen(
    contentPadding: PaddingValues,
    onBack: () -> Unit
) {
    val context = LocalContext.current
    val store = remember(context) { ProgressStore.get(context) }
    val progress by store.progress.collectAsState()
    val entries = remember(progress.xp) { DemoHousehold.leaderboard(yourWeeklyXp = progress.xp) }

    AdaptivePage(contentPadding) {
        item { SectionHeading("Neighborhood", "This week's XP and estimated kWh saved.") }
        item { PreviewBadge(label = DemoLabels.NEIGHBORHOOD) }
        items(entries, key = { it.name }) { entry ->
            val scheme = MaterialTheme.colorScheme
            Card(
                shape = RoundedCornerShape(20.dp),
                colors = CardDefaults.cardColors(
                    containerColor = if (entry.isYou) scheme.primaryContainer else scheme.surface
                ),
                modifier = Modifier
                    .fillMaxWidth()
                    .clearAndSetSemantics {
                        contentDescription = "Rank ${entry.rank}, ${entry.name}, ${entry.weeklyXp} XP, " +
                            "${formatNumber(entry.kwhSaved, 1)} kWh saved"
                    }
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp).heightIn(min = 32.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Text(
                        entry.rank.toString(),
                        style = MaterialTheme.typography.titleMedium.copy(fontFamily = FontFamily.Monospace),
                        modifier = Modifier.widthIn(min = 24.dp)
                    )
                    Column(Modifier.weight(1f)) {
                        Text(entry.name, style = MaterialTheme.typography.titleMedium,
                            fontWeight = if (entry.isYou) FontWeight.Bold else FontWeight.SemiBold)
                        Text("${formatNumber(entry.kwhSaved, 1)} kWh saved", style = MaterialTheme.typography.bodySmall)
                    }
                    Text(
                        "${entry.weeklyXp} XP",
                        style = MaterialTheme.typography.titleMedium.copy(fontFamily = FontFamily.Monospace)
                    )
                }
            }
        }
        item {
            OutlinedButton(onClick = onBack, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) {
                Text("Back to Learn")
            }
        }
    }
}
