package com.reallyfun.quantis.player

import android.content.ComponentName
import android.content.Context
import android.content.Intent
import androidx.core.content.ContextCompat
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.session.MediaController
import androidx.media3.session.SessionToken
import com.google.common.util.concurrent.ListenableFuture
import com.google.common.util.concurrent.MoreExecutors
import com.reallyfun.quantis.data.model.Track
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

data class PlayerUiState(
    val currentTrack: Track? = null,
    val isPlaying: Boolean = false,
    val isBuffering: Boolean = false,
    val hasNext: Boolean = false,
    val hasPrevious: Boolean = false,
    val error: String? = null,
)

class PlayerController(private val context: Context) {
  private var controllerFuture: ListenableFuture<MediaController>? = null
  private var mediaController: MediaController? = null

  private val _state = MutableStateFlow(PlayerUiState())
  val state: StateFlow<PlayerUiState> = _state.asStateFlow()

  private val playerListener =
      object : Player.Listener {
        override fun onIsPlayingChanged(isPlaying: Boolean) {
          _state.update { it.copy(isPlaying = isPlaying) }
        }

        override fun onPlaybackStateChanged(playbackState: Int) {
          _state.update {
            it.copy(isBuffering = playbackState == Player.STATE_BUFFERING)
          }
        }

        override fun onMediaItemTransition(mediaItem: MediaItem?, reason: Int) {
          val track = mediaItem?.let(MediaItemFactory::trackFromMediaItem)
          val controller = mediaController
          _state.update {
            it.copy(
                currentTrack = track,
                hasNext = controller?.hasNextMediaItem() == true,
                hasPrevious = controller?.hasPreviousMediaItem() == true,
            )
          }
        }
      }

  init {
    connect()
  }

  private fun connect() {
    ContextCompat.startForegroundService(context, Intent(context, PlaybackService::class.java))
    val sessionToken =
        SessionToken(context, ComponentName(context, PlaybackService::class.java))
    controllerFuture = MediaController.Builder(context, sessionToken).buildAsync()
    controllerFuture?.addListener(
        {
          mediaController =
              controllerFuture?.get()?.also { controller ->
                controller.addListener(playerListener)
                syncState(controller)
              }
        },
        MoreExecutors.directExecutor(),
    )
  }

  private fun syncState(controller: MediaController) {
    val track =
        controller.currentMediaItem?.let(MediaItemFactory::trackFromMediaItem)
    _state.update {
      it.copy(
          currentTrack = track,
          isPlaying = controller.isPlaying,
          isBuffering = controller.playbackState == Player.STATE_BUFFERING,
          hasNext = controller.hasNextMediaItem(),
          hasPrevious = controller.hasPreviousMediaItem(),
      )
    }
  }

  fun playQueue(entries: List<Pair<Track, String>>, startIndex: Int = 0) {
    val controller = mediaController ?: return
    if (entries.isEmpty()) return

    val items = entries.map { (track, url) -> MediaItemFactory.fromTrack(track, url) }
    val index = startIndex.coerceIn(0, items.lastIndex)
    controller.setMediaItems(items, index, 0)
    controller.prepare()
    controller.play()
    _state.update {
      it.copy(
          currentTrack = entries[index].first,
          error = null,
          hasNext = index < items.lastIndex,
          hasPrevious = index > 0,
      )
    }
  }

  fun togglePlayPause() {
    val controller = mediaController ?: return
    if (controller.isPlaying) {
      controller.pause()
    } else {
      controller.play()
    }
  }

  fun skipToNext() {
    mediaController?.seekToNextMediaItem()
  }

  fun skipToPrevious() {
    mediaController?.seekToPreviousMediaItem()
  }

  fun reportError(message: String) {
    _state.update { it.copy(error = message) }
  }

  fun release() {
    mediaController?.removeListener(playerListener)
    MediaController.releaseFuture(controllerFuture ?: return)
    controllerFuture = null
    mediaController = null
  }
}
