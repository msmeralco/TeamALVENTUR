package com.alventur.silipapp.ui.design

import androidx.compose.animation.Crossfade
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.runtime.State
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.TransformOrigin
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.alventur.silipapp.ui.AliPose
import com.alventur.silipapp.ui.theme.AliGlowGreen
import com.alventur.silipapp.ui.theme.AliGlowOrange

/**
 * Color of the light behind Ali's bulb. Green = welcome, learning, all good.
 * Orange = caution or "please check". The glow never carries meaning alone: pair it with text.
 */
enum class AliGlow(val color: Color) {
    Green(AliGlowGreen),
    Orange(AliGlowOrange);

    companion object {
        /** Orange for [AliPose.Caution], green for every other pose. */
        internal fun forPose(pose: AliPose): AliGlow =
            if (pose == AliPose.Caution) Orange else Green
    }
}

/**
 * Ali the Alitaptap with idle life: a gentle bob, a wing flutter (small rotation and squash),
 * and a pulsing glow drawn behind the bulb.
 *
 * - Decorative to TalkBack (semantics cleared). Put the message in nearby text.
 * - Under [rememberReduceMotion] Ali is drawn still, with a steady glow.
 * - Changing [pose] crossfades; changing [glow] animates the glow color.
 *
 * @param pose which illustration to show.
 * @param glow bulb light color. Defaults to orange for [AliPose.Caution], green otherwise.
 * @param size square size of Ali, including the glow.
 * @param animate false to draw Ali still even when motion is allowed (dense lists).
 * @param flyIn true to fly Ali in from the lower left on first composition (onboarding splash).
 */
@Composable
internal fun AnimatedAli(
    pose: AliPose,
    modifier: Modifier = Modifier,
    glow: AliGlow = AliGlow.forPose(pose),
    size: Dp = 96.dp,
    animate: Boolean = true,
    flyIn: Boolean = false
) {
    val reduceMotion = rememberReduceMotion()
    val moving = animate && !reduceMotion
    val motion = if (moving) rememberLiveAliMotion() else StillAliMotion
    val glowColor by animateColorAsState(
        targetValue = glow.color,
        animationSpec = SilipMotion.standard<Color>().orSnap(reduceMotion),
        label = "ali-glow-color"
    )
    val entrance = remember { Animatable(if (flyIn && !reduceMotion) 0f else 1f) }
    LaunchedEffect(flyIn, reduceMotion) {
        if (flyIn && !reduceMotion) {
            entrance.animateTo(1f, spring(dampingRatio = 0.62f, stiffness = 140f))
        } else {
            entrance.snapTo(1f)
        }
    }

    Box(
        modifier = modifier
            .size(size)
            .clearAndSetSemantics { }
            .graphicsLayer {
                val e = entrance.value
                val remaining = 1f - e
                translationX = -size.toPx() * 1.1f * remaining
                translationY = size.toPx() * 0.7f * remaining - motion.bob.value * 5.dp.toPx()
                alpha = e.coerceIn(0f, 1f)
                rotationZ = -14f * remaining + (motion.flutter.value - 0.5f) * 3f
                scaleX = 1f + (motion.flutter.value - 0.5f) * 0.02f
                scaleY = 1f - (motion.flutter.value - 0.5f) * 0.015f
                transformOrigin = TransformOrigin(0.5f, 0.55f)
            }
    ) {
        // Glow sits behind the bulb (lower left of every pose).
        Canvas(Modifier.matchParentSize()) {
            val pulse = motion.pulse.value
            val center = Offset(this.size.width * 0.42f, this.size.height * 0.74f)
            val radius = this.size.minDimension * (0.28f + 0.07f * pulse)
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(
                        glowColor.copy(alpha = 0.30f + 0.28f * pulse),
                        glowColor.copy(alpha = 0.10f + 0.08f * pulse),
                        Color.Transparent
                    ),
                    center = center,
                    radius = radius
                ),
                radius = radius,
                center = center
            )
        }
        Crossfade(
            targetState = pose,
            animationSpec = tween(SilipMotion.STANDARD),
            label = "ali-pose",
            modifier = Modifier.fillMaxSize()
        ) { visiblePose ->
            Image(
                painter = painterResource(visiblePose.drawableRes),
                contentDescription = null,
                contentScale = ContentScale.Fit,
                modifier = Modifier.fillMaxSize()
            )
        }
    }
}

private class AliMotionValues(
    val bob: State<Float>,
    val flutter: State<Float>,
    val pulse: State<Float>
)

private val StillAliMotion = AliMotionValues(
    bob = mutableFloatStateOf(0.5f),
    flutter = mutableFloatStateOf(0.5f),
    pulse = mutableFloatStateOf(0.5f)
)

@Composable
private fun rememberLiveAliMotion(): AliMotionValues {
    val transition = rememberInfiniteTransition(label = "ali-idle")
    val bob = transition.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(1900, easing = FastOutSlowInEasing), RepeatMode.Reverse),
        label = "ali-bob"
    )
    val flutter = transition.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(420, easing = FastOutSlowInEasing), RepeatMode.Reverse),
        label = "ali-flutter"
    )
    val pulse = transition.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(1400, easing = FastOutSlowInEasing), RepeatMode.Reverse),
        label = "ali-pulse"
    )
    return remember(bob, flutter, pulse) { AliMotionValues(bob, flutter, pulse) }
}
