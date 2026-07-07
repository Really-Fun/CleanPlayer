package com.reallyfun.quantis.ui.home

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.reallyfun.quantis.ui.components.TrackRow

@Composable
fun HomeScreen(
    viewModel: HomeViewModel,
    modifier: Modifier = Modifier,
) {
  val state by viewModel.state.collectAsState()

  Column(
      modifier = modifier.fillMaxSize().padding(horizontal = 16.dp, vertical = 12.dp),
      verticalArrangement = Arrangement.spacedBy(8.dp),
  ) {
    Text(text = "Quantis", style = MaterialTheme.typography.headlineMedium)
    Text(
        text = "Рекомендации · YouTube Music",
        style = MaterialTheme.typography.bodyMedium,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
    Text(
        text = "Долгое нажатие — радио по треку",
        style = MaterialTheme.typography.bodySmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )

    state.error?.let { error ->
      Text(text = error, color = MaterialTheme.colorScheme.error)
    }

    if (state.isLoading && state.tracks.isEmpty()) {
      CircularProgressIndicator(modifier = Modifier.align(Alignment.CenterHorizontally))
    }

    LazyColumn(
        contentPadding = PaddingValues(bottom = 96.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
      items(state.tracks, key = { it.key }) { track ->
        TrackRow(
            track = track,
            isLoading = state.playingTrackId == track.key || state.radioTrackId == track.key,
            onClick = { viewModel.play(track) },
            onLongClick = { viewModel.playRadio(track) },
        )
      }
    }
  }
}
