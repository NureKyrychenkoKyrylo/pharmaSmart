package com.example.pharmasmart.ui.theme

import android.app.Activity
import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext

private val DarkColorScheme = darkColorScheme(
    primary = Jade80,
    secondary = TealGrey80,
    tertiary = Sky80,
    background = DarkSlate,
    surface = Color(0xFF202927),
    surfaceContainerLowest = Color(0xFF151D1B),
    onPrimary = DarkSlate,
    onSecondary = DarkSlate,
    onTertiary = DarkSlate,
)

private val LightColorScheme = lightColorScheme(
    primary = Jade40,
    secondary = TealGrey40,
    tertiary = Sky40,
    background = WarmBackground,
    surface = WarmSurface,
    surfaceContainerLowest = Color(0xFFF2F5F4),
    surfaceContainerHigh = Color(0xFFE7ECE9),
    primaryContainer = Color(0xFFC4EDDF),
    secondaryContainer = Color(0xFFD5E8E2),
    tertiaryContainer = Color(0xFFD8EAF8),
    error = SoftError,
)

@Composable
fun PharmasmartTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    // Dynamic color is available on Android 12+
    dynamicColor: Boolean = false,
    content: @Composable () -> Unit
) {
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        }

        darkTheme -> DarkColorScheme
        else -> LightColorScheme
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography,
        content = content
    )
}
