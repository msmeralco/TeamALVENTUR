package com.alventur.silipapp.ui.design

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.size
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.semantics.ProgressBarRangeInfo
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.progressBarRangeInfo
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

/**
 * Circular progress with a center slot, for "today's cost vs daily budget", the quiz timer,
 * and the burn-rate hero.
 *
 * - [progress] is clamped to 0..1 and animates with a gentle spring (snaps under reduce motion).
 * - [color] changes animate, so a switch from green to orange reads as a change, not a flicker.
 *   Color is never the only signal: put words in [content] or nearby ("Higher than usual").
 * - [pulse] draws a soft expanding halo to draw attention (e.g. burn rate rising). Off under reduce motion.
 * - [contentDescription] is read by TalkBack together with the progress value; children merge into it.
 */
@Composable
fun ProgressRing(
    progress: Float,
    modifier: Modifier = Modifier,
    size: Dp = 120.dp,
    strokeWidth: Dp = 10.dp,
    color: Color = MaterialTheme.colorScheme.primary,
    trackColor: Color = MaterialTheme.colorScheme.primaryContainer,
    pulse: Boolean = false,
    contentDescription: String? = null,
    content: @Composable BoxScope.() -> Unit = {}
) {
    val reduceMotion = rememberReduceMotion()
    val target = progress.coerceIn(0f, 1f).takeUnless { it.isNaN() } ?: 0f
    val animated by animateFloatAsState(
        targetValue = target,
        animationSpec = SilipMotion.gentle<Float>().orSnap(reduceMotion),
        label = "ring-progress"
    )
    val ringColor by animateColorAsState(
        targetValue = color,
        animationSpec = SilipMotion.standard<Color>().orSnap(reduceMotion),
        label = "ring-color"
    )
    val showPulse = pulse && !reduceMotion
    val halo = if (showPulse) {
        val transition = rememberInfiniteTransition(label = "ring-pulse")
        transition.animateFloat(
            initialValue = 0f,
            targetValue = 1f,
            animationSpec = infiniteRepeatable(tween(1600, easing = FastOutSlowInEasing), RepeatMode.Restart),
            label = "ring-halo"
        )
    } else {
        null
    }

    Box(
        modifier = modifier
            .size(size)
            .semantics(mergeDescendants = true) {
                progressBarRangeInfo = ProgressBarRangeInfo(target, 0f..1f)
                if (contentDescription != null) this.contentDescription = contentDescription
            },
        contentAlignment = Alignment.Center
    ) {
        Canvas(Modifier.matchParentSize()) {
            val stroke = strokeWidth.toPx()
            // Leave room for the halo outside the ring.
            val inset = stroke / 2f + stroke * 0.9f
            val arcSize = Size(this.size.width - inset * 2, this.size.height - inset * 2)
            val topLeft = Offset(inset, inset)
            halo?.let { state ->
                val h = state.value
                drawCircle(
                    color = ringColor.copy(alpha = 0.35f * (1f - h)),
                    radius = arcSize.minDimension / 2f + stroke * (0.2f + 0.9f * h),
                    style = Stroke(width = stroke * 0.5f)
                )
            }
            drawArc(
                color = trackColor,
                startAngle = 0f,
                sweepAngle = 360f,
                useCenter = false,
                topLeft = topLeft,
                size = arcSize,
                style = Stroke(width = stroke)
            )
            if (animated > 0f) {
                drawArc(
                    color = ringColor,
                    startAngle = -90f,
                    sweepAngle = 360f * animated,
                    useCenter = false,
                    topLeft = topLeft,
                    size = arcSize,
                    style = Stroke(width = stroke, cap = StrokeCap.Round)
                )
            }
        }
        content()
    }
}
