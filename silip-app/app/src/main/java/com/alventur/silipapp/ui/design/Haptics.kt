package com.alventur.silipapp.ui.design

import androidx.compose.runtime.Composable
import androidx.compose.runtime.Stable
import androidx.compose.runtime.remember
import androidx.compose.ui.hapticfeedback.HapticFeedback
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback

/**
 * Named haptics so every screen uses the same feel. Android respects the user's
 * system "touch feedback" setting, so no extra opt-out is needed.
 *
 * - [tick]: chart scrubber crossing a bar, timer seconds. Very light.
 * - [select]: a chip or answer is chosen.
 * - [confirm]: a key action succeeded (joined event, quiz correct, alert resolved).
 * - [reject]: wrong answer or a blocked action.
 * - [toggle]: a switch changed.
 * - [longPress]: press-and-hold started (scrubber grab).
 */
@Stable
class SilipHaptics internal constructor(private val feedback: HapticFeedback) {
    fun tick() = feedback.performHapticFeedback(HapticFeedbackType.SegmentFrequentTick)
    fun select() = feedback.performHapticFeedback(HapticFeedbackType.SegmentTick)
    fun confirm() = feedback.performHapticFeedback(HapticFeedbackType.Confirm)
    fun reject() = feedback.performHapticFeedback(HapticFeedbackType.Reject)
    fun toggle(on: Boolean) = feedback.performHapticFeedback(
        if (on) HapticFeedbackType.ToggleOn else HapticFeedbackType.ToggleOff
    )
    fun longPress() = feedback.performHapticFeedback(HapticFeedbackType.LongPress)
}

/** `val haptics = rememberHaptics(); haptics.confirm()` */
@Composable
fun rememberHaptics(): SilipHaptics {
    val feedback = LocalHapticFeedback.current
    return remember(feedback) { SilipHaptics(feedback) }
}
