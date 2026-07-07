package com.reallyfun.quantis.ui.search

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.reallyfun.quantis.ui.components.TrackRow

@Composable
fun SearchScreen(
    viewModel: SearchViewModel,
    modifier: Modifier = Modifier,
) {
  val state by viewModel.state.collectAsState()

  Column(
      modifier = modifier.fillMaxSize().padding(horizontal = 16.dp, vertical = 12.dp),
      verticalArrangement = Arrangement.spacedBy(12.dp),
  ) {
    OutlinedTextField(
        value = state.query,
        onValueChange = viewModel::onQueryChange,
        modifier = Modifier.fillMaxWidth(),
        placeholder = { Text("Название, исполнитель…") },
        singleLine = true,
        trailingIcon = {
          IconButton(onClick = viewModel::search) {
            Icon(Icons.Default.Search, contentDescription = "Искать")
          }
        },
    )

    state.error?.let { error ->
      Text(text = error, color = MaterialTheme.colorScheme.error)
    }

    if (state.isLoading) {
      CircularProgressIndicator(modifier = Modifier.align(Alignment.CenterHorizontally))
    }

    LazyColumn(
        contentPadding = PaddingValues(bottom = 96.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
      items(state.tracks, key = { it.key }) { track ->
        TrackRow(
            track = track,
            isLoading = state.playingTrackId == track.key,
            onClick = { viewModel.play(track) },
            onLongClick = { viewModel.playRadio(track) },
        )
      }
    }
  }
}
