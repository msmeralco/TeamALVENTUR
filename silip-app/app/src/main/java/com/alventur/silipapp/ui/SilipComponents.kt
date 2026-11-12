package com.alventur.silipapp.ui

import androidx.compose.animation.Crossfade
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.outlined.Lock
import androidx.compose.material.icons.outlined.TipsAndUpdates
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.foundation.layout.fillMaxSize
import com.alventur.silipapp.data.remote.HouseholdDashboardState
import com.alventur.silipapp.data.remote.UsagePoint
import com.alventur.silipapp.education.Lesson
import com.alventur.silipapp.R
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

internal enum class AliPose(val drawableRes: Int) {
    Welcome(R.drawable.ali_welcome),
    Learning(R.drawable.ali_learning),
    Practice(R.drawable.ali_practice),
    HouseholdCheck(R.drawable.ali_household_check),
    Success(R.drawable.ali_success),
    Caution(R.drawable.ali_caution)
}

internal enum class AliMotion {
    Still,
    Idle,
    Celebrate
}

@Composable
internal fun AliMascotIllustration(
    pose: AliPose,
    modifier: Modifier = Modifier,
    motion: AliMotion = AliMotion.Still
) {
    val animatedModifier = when (motion) {
        AliMotion.Still -> modifier
        AliMotion.Idle -> {
            val transition = rememberInfiniteTransition(label = "ali-idle")
            val bob by transition.animateFloat(
                initialValue = 0f,
                targetValue = -4f,
                animationSpec = infiniteRepeatable(
                    animation = tween(durationMillis = 1900, easing = FastOutSlowInEasing),
                    repeatMode = RepeatMode.Reverse
                ),
                label = "ali-bob"
            )
            val tilt by transition.animateFloat(
                initialValue = -1.2f,
                targetValue = 1.2f,
                animationSpec = infiniteRepeatable(
                    animation = tween(durationMillis = 2600, easing = FastOutSlowInEasing),
                    repeatMode = RepeatMode.Reverse
                ),
                label = "ali-tilt"
            )
            modifier.graphicsLayer {
                translationY = bob.dp.toPx()
                rotationZ = tilt
            }
        }
        AliMotion.Celebrate -> {
            val hop = remember { Animatable(0f) }
            LaunchedEffect(pose, motion) {
                if (pose == AliPose.Success) {
                    hop.snapTo(0f)
                    hop.animateTo(-14f, animationSpec = tween(durationMillis = 150))
                    hop.animateTo(0f, animationSpec = spring(dampingRatio = 0.52f))
                }
            }
            modifier.graphicsLayer { translationY = hop.value.dp.toPx() }
        }
    }

    Crossfade(
        targetState = pose,
        modifier = animatedModifier,
        animationSpec = tween(durationMillis = 240),
        label = "ali-pose"
    ) { visiblePose ->
        Image(
            painter = painterResource(visiblePose.drawableRes),
            contentDescription = null,
            contentScale = ContentScale.Fit,
            modifier = Modifier.fillMaxSize()
        )
    }
}

