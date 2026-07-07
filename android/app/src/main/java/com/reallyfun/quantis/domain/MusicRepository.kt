package com.reallyfun.quantis.domain

import com.reallyfun.quantis.data.model.Track
import com.reallyfun.quantis.data.model.TrackSource
import com.reallyfun.quantis.data.prefs.TokenStore
import com.reallyfun.quantis.data.yandex.YandexRepository
import com.reallyfun.quantis.data.youtube.YoutubeRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.first

class MusicRepository(
    private val tokenStore: TokenStore,
    private val yandex: YandexRepository,
    private val youtube: YoutubeRepository,
) {
  suspend fun search(query: String, perSource: Int = 12): List<Track> = coroutineScope {
    val token = tokenStore.yandexToken.first()
    val yandexDeferred = async {
      if (token.isNullOrBlank()) {
        emptyList()
      } else {
        runCatching { yandex.search(token, query, perSource) }.getOrElse { emptyList() }
      }
    }
    val youtubeDeferred = async {
      runCatching { youtube.search(query, perSource) }.getOrElse { emptyList() }
    }
    yandexDeferred.await() + youtubeDeferred.await()
  }

  suspend fun homeRecommendations(limit: Int = 24): List<Track> =
      runCatching { youtube.getHomeTracks(limit) }.getOrElse { emptyList() }

  suspend fun radioFromTrack(seed: Track): List<Track> {
    val videoId =
        when (seed.source) {
          TrackSource.YOUTUBE -> seed.trackId
          TrackSource.YANDEX -> {
            search("${seed.title} ${seed.author}", perSource = 3)
                .firstOrNull { it.source == TrackSource.YOUTUBE }
                ?.trackId
                ?: return emptyList()
          }
        }
    return runCatching { youtube.getWatchPlaylist(videoId) }.getOrElse { emptyList() }
  }

  suspend fun streamUrl(track: Track): String? {
    return when (track.source) {
      TrackSource.YANDEX -> {
        val token = tokenStore.yandexToken.first() ?: return null
        yandex.getStreamUrl(token, track.trackId)
      }
      TrackSource.YOUTUBE -> youtube.getStreamUrl(track.trackId)
    }
  }
}
