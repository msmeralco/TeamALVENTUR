package com.alventur.silipapp.ui.alerts

import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import com.alventur.silipapp.data.demo.DemoLabels
import com.alventur.silipapp.data.demo.DemoSafetyAlert
import com.alventur.silipapp.data.local.AlertResolution
import com.alventur.silipapp.ui.AliPose
import com.alventur.silipapp.ui.PreviewBadge
import com.alventur.silipapp.ui.design.AliGlow
import com.alventur.silipapp.ui.design.AnimatedAli
import com.alventur.silipapp.ui.design.pressScale
import com.alventur.silipapp.ui.design.rememberHaptics
import com.alventur.silipapp.notifications.SafetyReminder
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Surface
import java.time.format.DateTimeFormatter
import java.util.Locale

/**
 * Safety alert sheet for the steady-load-while-away case. Truthful copy comes from [alert].
 *
 * - "I checked, all good" → [onResolved] with [AlertResolution.CheckedAllGood]; Ali turns green.
 * - "Call someone at home" → opens the dialer with no number (user chooses; nothing is stored),
 *   then [onResolved] with [AlertResolution.CalledSomeone].
 * - "Remind me in 10 min" → schedules [SafetyReminder] (a one-time notification on the home-safety
 *   channel), calls [onSnooze], then closes. Resolving the alert cancels a pending reminder.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun SafetyAlertSheet(
    alert: DemoSafetyAlert,
    onDismiss: () -> Unit,
    onResolved: (AlertResolution) -> Unit,
    onSnooze: () -> Unit
) {
    val context = LocalContext.current
    val haptics = rememberHaptics()
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    var resolved by rememberSaveable { mutableStateOf(false) }

    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = sheetState) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .navigationBarsPadding()
                .padding(horizontal = 24.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                AnimatedAli(
                    pose = if (resolved) AliPose.Success else AliPose.Caution,
                    glow = if (resolved) AliGlow.Green else AliGlow.Orange,
                    size = 96.dp
                )
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    PreviewBadge(label = DemoLabels.SIMULATED)
                    Text(
                        text = if (resolved) "Thanks for checking." else alert.title,
                        style = MaterialTheme.typography.titleLarge,
                        modifier = Modifier.semantics {
                            heading()
                            liveRegion = LiveRegionMode.Polite
                        }
                    )
                }
            }
            if (!resolved) {
                Text(alert.message, style = MaterialTheme.typography.bodyLarge)
                WhatAliSaw(alert)
                Text(alert.limits, style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant)
                Button(
                    onClick = {
                        haptics.confirm()
                        SafetyReminder.cancel(context, alert.id)
                        resolved = true
                        onResolved(AlertResolution.CheckedAllGood)
                    },
                    modifier = Modifier.fillMaxWidth().heightIn(min = 52.dp).pressScale()
                ) { Text("I checked, all good") }
                OutlinedButton(
                    onClick = {
                        try {
                            context.startActivity(Intent(Intent.ACTION_DIAL, Uri.parse("tel:")))
                        } catch (_: ActivityNotFoundException) {
                            // No dialer on this device: nothing to open.
                        }
                        SafetyReminder.cancel(context, alert.id)
                        resolved = true
                        onResolved(AlertResolution.CalledSomeone)
                    },
                    modifier = Modifier.fillMaxWidth().heightIn(min = 52.dp).pressScale()
                ) { Text("Call someone at home") }
                TextButton(
                    onClick = {
                        haptics.tick()
                        SafetyReminder.schedule(context, alert.id, alert.message)
                        onSnooze()
                        onDismiss()
                    },
                    modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)
                ) { Text("Remind me in 10 min") }
            } else {
                Text(
                    "Quick checks like this keep your home safer.",
                    style = MaterialTheme.typography.bodyLarge
                )
                Button(onClick = onDismiss, modifier = Modifier.fillMaxWidth().heightIn(min = 52.dp)) {
                    Text("Close")
                }
            }
        }
    }
}

private val ClockFormat: DateTimeFormatter = DateTimeFormatter.ofPattern("h:mm a", Locale.US)

/** The three facts the clamp actually saw, as short labeled chips. No heat or appliance claims. */
@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun WhatAliSaw(alert: DemoSafetyAlert) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(
            "What Ali saw",
            style = MaterialTheme.typography.labelLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        FlowRow(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            FactChip(label = "Steady load", value = "${"%.1f".format(alert.steadyKw)} kW")
            FactChip(label = "For", value = "${alert.minutes} min since ${alert.startedAt.format(ClockFormat)}")
            if (alert.awayMode) FactChip(label = "Away mode", value = "On")
        }
    }
}

@Composable
private fun FactChip(label: String, value: String) {
    Surface(
        shape = RoundedCornerShape(14.dp),
        color = MaterialTheme.colorScheme.tertiaryContainer,
        contentColor = MaterialTheme.colorScheme.onTertiaryContainer
    ) {
        Column(Modifier.padding(horizontal = 12.dp, vertical = 8.dp)) {
            Text(label, style = MaterialTheme.typography.labelMedium)
            Text(value, style = MaterialTheme.typography.titleSmall)
        }
    }
}