@Composable
internal fun PageHeader(
    eyebrow: String,
    title: String,
    subtitle: String,
    pose: AliPose,
    motion: AliMotion = AliMotion.Idle,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(26.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(8.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            AliMascotIllustration(
                pose = pose,
                modifier = Modifier.size(width = 82.dp, height = 88.dp),
                motion = motion
            )
            Column(
                modifier = Modifier
                    .weight(1f)
                    .padding(horizontal = 14.dp, vertical = 12.dp),
                verticalArrangement = Arrangement.spacedBy(3.dp)
            ) {
                Text(
                    text = eyebrow.uppercase(),
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary
                )
                Text(
                    text = title,
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurface,
                    modifier = Modifier.semantics { heading() }
                )
                Text(
                    text = subtitle,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

@Composable
internal fun PreviewBadge(
    label: String = "Sample data",
    modifier: Modifier = Modifier,
    containerColor: Color = MaterialTheme.colorScheme.primary,
    contentColor: Color = MaterialTheme.colorScheme.onPrimary
) {
    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(50),
        color = containerColor
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.labelMedium,
            fontWeight = FontWeight.Bold,
            color = contentColor,
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp)
        )
    }
}

@Composable
internal fun EnergyReceiptCard() {
    val paper = MaterialTheme.colorScheme.onPrimary
    val leaf = MaterialTheme.colorScheme.primaryContainer
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(28.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primary),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp)
    ) {
        Column(
            modifier = Modifier.padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "RIGHT NOW",
                    style = MaterialTheme.typography.labelLarge,
                    fontWeight = FontWeight.Bold,
                    color = paper
                )
                PreviewBadge(
                    containerColor = leaf,
                    contentColor = MaterialTheme.colorScheme.onPrimaryContainer
                )
            }
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.Bottom
            ) {
                Column(verticalArrangement = Arrangement.spacedBy(1.dp)) {
                    Text(
                        text = "₱12.00",
                        style = MaterialTheme.typography.displaySmall.copy(
                            fontFamily = FontFamily.Monospace,
                            fontWeight = FontWeight.Bold,
                            fontSize = 38.sp,
                            lineHeight = 44.sp
                        ),
                        color = paper
                    )
                    Text(
                        text = "estimated per hour",
                        style = MaterialTheme.typography.bodyMedium,
                        color = paper
                    )
                }
                Column(horizontalAlignment = Alignment.End) {
                    Text(
                        text = "1.18 kW",
                        style = MaterialTheme.typography.titleMedium.copy(
                            fontFamily = FontFamily.Monospace,
                            fontWeight = FontWeight.Bold
                        ),
                        color = paper
                    )
                    Text(
                        text = "example load",
                        style = MaterialTheme.typography.labelMedium,
                        color = paper
                    )
                }
            }
            TrendLine(
                values = listOf(0.24f, 0.29f, 0.25f, 0.42f, 0.38f, 0.53f, 0.78f, 0.7f),
                lineColor = leaf,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(50.dp),
                description = "Example household load rises in the evening. This is not a live reading."
            )
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                listOf("6 am", "12 pm", "6 pm", "now").forEach { label ->
                    Text(
                        text = label,
                        style = MaterialTheme.typography.labelSmall,
                        color = paper
                    )
                }
            }
            Text(
                text = "Aircon on: ₱4.50 → ₱12/hr · sample",
                style = MaterialTheme.typography.bodySmall,
                color = paper
            )
        }
    }
}

