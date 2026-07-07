package com.reallyfun.quantis.ui.components

import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.clickable
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.reallyfun.quantis.data.model.Track

@OptIn(ExperimentalFoundationApi::class)
@Composable
fun TrackRow(
    track: Track,
    isLoading: Boolean,
    onClick: () -> Unit,
    onLongClick: (() -> Unit)? = null,
    modifier: Modifier = Modifier,
) {
  val interactionModifier =
      if (onLongClick != null) {
        Modifier.combinedClickable(
            enabled = !isLoading,
            onClick = onClick,
            onLongClick = onLongClick,
        )
      } else {
        Modifier.clickable(enabled = !isLoading, onClick = onClick)
      }

  Column(
      modifier = modifier.fillMaxWidth().then(interactionModifier).padding(vertical = 10.dp),
  ) {
    Text(
        text = track.title,
        style = MaterialTheme.typography.titleMedium,
        maxLines = 1,
        overflow = TextOverflow.Ellipsis,
    )
    Text(
        text = "${track.author} · ${track.source.value}",
        style = MaterialTheme.typography.bodySmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        maxLines = 1,
        overflow = TextOverflow.Ellipsis,
    )
    if (isLoading) {
      CircularProgressIndicator(modifier = Modifier.padding(top = 6.dp))
    }
  }
}
