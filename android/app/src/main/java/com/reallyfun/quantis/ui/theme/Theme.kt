package com.reallyfun.quantis.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val EditorialBackground = Color(0xFF0C0C0E)
private val EditorialSurface = Color(0xFF16161A)
private val EditorialAccent = Color(0xFFE8E4DC)
private val EditorialMuted = Color(0xFF8A8780)

private val QuantisColors =
    darkColorScheme(
        primary = EditorialAccent,
        onPrimary = EditorialBackground,
        secondary = EditorialMuted,
        background = EditorialBackground,
        surface = EditorialSurface,
        onBackground = EditorialAccent,
        onSurface = EditorialAccent,
        onSurfaceVariant = EditorialMuted,
    )

@Composable
fun QuantisTheme(content: @Composable () -> Unit) {
  MaterialTheme(
      colorScheme = QuantisColors,
      content = content,
  )
}