@Composable
internal fun HouseholdDataCard(
    state: HouseholdDashboardState,
    deviceId: String,
    onDeviceIdChange: (String) -> Unit,
    showDeviceInput: Boolean,
    onConnect: () -> Unit,
    onRefresh: () -> Unit,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp)
    ) {
        Column(
            modifier = Modifier.padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Text(
                text = "Device readings",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold
            )
            if (showDeviceInput) {
                OutlinedTextField(
                    value = deviceId,
                    onValueChange = onDeviceIdChange,
                    label = { Text("Device ID") },
                    supportingText = { Text("PoC demo device: silip-esp32-test") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                Button(
                    onClick = onConnect,
                    enabled = deviceId.isNotBlank(),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Connect device")
                }
            }
            when (state) {
                HouseholdDashboardState.Loading -> {
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        CircularProgressIndicator(modifier = Modifier.size(24.dp), strokeWidth = 3.dp)
                        Text("Loading device readings…", style = MaterialTheme.typography.bodyMedium)
                    }
                }
                is HouseholdDashboardState.NotFound -> {
                    Text(
                        text = "No readings found for ${state.clampId}. Check the ID and try again.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    if (!showDeviceInput) {
                        OutlinedButton(onClick = onRefresh, modifier = Modifier.fillMaxWidth()) {
                            Text("Try again")
                        }
                    }
                }
                is HouseholdDashboardState.Error -> {
                    Text(
                        text = state.message,
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    OutlinedButton(onClick = onRefresh, modifier = Modifier.fillMaxWidth()) {
                        Text("Refresh")
                    }
                }
                is HouseholdDashboardState.Loaded -> {
                    val device = state.device
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "LAST 7 DAYS",
                            style = MaterialTheme.typography.labelMedium,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.primary
                        )
                        PreviewBadge(
                            label = when {
                                device.isSimulated -> "Simulated"
                                device.points.isEmpty() -> "Waiting"
                                else -> "Live"
                            }
                        )
                    }
                    Text(
                        text = "${device.totalKwh.energyFormat()} kWh",
                        style = MaterialTheme.typography.headlineLarge.copy(
                            fontFamily = FontFamily.Monospace,
                            fontWeight = FontWeight.Bold
                        )
                    )
                    Text(
                        text = if (device.points.isEmpty()) {
                            "No readings received yet."
                        } else {
                            "${device.points.size} intervals · whole-home energy use"
                        },
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
                        Text(
                            text = "${device.clampId} · Transformer ${device.transformerId}",
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.SemiBold
                        )
                        Text(
                            text = device.lastSeenAt?.let(::formatLastSeen)
                                ?.let { "Last reading · $it" }
                                ?: "Waiting for the first device reading",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    OutlinedButton(onClick = onRefresh, modifier = Modifier.fillMaxWidth()) {
                        Text("Refresh readings")
                    }
                }
            }
        }
    }
}

private fun Double.energyFormat(): String = String.format(Locale.getDefault(), "%.2f", this)

private fun formatLastSeen(timestamp: String): String = runCatching {
    OffsetDateTime.parse(timestamp)
        .atZoneSameInstant(ZoneId.systemDefault())
        .format(DateTimeFormatter.ofPattern("MMM d · h:mm a", Locale.getDefault()))
}.getOrDefault(timestamp)

@Composable
internal fun BudgetProgressCard(
    title: String = "Monthly budget",
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp)
    ) {
        Column(
            modifier = Modifier.padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = title,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurface
                )
                PreviewBadge(label = "Example")
            }
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.Bottom
            ) {
                Text(
                    text = "₱2,320",
                    style = MaterialTheme.typography.headlineMedium.copy(
                        fontFamily = FontFamily.Monospace,
                        fontWeight = FontWeight.Bold
                    ),
                    color = MaterialTheme.colorScheme.onSurface
                )
                Text(
                    text = "of ₱4,000",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            LinearProgressIndicator(
                progress = { 0.58f },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(9.dp)
                    .clip(CircleShape),
                color = MaterialTheme.colorScheme.primary,
                trackColor = MaterialTheme.colorScheme.surface
            )
            Text(
                text = "58% used",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
internal fun SafetyPreviewCard() {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .border(
                width = 1.dp,
                color = MaterialTheme.colorScheme.outlineVariant,
                shape = RoundedCornerShape(24.dp)
            ),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp)
    ) {
        Row(
            modifier = Modifier.padding(18.dp),
            horizontalArrangement = Arrangement.spacedBy(14.dp),
            verticalAlignment = Alignment.Top
        ) {
            AliMascotIllustration(
                pose = AliPose.Caution,
                modifier = Modifier.size(58.dp)
            )
            Column(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(5.dp)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "Home safety",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )
                    PreviewBadge(label = "Preview")
                }
                Text(
                    text = "Total load only. No appliance or heat alerts yet.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

@Composable
internal fun SectionHeading(
    title: String,
    subtitle: String? = null,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        Text(
            text = title,
            style = MaterialTheme.typography.titleLarge,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.semantics { heading() }
        )
        if (subtitle != null) {
            Text(
                text = subtitle,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
internal fun TrendBarsCard(
    title: String,
    description: String,
    modifier: Modifier = Modifier
) {
    val barColor = MaterialTheme.colorScheme.secondary
    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
        border = CardDefaults.outlinedCardBorder()
    ) {
        Column(
            modifier = Modifier.padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Text(
                text = title,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold
            )
            Text(
                text = description,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            SampleBars(
                values = listOf(0.22f, 0.36f, 0.28f, 0.43f, 0.54f, 0.4f, 0.82f, 0.65f),
                color = barColor,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(112.dp),
                chartDescription = "Example hourly household use: lower in the morning and higher in the evening."
            )
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                listOf("6 am", "10 am", "2 pm", "6 pm", "now").forEach { label ->
                    Text(
                        text = label,
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
            Text(
                text = "Example pattern · chart values are illustrative",
                style = MaterialTheme.typography.labelMedium,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.primary
            )
        }
    }
}

@Composable
internal fun HouseholdUsageTrendCard(points: List<UsagePoint>) {
    val recentPoints = points.sortedBy(UsagePoint::timestamp).takeLast(48)
    val peakKw = recentPoints.maxOfOrNull(UsagePoint::powerKw) ?: 0.0
    val normalized = recentPoints.map { point ->
        if (peakKw > 0.0) (point.powerKw / peakKw).toFloat() else 0f
    }
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
        border = CardDefaults.outlinedCardBorder()
    ) {
        Column(
            modifier = Modifier.padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Text(
                text = "Recent home load",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold
            )
            Text(
                text = "Relative demand · latest ${recentPoints.size} readings",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            if (recentPoints.isEmpty()) {
                Text(
                    text = "A trend will appear after the device sends readings.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            } else {
                TrendLine(
                    values = normalized,
                    lineColor = MaterialTheme.colorScheme.primary,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(100.dp),
                    description = "Relative whole-home power demand over the latest ${recentPoints.size} readings."
                )
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text("Earlier", style = MaterialTheme.typography.labelSmall)
                    Text("Now", style = MaterialTheme.typography.labelSmall)
                }
                Text(
                    text = "Peak in this chart · ${peakKw.energyFormat()} kW",
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.primary
                )
            }
        }
    }
}

@Composable
private fun SampleBars(
    values: List<Float>,
    color: Color,
    modifier: Modifier = Modifier,
    chartDescription: String
) {
    Canvas(
        modifier = modifier.semantics { contentDescription = chartDescription }
    ) {
        val gap = size.width / (values.size * 1.65f)
        val barWidth = gap * 0.65f
        val fullGroup = size.width / values.size
        values.forEachIndexed { index, value ->
            val height = size.height * value.coerceIn(0.08f, 1f)
            drawRoundRect(
                color = color,
                topLeft = Offset(x = fullGroup * index + (fullGroup - barWidth) / 2, y = size.height - height),
                size = Size(width = barWidth, height = height),
                cornerRadius = CornerRadius(x = barWidth / 2, y = barWidth / 2)
            )
        }
    }
}

@Composable
private fun TrendLine(
    values: List<Float>,
    lineColor: Color,
    modifier: Modifier = Modifier,
    description: String
) {
    Canvas(
        modifier = modifier.semantics { contentDescription = description }
    ) {
        if (values.size < 2) return@Canvas
        val path = Path()
        values.forEachIndexed { index, value ->
            val x = size.width * index / (values.size - 1)
            val y = size.height * (1f - value.coerceIn(0.05f, 0.95f))
            if (index == 0) path.moveTo(x, y) else path.lineTo(x, y)
        }
        drawPath(
            path = path,
            color = lineColor,
            style = Stroke(width = 3.dp.toPx(), cap = StrokeCap.Round)
        )
        val end = values.last().coerceIn(0.05f, 0.95f)
        drawCircle(
            color = lineColor,
            radius = 4.dp.toPx(),
            center = Offset(x = size.width, y = size.height * (1f - end))
        )
    }
}

@Composable
internal fun InsightPreviewCard(
    title: String,
    label: String,
    description: String,
    icon: ImageVector,
    modifier: Modifier = Modifier,
    mascotPose: AliPose? = null
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp)
    ) {
        Row(
            modifier = Modifier.padding(18.dp),
            horizontalArrangement = Arrangement.spacedBy(14.dp),
            verticalAlignment = Alignment.Top
        ) {
            if (mascotPose != null) {
                AliMascotIllustration(
                    pose = mascotPose,
                    modifier = Modifier.size(56.dp)
                )
            } else {
                Surface(
                    modifier = Modifier.size(44.dp),
                    shape = RoundedCornerShape(14.dp),
                    color = MaterialTheme.colorScheme.primary
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Icon(
                            imageVector = icon,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.onPrimary,
                            modifier = Modifier.size(22.dp)
                        )
                    }
                }
            }
            Column(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(5.dp)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = title,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.weight(1f)
                    )
                    PreviewBadge(label = label)
                }
                Text(
                    text = description,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

@Composable
internal fun QuickLessonCard(onClick: () -> Unit) {
    Card(
        onClick = onClick,
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp)
    ) {
        Row(
            modifier = Modifier.padding(18.dp),
            horizontalArrangement = Arrangement.spacedBy(14.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            AliMascotIllustration(
                pose = AliPose.Learning,
                modifier = Modifier.size(64.dp)
            )
            Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(
                    text = "Quick lesson",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onPrimaryContainer
                )
                Text(
                    text = "Standby power · 5 questions",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onPrimaryContainer
                )
            }
            Icon(
                imageVector = Icons.AutoMirrored.Filled.ArrowForward,
                contentDescription = "Open daily challenge",
                tint = MaterialTheme.colorScheme.onPrimaryContainer
            )
        }
    }
}

@Composable
internal fun LearningStatsRow(streak: Int, xp: Int) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        AliMascotIllustration(
            pose = AliPose.Welcome,
            modifier = Modifier.size(66.dp),
            motion = AliMotion.Idle
        )
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Surface(shape = RoundedCornerShape(18.dp), color = MaterialTheme.colorScheme.surfaceVariant) {
                Row(
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text("🔥", style = MaterialTheme.typography.titleMedium)
                    Text("$streak", fontWeight = FontWeight.ExtraBold, color = MaterialTheme.colorScheme.onSurface)
                }
            }
            Surface(shape = RoundedCornerShape(18.dp), color = MaterialTheme.colorScheme.surfaceVariant) {
                Row(
                    modifier = Modifier.padding(horizontal = 10.dp, vertical = 8.dp),
                    horizontalArrangement = Arrangement.spacedBy(5.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Image(
                        painter = painterResource(R.drawable.silip_energy_token),
                        contentDescription = null,
                        contentScale = ContentScale.Fit,
                        modifier = Modifier.size(22.dp)
                    )
                    Text("$xp XP", fontWeight = FontWeight.ExtraBold, color = MaterialTheme.colorScheme.onSurface)
                }
            }
        }
    }
}

@Composable
internal fun LearningUnitBanner(completed: Int, total: Int) {
    val progress = if (total > 0) completed.toFloat() / total else 0f
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(22.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primary),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier.padding(horizontal = 18.dp, vertical = 16.dp),
            verticalArrangement = Arrangement.spacedBy(9.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    Text(
                        text = "UNIT 1 · ENERGY BASICS",
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.ExtraBold,
                        color = MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.72f)
                    )
                    Text(
                        text = "Know your home",
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.ExtraBold,
                        color = MaterialTheme.colorScheme.onPrimary
                    )
                }
                Column(horizontalAlignment = Alignment.End) {
                    Text(
                        text = "$completed/$total",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.ExtraBold,
                        color = MaterialTheme.colorScheme.onPrimary
                    )
                    Text(
                        text = "PREVIEW",
                        style = MaterialTheme.typography.labelSmall,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.7f)
                    )
                }
            }
            LinearProgressIndicator(
                progress = { progress },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(8.dp)
                    .clip(CircleShape),
                color = MaterialTheme.colorScheme.primaryContainer,
                trackColor = MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.18f)
            )
        }
    }
}

