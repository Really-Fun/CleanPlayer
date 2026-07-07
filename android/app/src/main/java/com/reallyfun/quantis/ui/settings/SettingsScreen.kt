package com.reallyfun.quantis.ui.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun SettingsScreen(
    viewModel: SettingsViewModel,
    modifier: Modifier = Modifier,
) {
  val state by viewModel.state.collectAsState()

  Column(
      modifier = modifier.fillMaxSize().padding(16.dp),
      verticalArrangement = Arrangement.spacedBy(12.dp),
  ) {
    Text(
        text = "Настройки",
        style = MaterialTheme.typography.headlineSmall,
    )
    Text(
        text = "OAuth-токен Яндекс.Музыки. Без него поиск и воспроизведение работают только через YouTube.",
        style = MaterialTheme.typography.bodyMedium,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
    OutlinedTextField(
        value = state.yandexToken,
        onValueChange = viewModel::onTokenChange,
        modifier = Modifier.fillMaxWidth(),
        label = { Text("Yandex OAuth token") },
        singleLine = false,
        minLines = 2,
    )
    Button(onClick = viewModel::save) {
      Text(if (state.saved) "Сохранено" else "Сохранить")
    }
  }
}
