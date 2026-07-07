package com.reallyfun.quantis

import android.app.Application
import com.reallyfun.quantis.data.network.HttpClients
import com.reallyfun.quantis.data.prefs.TokenStore
import com.reallyfun.quantis.data.yandex.YandexRepository
import com.reallyfun.quantis.data.youtube.YoutubeRepository
import com.reallyfun.quantis.domain.MusicRepository
import com.reallyfun.quantis.domain.PlaybackCoordinator
import com.reallyfun.quantis.player.PlayerController

class QuantisApplication : Application() {
  lateinit var musicRepository: MusicRepository
    private set

  lateinit var playbackCoordinator: PlaybackCoordinator
    private set

  lateinit var playerController: PlayerController
    private set

  lateinit var tokenStore: TokenStore
    private set

  override fun onCreate() {
    super.onCreate()
    val client = HttpClients.create()
    tokenStore = TokenStore(this)
    musicRepository =
        MusicRepository(
            tokenStore = tokenStore,
            yandex = YandexRepository(client),
            youtube = YoutubeRepository(client),
        )
    playerController = PlayerController(this)
    playbackCoordinator = PlaybackCoordinator(musicRepository, playerController)
  }

  override fun onTerminate() {
    playerController.release()
    super.onTerminate()
  }
}