private sealed interface LearningPathStop {
    data class LessonStop(
        val lesson: Lesson,
        val isCurrent: Boolean,
        val isCompleted: Boolean,
        val isUnlocked: Boolean
    ) : LearningPathStop
    data class RewardStop(
        val title: String,
        val drawableRes: Int,
        val isUnlocked: Boolean
    ) : LearningPathStop
}

@Composable
internal fun LearningMap(
    lessons: List<Lesson>,
    completedLessons: Int,
    onStart: (Lesson) -> Unit
) {
    val stops = buildList<LearningPathStop> {
        lessons.forEachIndexed { index, lesson ->
            add(
                LearningPathStop.LessonStop(
                    lesson = lesson,
                    isCurrent = index == completedLessons,
                    isCompleted = index < completedLessons,
                    isUnlocked = index <= completedLessons
                )
            )
            if (index == 1) {
                add(
                    LearningPathStop.RewardStop(
                        title = "Bonus chest",
                        drawableRes = R.drawable.silip_reward_chest,
                        isUnlocked = completedLessons >= 2
                    )
                )
            }
            if (index == 2) {
                add(
                    LearningPathStop.RewardStop(
                        title = "Energy bonus",
                        drawableRes = R.drawable.silip_energy_token,
                        isUnlocked = completedLessons >= 3
                    )
                )
            }
        }
        add(
            LearningPathStop.RewardStop(
                title = "Unit trophy",
                drawableRes = R.drawable.silip_trophy,
                isUnlocked = completedLessons >= lessons.size
            )
        )
    }
    val mapPositions = listOf(0.08f, 0.62f, 0.39f, 0.08f, 0.47f, 0.63f, 0.34f)
    val rowHeight = 144.dp
    val itemWidth = 152.dp
    val nodeSize = 78.dp
    val mapLine = MaterialTheme.colorScheme.primary
    val mapHighlight = MaterialTheme.colorScheme.primaryContainer

    BoxWithConstraints(
        modifier = Modifier
            .fillMaxWidth()
            .height(rowHeight * stops.size)
    ) {
        Canvas(modifier = Modifier.fillMaxSize()) {
            val itemWidthPx = itemWidth.toPx()
            val maxX = (size.width - itemWidthPx).coerceAtLeast(0f)
            val centers = stops.indices.map { index ->
                Offset(
                    x = maxX * mapPositions[index % mapPositions.size] + itemWidthPx / 2f,
                    y = rowHeight.toPx() * index + nodeSize.toPx() / 2f
                )
            }
            val path = Path().apply {
                centers.forEachIndexed { index, point ->
                    if (index == 0) {
                        moveTo(point.x, point.y)
                    } else {
                        val previous = centers[index - 1]
                        cubicTo(
                            previous.x,
                            previous.y + rowHeight.toPx() * 0.36f,
                            point.x,
                            point.y - rowHeight.toPx() * 0.36f,
                            point.x,
                            point.y
                        )
                    }
                }
            }
            drawPath(
                path = path,
                color = mapHighlight,
                style = Stroke(width = 18.dp.toPx(), cap = StrokeCap.Round)
            )
            drawPath(
                path = path,
                color = mapLine.copy(alpha = 0.42f),
                style = Stroke(width = 5.dp.toPx(), cap = StrokeCap.Round)
            )
        }

        stops.forEachIndexed { index, stop ->
            val position = mapPositions[index % mapPositions.size]
            val x = ((maxWidth - itemWidth) * position).coerceAtLeast(0.dp)
            val y = rowHeight * index
            Column(
                modifier = Modifier
                    .offset(x = x, y = y)
                    .width(itemWidth),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                when (stop) {
                    is LearningPathStop.LessonStop -> LearningLessonNode(
                        lesson = stop.lesson,
                        isCurrent = stop.isCurrent,
                        isCompleted = stop.isCompleted,
                        isUnlocked = stop.isUnlocked,
                        nodeSize = nodeSize,
                        onClick = { onStart(stop.lesson) }
                    )
                    is LearningPathStop.RewardStop -> LearningRewardNode(
                        stop = stop,
                        nodeSize = nodeSize
                    )
                }
            }
        }
    }
}

