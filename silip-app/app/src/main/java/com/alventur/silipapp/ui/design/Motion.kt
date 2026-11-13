package com.alventur.silipapp.ui.design

import android.animation.ValueAnimator
import android.content.ContentResolver
import android.database.ContentObserver
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import androidx.compose.animation.core.AnimationSpec
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.Easing
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.LinearOutSlowInEasing
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.SpringSpec
import androidx.compose.animation.core.TweenSpec
import androidx.compose.animation.core.snap
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalInspectionMode

/**
 * SILIP motion tokens.
 *
 * Rules (see docs/ui-foundation.md, "Motion"):
 * - UI transitions use [STANDARD] (250 ms) with [StandardEasing]. Nothing routine exceeds 300 ms.
 * - Playful moments (Ali, streak pop, confetti, XP) use [playful] springs.
 * - Motion that only decorates stops when [rememberReduceMotion] is true. Motion that shows
 *   a change of state snaps instead, via [orSnap].
 */
object SilipMotion {
    /** Small state changes: chip selection, icon swap. */
    const val SHORT = 150

    /** Default for UI transitions: content swaps, colors, sheets. */
    const val STANDARD = 250

    /** Larger, emphasized transitions such as step changes in onboarding. */
    const val EMPHASIZED = 300

    /** Number counters and progress rings. Long enough to read the change. */
    const val COUNT = 700

    /** Material standard easing. */
    val StandardEasing: Easing = FastOutSlowInEasing

    /** Emphasized decelerate, for things entering the screen. */
    val EnterEasing: Easing = CubicBezierEasing(0.05f, 0.7f, 0.1f, 1f)

    /** Things leaving the screen. */
    val ExitEasing: Easing = CubicBezierEasing(0.3f, 0f, 0.8f, 0.15f)

    /** Calm deceleration for counters. */
    val CountEasing: Easing = LinearOutSlowInEasing

    /** 250 ms standard tween. */
    fun <T> standard(): TweenSpec<T> = tween(STANDARD, easing = StandardEasing)

    /** 150 ms tween for small changes. */
    fun <T> short(): TweenSpec<T> = tween(SHORT, easing = StandardEasing)

    /** 300 ms entering tween. */
    fun <T> enter(): TweenSpec<T> = tween(EMPHASIZED, easing = EnterEasing)

    /** Bouncy spring for playful moments (Ali, streak, XP, nav icon). */
    fun <T> playful(): SpringSpec<T> =
        spring(dampingRatio = 0.55f, stiffness = Spring.StiffnessMediumLow)

    /** Snappy spring with little overshoot, for indicators and press feedback. */
    fun <T> snappy(): SpringSpec<T> =
        spring(dampingRatio = 0.75f, stiffness = Spring.StiffnessMedium)

    /** No-bounce spring for progress values. */
    fun <T> gentle(): SpringSpec<T> =
        spring(dampingRatio = Spring.DampingRatioNoBouncy, stiffness = Spring.StiffnessLow)
}

/** Returns [snap] when [reduceMotion] is true, otherwise this spec. */
fun <T> AnimationSpec<T>.orSnap(reduceMotion: Boolean): AnimationSpec<T> =
    if (reduceMotion) snap() else this

/**
 * True when the user turned animations off: Developer options "Animator duration scale" = 0,
 * or Accessibility "Remove animations" (which sets the same global scale).
 * Updates live if the setting changes while the app is open.
 */
@Composable
fun rememberReduceMotion(): Boolean {
    if (LocalInspectionMode.current) return false
    val resolver = LocalContext.current.contentResolver
    var reduce by remember(resolver) { mutableStateOf(isReduceMotionEnabled(resolver)) }
    DisposableEffect(resolver) {
        val observer = object : ContentObserver(Handler(Looper.getMainLooper())) {
            override fun onChange(selfChange: Boolean) {
                reduce = isReduceMotionEnabled(resolver)
            }
        }
        resolver.registerContentObserver(
            Settings.Global.getUriFor(Settings.Global.ANIMATOR_DURATION_SCALE),
            false,
            observer
        )
        onDispose { resolver.unregisterContentObserver(observer) }
    }
    return reduce
}

/** Non-composable check, for code outside composition. */
fun isReduceMotionEnabled(resolver: ContentResolver): Boolean {
    val scale = runCatching {
        Settings.Global.getFloat(resolver, Settings.Global.ANIMATOR_DURATION_SCALE, 1f)
    }.getOrDefault(1f)
    return scale == 0f || !ValueAnimator.areAnimatorsEnabled()
}
