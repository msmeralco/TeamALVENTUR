package com.alventur.silipapp.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

private val LightColors = lightColorScheme(
    primary = Forest,
    onPrimary = Paper,
    primaryContainer = Sage,
    onPrimaryContainer = Charcoal,
    secondary = Forest,
    onSecondary = Paper,
    secondaryContainer = Sage,
    onSecondaryContainer = Charcoal,
    tertiary = AlertOrange,
    onTertiary = Paper,
    tertiaryContainer = AlertSurface,
    onTertiaryContainer = Charcoal,
    error = AlertOrange,
    onError = Paper,
    errorContainer = AlertSurface,
    onErrorContainer = Charcoal,
    background = Paper,
    onBackground = Charcoal,
    surface = Color.White,
    onSurface = Charcoal,
    surfaceVariant = Sage,
    onSurfaceVariant = Charcoal,
    outline = Moss,
    outlineVariant = Moss,
    surfaceTint = Forest
)

private val DarkColors = darkColorScheme(
    primary = Sage,
    onPrimary = Charcoal,
    primaryContainer = Forest,
    onPrimaryContainer = Paper,
    secondary = Sage,
    onSecondary = Charcoal,
    secondaryContainer = NightSurfaceVariant,
    onSecondaryContainer = Paper,
    tertiary = NightAlert,
    onTertiary = Charcoal,
    tertiaryContainer = NightAlertSurface,
    onTertiaryContainer = Paper,
    error = NightAlert,
    onError = Charcoal,
    errorContainer = NightAlertSurface,
    onErrorContainer = Paper,
    background = Charcoal,
    onBackground = Paper,
    surface = NightSurface,
    onSurface = Paper,
    surfaceVariant = NightSurfaceVariant,
    onSurfaceVariant = Sage,
    outline = NightOutline,
    outlineVariant = NightOutline,
    surfaceTint = Sage
)

// Learn retains its original palette and illustrations.
private val OriginalLightColors = LightColors.copy(
    primary = Color(0xFF254E21), onPrimary = Color(0xFFF2EFE3),
    primaryContainer = Color(0xFFC3D2C5),
    secondary = Color(0xFF254E21), onSecondary = Color(0xFFF2EFE3),
    secondaryContainer = Color(0xFFC3D2C5), onTertiary = Color(0xFFF2EFE3),
    onError = Color(0xFFF2EFE3), background = Color(0xFFF2EFE3),
    surface = Color(0xFFF2EFE3), surfaceVariant = Color(0xFFC3D2C5),
    outline = Color(0xFF58815F), outlineVariant = Color(0xFF58815F),
    surfaceTint = Color(0xFF254E21)
)
private val OriginalDarkColors = DarkColors.copy(
    primary = Color(0xFFC3D2C5), primaryContainer = Color(0xFF254E21),
    onPrimaryContainer = Color(0xFFF2EFE3), secondary = Color(0xFFC3D2C5),
    onSecondaryContainer = Color(0xFFF2EFE3), onTertiaryContainer = Color(0xFFF2EFE3),
    onErrorContainer = Color(0xFFF2EFE3), onBackground = Color(0xFFF2EFE3),
    onSurface = Color(0xFFF2EFE3), onSurfaceVariant = Color(0xFFC3D2C5),
    surfaceTint = Color(0xFFC3D2C5)
)

private val SilipTypography = Typography(
    displaySmall = Typography().displaySmall.copy(
        fontFamily = FontFamily.Monospace,
        fontWeight = FontWeight.Bold
    ),
    headlineLarge = Typography().headlineLarge.copy(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Bold
    ),
    headlineMedium = Typography().headlineMedium.copy(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Bold
    ),
    headlineSmall = Typography().headlineSmall.copy(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Bold
    ),
    titleLarge = Typography().titleLarge.copy(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Bold
    ),
    titleMedium = Typography().titleMedium.copy(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.SemiBold
    ),
    bodyLarge = Typography().bodyLarge.copy(
        fontFamily = FontFamily.SansSerif,
        fontSize = 16.sp,
        lineHeight = 24.sp
    ),
    bodyMedium = Typography().bodyMedium.copy(
        fontFamily = FontFamily.SansSerif,
        fontSize = 16.sp,
        lineHeight = 23.sp
    ),
    bodySmall = Typography().bodySmall.copy(
        fontFamily = FontFamily.SansSerif,
        fontSize = 14.sp,
        lineHeight = 20.sp
    ),
    labelLarge = Typography().labelLarge.copy(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.SemiBold
    ),
    labelMedium = Typography().labelMedium.copy(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Medium
    )
)

@Composable
fun SilipTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    originalPalette: Boolean = false,
    content: @Composable () -> Unit
) {
    MaterialTheme(
        colorScheme = when {
            originalPalette && darkTheme -> OriginalDarkColors
            originalPalette -> OriginalLightColors
            darkTheme -> DarkColors
            else -> LightColors
        },
        typography = SilipTypography,
        content = content
    )
}