@Composable
private fun LearningLessonNode(
    lesson: Lesson,
    isCurrent: Boolean,
    isCompleted: Boolean,
    isUnlocked: Boolean,
    nodeSize: androidx.compose.ui.unit.Dp,
    onClick: () -> Unit
) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Box(
            modifier = Modifier
                .size(nodeSize)
                .clickable(enabled = isUnlocked, onClick = onClick),
            contentAlignment = Alignment.Center
        ) {
            Image(
                painter = painterResource(R.drawable.silip_energy_token),
                contentDescription = lesson.title,
                contentScale = ContentScale.Fit,
                modifier = Modifier
                    .size(nodeSize)
                    .graphicsLayer { alpha = if (isUnlocked) 1f else 0.45f }
            )
            if (!isUnlocked) {
                Surface(
                    modifier = Modifier
                        .align(Alignment.BottomEnd)
                        .padding(4.dp)
                        .size(25.dp),
                    shape = CircleShape,
                    color = MaterialTheme.colorScheme.surface
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Icon(
                            imageVector = Icons.Outlined.Lock,
                            contentDescription = "Locked lesson",
                            tint = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.size(15.dp)
                        )
                    }
                }
            } else if (isCompleted) {
                Surface(
                    modifier = Modifier
                        .align(Alignment.BottomEnd)
                        .padding(4.dp)
                        .size(25.dp),
                    shape = CircleShape,
                    color = MaterialTheme.colorScheme.primary
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Text(
                            text = "✓",
                            style = MaterialTheme.typography.labelLarge,
                            fontWeight = FontWeight.ExtraBold,
                            color = MaterialTheme.colorScheme.onPrimary
                        )
                    }
                }
            }
        }
        Surface(
            shape = RoundedCornerShape(8.dp),
            color = MaterialTheme.colorScheme.background
        ) {
            Text(
                text = lesson.title,
                style = MaterialTheme.typography.labelLarge,
                fontWeight = FontWeight.ExtraBold,
                color = if (isCurrent || isCompleted) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface,
                maxLines = 1,
                modifier = Modifier.padding(horizontal = 4.dp, vertical = 2.dp)
            )
        }
        if (isCompleted) {
            Text(
                text = "${lesson.points} XP earned",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.primary
            )
            Surface(
                shape = RoundedCornerShape(50),
                color = MaterialTheme.colorScheme.primaryContainer
            ) {
                Text(
                    text = "RETAKE",
                    style = MaterialTheme.typography.labelSmall,
                    fontWeight = FontWeight.ExtraBold,
                    color = MaterialTheme.colorScheme.onPrimaryContainer,
                    modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp)
                )
            }
        } else if (isCurrent) {
            Text(
                text = "5 questions · +${lesson.points} XP",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Surface(
                shape = RoundedCornerShape(50),
                color = MaterialTheme.colorScheme.primary
            ) {
                Text(
                    text = "START",
                    style = MaterialTheme.typography.labelSmall,
                    fontWeight = FontWeight.ExtraBold,
                    color = MaterialTheme.colorScheme.onPrimary,
                    modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp)
                )
            }
        }
    }
}

