package com.alventur.silipapp.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

private val LightColors = lightColorScheme(
    primary = ForestGreen,
    onPrimary = PaperWhite,
    primaryContainer = SoftLeaf,
    onPrimaryContainer = DeepForest,
    secondary = SlateBlue,
    onSecondary = PaperWhite,
    secondaryContainer = SoftBlue,
    onSecondaryContainer = DeepSlate,
    tertiary = DeepAmber,
    onTertiary = PaperWhite,
    tertiaryContainer = SoftAmber,
    onTertiaryContainer = DeepAmber,
    error = DeepCoral,
    errorContainer = SoftCoral,
    onErrorContainer = DeepCoral,
    background = WarmPaper,
    onBackground = Ink,
    surface = PaperWhite,
    onSurface = Ink,
    surfaceVariant = androidx.compose.ui.graphics.Color(0xFFE8EEE8),
    onSurfaceVariant = MutedInk
)

private val DarkColors = darkColorScheme(
    primary = androidx.compose.ui.graphics.Color(0xFF8DD5A8),
    onPrimary = androidx.compose.ui.graphics.Color(0xFF003920),
    primaryContainer = androidx.compose.ui.graphics.Color(0xFF075132),
    onPrimaryContainer = androidx.compose.ui.graphics.Color(0xFFB3F0C7),
    secondary = androidx.compose.ui.graphics.Color(0xFFA4CEDD),
    onSecondary = androidx.compose.ui.graphics.Color(0xFF123540),
    secondaryContainer = androidx.compose.ui.graphics.Color(0xFF294D5A),
    onSecondaryContainer = androidx.compose.ui.graphics.Color(0xFFC0EAF8),
    tertiary = androidx.compose.ui.graphics.Color(0xFFE8CC79),
    onTertiary = androidx.compose.ui.graphics.Color(0xFF3D3000),
    tertiaryContainer = androidx.compose.ui.graphics.Color(0xFF574500),
    onTertiaryContainer = androidx.compose.ui.graphics.Color(0xFFFFE8A3),
    error = androidx.compose.ui.graphics.Color(0xFFFFB4A9),
    errorContainer = androidx.compose.ui.graphics.Color(0xFF5A211B),
    onErrorContainer = androidx.compose.ui.graphics.Color(0xFFFFDAD4),
    background = NightBackground,
    onBackground = NightInk,
    surface = NightSurface,
    onSurface = NightInk,
    surfaceVariant = NightSurfaceVariant,
    onSurfaceVariant = NightMutedInk
)

@Composable
fun SilipTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    MaterialTheme(
        colorScheme = if (darkTheme) DarkColors else LightColors,
        content = content
    )
}
