package com.alventur.silipapp.ui.design

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.tween
import androidx.compose.material3.LocalTextStyle
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableDoubleStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import java.util.Locale

/** "₱1,234.50". Pesos always lead, per the copy rules. */
fun formatPesos(amount: Double, decimals: Int = 2): String =
    "₱" + String.format(Locale.getDefault(), "%,.${decimals}f", amount)

/** "1,234.5" with a fixed number of decimals. */
fun formatNumber(value: Double, decimals: Int = 0): String =
    String.format(Locale.getDefault(), "%,.${decimals}f", value)

/**
 * A number that counts from its previous value to [value] instead of jumping.
 *
 * - Digits are monospaced with tabular figures, so the width stays steady while counting.
 * - TalkBack reads only the final value ([accessibilityText] or `format(value)`), never the frames.
 * - Under reduce motion the value changes at once.
 * - The first composition shows [value] directly; pass [countFrom] to count up on entry (e.g. 0 for "+10 XP").
 *
 * @param format turns the shown value into text. See [formatPesos] and [formatNumber].
 */
@Composable
fun AnimatedNumber(
    value: Double,
    modifier: Modifier = Modifier,
    format: (Double) -> String = { formatNumber(it) },
    style: TextStyle = LocalTextStyle.current,
    color: Color = Color.Unspecified,
    durationMillis: Int = SilipMotion.COUNT,
    countFrom: Double? = null,
    accessibilityText: String? = null
) {
    val reduceMotion = rememberReduceMotion()
    var shown by remember { mutableDoubleStateOf(countFrom ?: value) }
    val progress = remember { Animatable(1f) }
    LaunchedEffect(value, reduceMotion) {
        if (reduceMotion || shown == value) {
            shown = value
            return@LaunchedEffect
        }
        val start = shown
        progress.snapTo(0f)
        progress.animateTo(1f, tween(durationMillis, easing = SilipMotion.CountEasing)) {
            shown = start + (value - start) * this.value
        }
        shown = value
    }
    val spoken = accessibilityText ?: format(value)
    Text(
        text = format(shown),
        style = style.merge(TextStyle(fontFamily = FontFamily.Monospace, fontFeatureSettings = "tnum")),
        color = color,
        modifier = modifier.clearAndSetSemantics { contentDescription = spoken }
    )
}

/**
 * Peso counter, e.g. "₱12.05/h". Use for burn rate, cost so far and rewards.
 * Peso figures are estimates: keep an "estimate" label nearby.
 */
@Composable
fun AnimatedPesos(
    amount: Double,
    modifier: Modifier = Modifier,
    decimals: Int = 2,
    suffix: String = "",
    style: TextStyle = LocalTextStyle.current,
    color: Color = Color.Unspecified,
    countFrom: Double? = null,
    accessibilityText: String? = null
) {
    AnimatedNumber(
        value = amount,
        modifier = modifier,
        format = { formatPesos(it, decimals) + suffix },
        style = style,
        color = color,
        countFrom = countFrom,
        accessibilityText = accessibilityText
    )
}