@Composable
private fun LearningRewardNode(stop: LearningPathStop.RewardStop, nodeSize: androidx.compose.ui.unit.Dp) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Box(
            modifier = Modifier.size(nodeSize),
            contentAlignment = Alignment.Center
        ) {
            Image(
                painter = painterResource(stop.drawableRes),
                contentDescription = null,
                contentScale = ContentScale.Fit,
                modifier = Modifier
                    .size(74.dp)
                    .graphicsLayer { alpha = if (stop.isUnlocked) 1f else 0.48f }
            )
            if (!stop.isUnlocked) {
                Surface(
                    modifier = Modifier
                        .align(Alignment.BottomEnd)
                        .padding(3.dp)
                        .size(24.dp),
                    shape = CircleShape,
                    color = MaterialTheme.colorScheme.surface
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Icon(
                            imageVector = Icons.Outlined.Lock,
                            contentDescription = "Locked reward",
                            tint = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.size(14.dp)
                        )
                    }
                }
            }
        }
        Surface(
            shape = RoundedCornerShape(8.dp),
            color = MaterialTheme.colorScheme.background
        ) {
            Text(
                text = stop.title,
                style = MaterialTheme.typography.labelLarge,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onSurface,
                maxLines = 1,
                modifier = Modifier.padding(horizontal = 4.dp, vertical = 2.dp)
            )
        }
    }
}

