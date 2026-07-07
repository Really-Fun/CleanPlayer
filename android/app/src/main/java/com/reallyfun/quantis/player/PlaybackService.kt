package com.reallyfun.quantis.player

import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.session.MediaSession
import androidx.media3.session.MediaSessionService

class PlaybackService : MediaSessionService() {
  private var player: ExoPlayer? = null
  private var mediaSession: MediaSession? = null

  override fun onCreate() {
    super.onCreate()
    val exoPlayer = ExoPlayer.Builder(this).build()
    player = exoPlayer
    mediaSession = MediaSession.Builder(this, exoPlayer).build()
  }

  override fun onGetSession(controllerInfo: MediaSession.ControllerInfo): MediaSession? =
      mediaSession

  override fun onDestroy() {
    mediaSession?.run {
      player.release()
      release()
    }
    mediaSession = null
    player = null
    super.onDestroy()
  }
}
