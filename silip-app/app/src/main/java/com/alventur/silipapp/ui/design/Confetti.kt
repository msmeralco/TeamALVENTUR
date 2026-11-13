package com.alventur.silipapp.ui.design

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.rotate
import com.alventur.silipapp.ui.theme.AliGlowGreen
import com.alventur.silipapp.ui.theme.Ember
import com.alventur.silipapp.ui.theme.Forest
import com.alventur.silipapp.ui.theme.Moss
import com.alventur.silipapp.ui.theme.Sage
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin
import kotlin.random.Random

/** Confetti colors from the SILIP palette. */
object ConfettiDefaults {
    val colors: List<Color> = listOf(Forest, Moss, Sage, AliGlowGreen, Ember)
}

private class Particle(
    val angle: Float,
    val speed: Float,
    val spin: Float,
    val startRotation: Float,
    val size: Float,
    val color: Color,
    val round: Boolean
)

/**
 * One-shot confetti burst drawn on a Canvas. Overlay it on the content (for example inside a Box
 * with `Modifier.matchParentSize()`); it does not take touches or TalkBack focus.
 *
 * A burst plays each time [trigger] changes to a new non-null value. Under reduce motion
 * nothing is drawn and [onFinished] runs at once.
 *
 * @param origin burst point as fractions of the canvas (0.5, 0.35 = center, upper third).
 */
@Composable
fun ConfettiBurst(
    trigger: Any?,
    modifier: Modifier = Modifier,
    origin: Offset = Offset(0.5f, 0.35f),
    particleCount: Int = 72,
    durationMillis: Int = 1700,
    colors: List<Color> = ConfettiDefaults.colors,
    onFinished: () -> Unit = {}
) {
    val reduceMotion = rememberReduceMotion()
    val finished by rememberUpdatedState(onFinished)
    val progress = remember { Animatable(0f) }
    var particles by remember { mutableStateOf<List<Particle>>(emptyList()) }

    LaunchedEffect(trigger) {
        if (trigger == null) return@LaunchedEffect
        if (reduceMotion || colors.isEmpty()) {
            particles = emptyList()
            finished()
            return@LaunchedEffect
        }
        val random = Random(trigger.hashCode())
        particles = List(particleCount) {
            Particle(
                // Mostly upward, spread 130 degrees.
                angle = (-PI / 2 + (random.nextFloat() - 0.5f) * 2.27f).toFloat(),
                speed = 0.55f + random.nextFloat() * 0.85f,
                spin = (random.nextFloat() - 0.5f) * 900f,
                startRotation = random.nextFloat() * 360f,
                size = 0.012f + random.nextFloat() * 0.014f,
                color = colors[random.nextInt(colors.size)],
                round = random.nextFloat() < 0.3f
            )
        }
        progress.snapTo(0f)
        progress.animateTo(1f, tween(durationMillis, easing = LinearEasing))
        particles = emptyList()
        finished()
    }

    if (particles.isEmpty()) return
    Canvas(modifier) {
        val p = progress.value
        val seconds = p * durationMillis / 1000f
        val unit = size.minDimension
        val gravity = unit * 1.7f
        val start = Offset(size.width * origin.x, size.height * origin.y)
        val alpha = 1f - ((p - 0.7f) / 0.3f).coerceIn(0f, 1f)
        particles.forEach { particle ->
            val v = particle.speed * unit * 1.25f
            // Air drag: horizontal speed eases off over time.
            val drag = 1f / (1f + seconds * 1.2f)
            val x = start.x + cos(particle.angle) * v * seconds * drag
            val y = start.y + sin(particle.angle) * v * seconds + 0.5f * gravity * seconds * seconds
            val side = particle.size * unit
            val color = particle.color.copy(alpha = alpha)
            if (particle.round) {
                drawCircle(color = color, radius = side * 0.45f, center = Offset(x, y))
            } else {
                rotate(particle.startRotation + particle.spin * seconds, pivot = Offset(x, y)) {
                    drawRect(
                        color = color,
                        topLeft = Offset(x - side / 2f, y - side / 4f),
                        size = Size(side, side / 2f)
                    )
                }
            }
        }
    }
}