@Composable
internal fun ChallengeAnswerCard(
    text: String,
    selected: Boolean,
    enabled: Boolean,
    onClick: () -> Unit
) {
    val selectedColor = MaterialTheme.colorScheme.primaryContainer
    Card(
        onClick = onClick,
        enabled = enabled,
        modifier = Modifier
            .fillMaxWidth()
            .border(
                width = if (selected) 2.dp else 1.dp,
                color = if (selected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outlineVariant,
                shape = RoundedCornerShape(20.dp)
            ),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(
            containerColor = if (selected) selectedColor else MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp)
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.bodyLarge,
            color = if (selected) MaterialTheme.colorScheme.onPrimaryContainer else MaterialTheme.colorScheme.onSurface,
            modifier = Modifier.padding(horizontal = 18.dp, vertical = 16.dp)
        )
    }
}

@Composable
internal fun ChallengeFeedbackCard(isCorrect: Boolean, explanation: String) {
    val pose = if (isCorrect) AliPose.Success else AliPose.Caution
    val title = if (isCorrect) "That’s right" else "Try another way"
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(
            containerColor = if (isCorrect) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.tertiaryContainer
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp)
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            AliMascotIllustration(
                pose = pose,
                modifier = Modifier.size(72.dp),
                motion = if (isCorrect) AliMotion.Celebrate else AliMotion.Still
            )
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(
                    text = title,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    text = explanation,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface
                )
            }
        }
    }
}

