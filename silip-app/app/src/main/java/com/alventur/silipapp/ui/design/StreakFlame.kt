package com.alventur.silipapp.ui.design

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.LocalFireDepartment
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.TransformOrigin
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.alventur.silipapp.ui.theme.Ember

/**
 * Eco-Streak flame with the day count.
 *
 * - [litToday] = the streak already counts today (gold flame with a soft glow and flicker).
 *   Not yet today = muted outline color, so the user sees there is still something to do.
 * - Each time [celebrateKey] changes to a new non-null value the flame pops (spring).
 *   Pass e.g. the streak count after a quiz.
 * - TalkBack reads "3-day Eco-Streak, done today" as one item.
 * - Under reduce motion: no flicker, no glow pulse, no pop.
 */
@Composable
fun StreakFlame(
    days: Int,
    modifier: Modifier = Modifier,
    litToday: Boolean = true,
    size: Dp = 32.dp,
    showCount: Boolean = true,
    countStyle: TextStyle = MaterialTheme.typography.titleMedium,
    celebrateKey: Any? = null
) {
    val reduceMotion = rememberReduceMotion()
    val flameColor = if (litToday) Ember else MaterialTheme.colorScheme.outline
    val pop = remember { Animatable(1f) }
    LaunchedEffect(celebrateKey, reduceMotion) {
        if (celebrateKey == null || reduceMotion) return@LaunchedEffect
        pop.snapTo(1.4f)
        pop.animateTo(1f, SilipMotion.playful())
    }
    val live = litToday && !reduceMotion
    val flicker = if (live) {
        val transition = rememberInfiniteTransition(label = "flame")
        transition.animateFloat(
            initialValue = 0f,
            targetValue = 1f,
            animationSpec = infiniteRepeatable(tween(700, easing = FastOutSlowInEasing), RepeatMode.Reverse),
            label = "flame-flicker"
        )
    } else {
        null
    }
    val description = "$days-day Eco-Streak, " + if (litToday) "done today" else "not done today"

    Row(
        modifier = modifier.clearAndSetSemantics { contentDescription = description },
        horizontalArrangement = Arrangement.spacedBy(4.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(Modifier.size(size), contentAlignment = Alignment.Center) {
            if (litToday) {
                Canvas(Modifier.matchParentSize()) {
                    val f = flicker?.value ?: 0.5f
                    val center = Offset(this.size.width / 2f, this.size.height * 0.62f)
                    val radius = this.size.minDimension * (0.55f + 0.08f * f)
                    drawCircle(
                        brush = Brush.radialGradient(
                            colors = listOf(Ember.copy(alpha = 0.35f + 0.15f * f), Color.Transparent),
                            center = center,
                            radius = radius
                        ),
                        radius = radius,
                        center = center
                    )
                }
            }
            Icon(
                imageVector = Icons.Rounded.LocalFireDepartment,
                contentDescription = null,
                tint = flameColor,
                modifier = Modifier
                    .fillMaxSize()
                    .graphicsLayer {
                        val f = flicker?.value ?: 0.5f
                        transformOrigin = TransformOrigin(0.5f, 0.9f)
                        scaleX = pop.value * (1f - 0.02f * f)
                        scaleY = pop.value * (0.97f + 0.06f * f)
                    }
            )
        }
        if (showCount) {
            Text(
                text = days.toString(),
                style = countStyle.copy(fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold),
                color = MaterialTheme.colorScheme.onSurface
            )
        }
    }
}
