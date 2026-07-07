package com.reallyfun.quantis.data.yandex

import com.reallyfun.quantis.data.model.Track
import com.reallyfun.quantis.data.model.TrackSource
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get
import io.ktor.client.request.header
import io.ktor.client.request.parameter
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
private data class YandexSearchResponse(
    val result: YandexSearchResult? = null,
)

@Serializable
private data class YandexSearchResult(
    val tracks: YandexTracksBlock? = null,
)

@Serializable
private data class YandexTracksBlock(
    val results: List<YandexTrackDto> = emptyList(),
)

@Serializable
private data class YandexTrackDto(
    val id: Long,
    val title: String,
    val artists: List<YandexArtistDto> = emptyList(),
)

@Serializable
private data class YandexArtistDto(
    val name: String? = null,
)

@Serializable
private data class YandexTracksResponse(
    val result: List<YandexTrackDto> = emptyList(),
)

@Serializable
private data class YandexDownloadInfoResponse(
    val result: List<YandexDownloadInfoDto> = emptyList(),
)

@Serializable
private data class YandexDownloadInfoDto(
    @SerialName("downloadInfoUrl") val downloadInfoUrl: String? = null,
)

class YandexRepository(private val client: HttpClient) {
  suspend fun search(token: String, query: String, limit: Int = 12): List<Track> {
    val response: YandexSearchResponse =
        client.get("$BASE_URL/search") {
          header("Authorization", "OAuth $token")
          parameter("text", query)
          parameter("type", "track")
          parameter("page", 0)
          parameter("nocorrect", false)
        }.body()

    return response.result?.tracks?.results.orEmpty().take(limit).map { dto ->
      Track(
          trackId = dto.id.toString(),
          title = dto.title,
          author = dto.artists.mapNotNull { it.name }.joinToString(" & "),
          source = TrackSource.YANDEX,
      )
    }
  }

  suspend fun getStreamUrl(token: String, trackId: String): String? {
    val tracks: YandexTracksResponse =
        client.get("$BASE_URL/tracks") {
          header("Authorization", "OAuth $token")
          parameter("track-ids", trackId)
        }.body()

    val track = tracks.result.firstOrNull() ?: return null
    val downloadInfo: YandexDownloadInfoResponse =
        client.get("$BASE_URL/tracks/${track.id}/download-info") {
          header("Authorization", "OAuth $token")
        }.body()

    val infoUrl = downloadInfo.result.firstOrNull()?.downloadInfoUrl ?: return null
    return resolveDirectLink(infoUrl)
  }

  private suspend fun resolveDirectLink(downloadInfoUrl: String): String? {
    val xml: String = client.get(downloadInfoUrl).body()
    val host = XML_TAG.find(xml, "host") ?: return null
    val path = XML_TAG.find(xml, "path") ?: return null
    val ts = XML_TAG.find(xml, "ts") ?: return null
    val sign = XML_TAG.find(xml, "s") ?: return null
    return "https://$host/get-mp3/$sign/$ts$path"
  }

  companion object {
    private const val BASE_URL = "https://api.music.yandex.net"
    private val XML_TAG = Regex("<(\\w+)>([^<]+)</\\1>")

    private fun Regex.find(xml: String, tag: String): String? =
        findAll(xml).firstOrNull { it.groupValues[1] == tag }?.groupValues?.get(2)
  }
}
