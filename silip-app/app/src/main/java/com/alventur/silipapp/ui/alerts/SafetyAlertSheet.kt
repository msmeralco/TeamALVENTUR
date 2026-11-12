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

// WAVE 2: Home owner expands this.
// Target (pillar 4): full-screen sheet; Ali glows orange; "what was seen" block (steady load, how long,
// while away); the three actions; resolution animation where Ali turns green with "Thanks for checking.";
// a 10-minute reminder (WorkManager or AlarmManager) for "Remind me in 10 min".

/**
 * Safety alert sheet for the steady-load-while-away case. Truthful copy comes from [alert].
 *
 * - "I checked, all good" → [onResolved] with [AlertResolution.CheckedAllGood]; Ali turns green.
 * - "Call someone at home" → opens the dialer with no number (user chooses; nothing is stored),
 *   then [onResolved] with [AlertResolution.CalledSomeone].
 * - "Remind me in 10 min" → [onSnooze], then closes. Wave 1 stores the snooze only; no reminder fires yet.
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
                Text(alert.limits, style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant)
                Button(
                    onClick = {
                        haptics.confirm()
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
                        resolved = true
                        onResolved(AlertResolution.CalledSomeone)
                    },
                    modifier = Modifier.fillMaxWidth().heightIn(min = 52.dp).pressScale()
                ) { Text("Call someone at home") }
                TextButton(
                    onClick = {
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
