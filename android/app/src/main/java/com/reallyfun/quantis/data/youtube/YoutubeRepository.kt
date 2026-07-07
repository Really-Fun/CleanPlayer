package com.reallyfun.quantis.data.youtube

import com.reallyfun.quantis.data.model.Track
import com.reallyfun.quantis.data.model.TrackSource
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.header
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.http.ContentType
import io.ktor.http.HttpHeaders
import io.ktor.http.contentType
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

@Serializable
private data class InnerTubeContext(
    val client: InnerTubeClient,
)

@Serializable
private data class InnerTubeClient(
    val clientName: String,
    val clientVersion: String,
    val hl: String = "ru",
    val gl: String = "RU",
)

@Serializable
private data class InnerTubeSearchBody(
    val context: InnerTubeContext,
    val query: String,
    val params: String = "EgWKAQIIAWoKEAMQBBAJEAoQBQ%3D%3D",
)

@Serializable
private data class InnerTubeBrowseBody(
    val context: InnerTubeContext,
    @SerialName("browseId") val browseId: String,
)

@Serializable
private data class InnerTubeNextBody(
    val context: InnerTubeContext,
    @SerialName("videoId") val videoId: String,
    @SerialName("playlistId") val playlistId: String,
)

@Serializable
private data class InnerTubePlayerBody(
    val context: InnerTubeContext,
    @SerialName("videoId") val videoId: String,
)

class YoutubeRepository(private val client: HttpClient) {
  private val json = Json { ignoreUnknownKeys = true }

  suspend fun search(query: String, limit: Int = 12): List<Track> {
    val body = InnerTubeSearchBody(context = MUSIC_CONTEXT, query = query)
    return collectTracks(json.parseToJsonElement(postInnerTube("search", body)), limit)
  }

  suspend fun getHomeTracks(limit: Int = 24): List<Track> {
    val body = InnerTubeBrowseBody(context = MUSIC_CONTEXT, browseId = "FEmusic_home")
    return collectTracks(json.parseToJsonElement(postInnerTube("browse", body)), limit)
  }

  suspend fun getWatchPlaylist(videoId: String, limit: Int = 15): List<Track> {
    val body =
        InnerTubeNextBody(
            context = MUSIC_CONTEXT,
            videoId = videoId,
            playlistId = "RDAMVM$videoId",
        )
    return collectTracks(json.parseToJsonElement(postInnerTube("next", body)), limit)
  }

  suspend fun getStreamUrl(videoId: String): String? {
    val body = InnerTubePlayerBody(context = ANDROID_CONTEXT, videoId = videoId)
    val responseText =
        postInnerTube(
            "player",
            body,
            clientName = ANDROID_CLIENT_NAME,
            clientVersion = ANDROID_CLIENT_VERSION,
        )

    val root = json.parseToJsonElement(responseText).jsonObject
    val streamingData = root["streamingData"]?.jsonObject ?: return null
    val formats =
        streamingData["adaptiveFormats"]?.jsonArray ?: streamingData["formats"]?.jsonArray
    formats?.forEach { format ->
      val obj = format.jsonObject
      val mime = obj["mimeType"]?.jsonPrimitive?.contentOrNull.orEmpty()
      if (!mime.startsWith("audio/")) return@forEach
      val url = obj["url"]?.jsonPrimitive?.contentOrNull
      if (!url.isNullOrBlank()) return url
    }
    return null
  }

  private fun collectTracks(root: JsonElement, limit: Int): List<Track> {
    val tracks = mutableListOf<Track>()
    val seen = mutableSetOf<String>()

    fun add(track: Track?) {
      if (track == null || track.key in seen || tracks.size >= limit) return
      seen += track.key
      tracks += track
    }

    fun walk(node: JsonElement) {
      if (tracks.size >= limit) return
      when (node) {
        is JsonObject -> {
          node["musicResponsiveListItemRenderer"]?.jsonObject?.let { add(parseListItem(it)) }
          node["playlistPanelVideoRenderer"]?.jsonObject?.let { add(parsePanelVideo(it)) }
          node.forEach { (_, value) -> walk(value) }
        }
        is JsonArray -> node.forEach { walk(it) }
        else -> Unit
      }
    }

    walk(root)
    return tracks
  }

