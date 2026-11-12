package com.alventur.silipapp.ui.grid

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import com.alventur.silipapp.data.demo.DemoHousehold
import com.alventur.silipapp.data.demo.DemoLabels
import com.alventur.silipapp.ui.AdaptivePage
import com.alventur.silipapp.ui.DemoEvent
import com.alventur.silipapp.ui.DemoEventBus
import com.alventur.silipapp.ui.GridEventVisual
import com.alventur.silipapp.ui.PreviewBadge
import com.alventur.silipapp.ui.design.formatNumber
import com.alventur.silipapp.ui.design.pressScale
import com.alventur.silipapp.ui.design.rememberHaptics

// WAVE 2: Grid owner expands this.
// Target (pillar 6): event card with countdown to 8 PM; Join; suggested actions with kW;
// live view (your reduction vs target, neighbors joined N / 60, transformer gauge animating
// from orange 95% to emerald as participation rises, with TransformerStatus words);
// completion with ConfettiBurst and "+₱50 pending (pilot preview, no payout service yet)"; history.

/** Grid events tab: the demo April-night event (pilot preview) and the existing explainer. */
@Composable
internal fun GridEventScreen(
    contentPadding: PaddingValues,
    demoEvents: DemoEventBus
) {
    val event = DemoHousehold.gridEvent
    val haptics = rememberHaptics()
    var joined by rememberSaveable { mutableStateOf(false) }

    LaunchedEffect(demoEvents.pending) {
        if (demoEvents.pending == DemoEvent.StartGridEvent) demoEvents.consume(DemoEvent.StartGridEvent)
    }

    val households = if (joined) event.initialJoined + 1 else event.initialJoined
    val load = event.transformerLoadPercent(households)

    AdaptivePage(contentPadding) {
        item {
            Card(
                shape = RoundedCornerShape(28.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.tertiaryContainer),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    PreviewBadge(label = DemoLabels.PILOT)
                    Text(event.headline, style = MaterialTheme.typography.headlineSmall)
                    Text(event.message, style = MaterialTheme.typography.bodyLarge)
                    Text(
                        "Transformer load ${formatNumber(load)}% · ${event.loadStatus(load).label}",
                        style = MaterialTheme.typography.titleMedium,
                        modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite }
                    )
                    Text("$households of ${event.targetHouseholds} households joined",
                        style = MaterialTheme.typography.bodyMedium)
                    event.suggestedActions.firstOrNull()?.let { (action, kw) ->
                        Text("Try: $action, about −${formatNumber(kw, 1)} kW", style = MaterialTheme.typography.bodyMedium)
                    }
                    Button(
                        onClick = { joined = !joined; haptics.confirm() },
                        modifier = Modifier.fillMaxWidth().heightIn(min = 52.dp).pressScale()
                    ) { Text(if (joined) "Leave the event" else "Join for 8–9 PM") }
                    Text(event.disclaimer, style = MaterialTheme.typography.bodySmall)
                }
            }
        }
        item { GridEventVisual() }
    }
}
