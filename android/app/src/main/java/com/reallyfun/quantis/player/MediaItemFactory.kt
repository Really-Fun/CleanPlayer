package com.reallyfun.quantis.player

import android.os.Bundle
import androidx.media3.common.MediaItem
import androidx.media3.common.MediaMetadata
import com.reallyfun.quantis.data.model.Track
import com.reallyfun.quantis.data.model.TrackSource

object MediaItemFactory {
  private const val EXTRA_SOURCE = "quantis_source"

  fun fromTrack(track: Track, streamUrl: String): MediaItem =
      MediaItem.Builder()
          .setUri(streamUrl)
          .setMediaId(track.key)
          .setMediaMetadata(
              MediaMetadata.Builder()
                  .setTitle(track.title)
                  .setArtist(track.author)
                  .setExtras(
                      Bundle().apply {
                        putString(EXTRA_SOURCE, track.source.value)
                        putString("track_id", track.trackId)
                      },
                  )
                  .build(),
          )
          .build()

  fun trackFromMediaItem(item: MediaItem): Track? {
    val metadata = item.mediaMetadata
    val extras = metadata.extras ?: return null
    val source =
        TrackSource.from(extras.getString(EXTRA_SOURCE).orEmpty()) ?: return null
    val trackId = extras.getString("track_id") ?: item.mediaId.substringAfter(':')
    val title = metadata.title?.toString() ?: return null
    val author = metadata.artist?.toString() ?: ""
    return Track(
        trackId = trackId,
        title = title,
        author = author,
        source = source,
    )
  }
}
