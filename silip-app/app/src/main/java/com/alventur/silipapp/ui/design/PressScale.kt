package com.alventur.silipapp.ui.design

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.waitForUpOrCancellation
import androidx.compose.foundation.interaction.InteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.composed
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.PointerEventPass
import androidx.compose.ui.input.pointer.pointerInput

/**
 * Shrinks the element slightly while pressed and springs back on release.
 *
 * Observes touches without consuming them, so it works on top of any clickable
 * (Button, Card(onClick), Modifier.clickable). Put it before the clickable in the chain:
 * `Button(onClick = ..., modifier = Modifier.pressScale())`.
 * Under reduce motion it does nothing.
 */
fun Modifier.pressScale(pressedScale: Float = 0.96f): Modifier = composed {
    val reduceMotion = rememberReduceMotion()
    var pressed by remember { mutableStateOf(false) }
    val scale by animateFloatAsState(
        targetValue = if (pressed && !reduceMotion) pressedScale else 1f,
        animationSpec = SilipMotion.snappy(),
        label = "press-scale"
    )
    this
        .graphicsLayer {
            scaleX = scale
            scaleY = scale
        }
        .pointerInput(Unit) {
            awaitEachGesture {
                awaitFirstDown(requireUnconsumed = false, pass = PointerEventPass.Initial)
                pressed = true
                waitForUpOrCancellation(pass = PointerEventPass.Initial)
                pressed = false
            }
        }
}

/**
 * Variant driven by an [InteractionSource] you already pass to a component, e.g.
 * `val source = remember { MutableInteractionSource() }`
 * `Button(onClick = ..., interactionSource = source, modifier = Modifier.pressScale(source))`.
 * Also reacts to keyboard and switch-access presses.
 */
fun Modifier.pressScale(interactionSource: InteractionSource, pressedScale: Float = 0.96f): Modifier = composed {
    val reduceMotion = rememberReduceMotion()
    val pressed by interactionSource.collectIsPressedAsState()
    val scale by animateFloatAsState(
        targetValue = if (pressed && !reduceMotion) pressedScale else 1f,
        animationSpec = SilipMotion.snappy(),
        label = "press-scale"
    )
    this.graphicsLayer {
        scaleX = scale
        scaleY = scale
    }
}
