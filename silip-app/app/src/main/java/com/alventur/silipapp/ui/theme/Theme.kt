package com.alventur.silipapp.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
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
    surface = Paper,
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
    content: @Composable () -> Unit
) {
    MaterialTheme(
        colorScheme = if (darkTheme) DarkColors else LightColors,
        typography = SilipTypography,
        content = content
    )
}