@Composable
internal fun GridResponseCard() {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(28.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primary),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp)
    ) {
        Column(
            modifier = Modifier.padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "GRID FLEX",
                    style = MaterialTheme.typography.labelLarge,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onPrimary
                )
                PreviewBadge(
                    label = "Concept",
                    containerColor = MaterialTheme.colorScheme.primaryContainer,
                    contentColor = MaterialTheme.colorScheme.onPrimaryContainer
                )
            }
            Row(
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                AliMascotIllustration(
                    pose = AliPose.Success,
                    modifier = Modifier.size(72.dp),
                    motion = AliMotion.Idle
                )
                Column(
                    modifier = Modifier.weight(1f),
                    verticalArrangement = Arrangement.spacedBy(5.dp)
                ) {
                    Text(
                        text = "Lower peak demand.",
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onPrimary
                    )
                    Text(
                        text = "A future event could reward lower peak use.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onPrimary
                    )
                }
            }
            Text(
                text = "No live events or payouts",
                style = MaterialTheme.typography.labelMedium,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.88f)
            )
        }
    }
}

@Composable
internal fun GridParticipationSteps() {
    val steps = listOf(
        "Meralco sends an event",
        "Choose what to reduce",
        "Sensor checks usage",
        "Partner confirms rewards"
    )
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp)
    ) {
        Column(
            modifier = Modifier.padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Text(
                text = "How it works",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold
            )
            steps.forEachIndexed { index, step ->
                Row(
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Surface(
                        modifier = Modifier.size(30.dp),
                        shape = CircleShape,
                        color = MaterialTheme.colorScheme.primary
                    ) {
                        Box(contentAlignment = Alignment.Center) {
                            Text(
                                text = (index + 1).toString(),
                                style = MaterialTheme.typography.labelLarge,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.onPrimary
                            )
                        }
                    }
                    Text(
                        text = step,
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                }
            }
        }
    }
}
