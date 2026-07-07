package com.reallyfun.quantis.domain

import com.reallyfun.quantis.data.model.Track
import com.reallyfun.quantis.player.PlayerController
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope

class PlaybackCoordinator(
    private val musicRepository: MusicRepository,
    private val playerController: PlayerController,
) {
  suspend fun playTracks(tracks: List<Track>, startIndex: Int = 0) = coroutineScope {
    if (tracks.isEmpty()) return@coroutineScope

    val slice =
        tracks
            .drop(startIndex.coerceIn(0, tracks.lastIndex))
            .take(MAX_QUEUE_SIZE)

    val resolved =
        slice
            .map { track ->
              async {
                runCatching { musicRepository.streamUrl(track) }
                    .getOrNull()
                    ?.let { url -> track to url }
              }
            }
            .mapNotNull { it.await() }

    if (resolved.isEmpty()) {
      playerController.reportError("Не удалось получить поток")
      return@coroutineScope
    }

    playerController.playQueue(resolved, 0)
  }

  suspend fun playSingle(track: Track, queue: List<Track> = emptyList()) {
    if (queue.isEmpty()) {
      playTracks(listOf(track))
      return
    }
    val startIndex = queue.indexOfFirst { it.key == track.key }.coerceAtLeast(0)
    playTracks(queue, startIndex)
  }

  suspend fun playRadio(seed: Track) {
    val tracks = musicRepository.radioFromTrack(seed)
    if (tracks.isEmpty()) {
      playerController.reportError("Не удалось загрузить радио")
      return
    }
    playTracks(tracks)
  }

  companion object {
    private const val MAX_QUEUE_SIZE = 25
  }
}