  private suspend inline fun <reified T> postInnerTube(
      path: String,
      body: T,
      clientName: String = WEB_REMIX_CLIENT_NAME,
      clientVersion: String = WEB_REMIX_CLIENT_VERSION,
  ): String =
      client
          .post("$INNERTUBE_BASE/$path") {
            contentType(ContentType.Application.Json)
            header(HttpHeaders.Origin, MUSIC_ORIGIN)
            header(HttpHeaders.Referrer, "$MUSIC_ORIGIN/")
            header("X-YouTube-Client-Name", clientName)
            header("X-YouTube-Client-Version", clientVersion)
            setBody(body)
          }
          .body()

  private fun parseListItem(renderer: JsonObject): Track? {
    val videoId = renderer.flexColumnVideoId() ?: return null
    val title = renderer.flexColumnText(0) ?: return null
    val author = renderer.flexColumnText(1) ?: "Unknown"
    return Track(
        trackId = videoId,
        title = title,
        author = author,
        source = TrackSource.YOUTUBE,
    )
  }

  private fun parsePanelVideo(renderer: JsonObject): Track? {
    val videoId = renderer["videoId"]?.jsonPrimitive?.contentOrNull ?: return null
    val title =
        renderer["title"]?.jsonObject?.get("runs")?.jsonArray?.firstOrNull()?.jsonObject
            ?.get("text")?.jsonPrimitive?.contentOrNull
            ?: return null
    val author =
        renderer["longBylineText"]?.jsonObject?.get("runs")?.jsonArray?.firstOrNull()?.jsonObject
            ?.get("text")?.jsonPrimitive?.contentOrNull
            ?: renderer["shortBylineText"]?.jsonObject?.get("runs")?.jsonArray?.firstOrNull()
                ?.jsonObject?.get("text")?.jsonPrimitive?.contentOrNull
                ?: "Unknown"
    return Track(
        trackId = videoId,
        title = title,
        author = author,
        source = TrackSource.YOUTUBE,
    )
  }

  private fun JsonObject.flexColumnVideoId(): String? {
    val column = get("flexColumns")?.jsonArray?.firstOrNull()?.jsonObject ?: return null
    val runs =
        column["musicResponsiveListItemFlexColumnRenderer"]?.jsonObject?.get("text")?.jsonObject
            ?.get("runs")?.jsonArray
    val navigationEndpoint =
        runs?.firstOrNull()?.jsonObject?.get("navigationEndpoint")?.jsonObject
    return navigationEndpoint?.get("watchEndpoint")?.jsonObject?.get("videoId")?.jsonPrimitive
        ?.contentOrNull
  }

  private fun JsonObject.flexColumnText(index: Int): String? {
    val columns = get("flexColumns")?.jsonArray ?: return null
    if (index >= columns.size) return null
    val runs =
        columns[index].jsonObject["musicResponsiveListItemFlexColumnRenderer"]?.jsonObject
            ?.get("text")?.jsonObject?.get("runs")?.jsonArray
    return runs?.firstOrNull()?.jsonObject?.get("text")?.jsonPrimitive?.contentOrNull
  }

  companion object {
    private const val MUSIC_ORIGIN = "https://music.youtube.com"
    private const val INNERTUBE_BASE = "$MUSIC_ORIGIN/youtubei/v1"
    private const val WEB_REMIX_CLIENT_NAME = "67"
    private const val WEB_REMIX_CLIENT_VERSION = "1.20250218.01.00"
    private const val ANDROID_CLIENT_NAME = "3"
    private const val ANDROID_CLIENT_VERSION = "19.11.43"

    private val MUSIC_CONTEXT =
        InnerTubeContext(
            client =
                InnerTubeClient(
                    clientName = "WEB_REMIX",
                    clientVersion = WEB_REMIX_CLIENT_VERSION,
                ),
        )

    private val ANDROID_CONTEXT =
        InnerTubeContext(
            client =
                InnerTubeClient(
                    clientName = "ANDROID",
                    clientVersion = ANDROID_CLIENT_VERSION,
                ),
        )
  }
}
