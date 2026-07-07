package com.reallyfun.quantis.ui.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.reallyfun.quantis.data.model.Track
import com.reallyfun.quantis.domain.MusicRepository
import com.reallyfun.quantis.domain.PlaybackCoordinator
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class HomeUiState(
    val tracks: List<Track> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null,
    val playingTrackId: String? = null,
    val radioTrackId: String? = null,
)

class HomeViewModel(
    private val musicRepository: MusicRepository,
    private val playbackCoordinator: PlaybackCoordinator,
) : ViewModel() {
  private val _state = MutableStateFlow(HomeUiState())
  val state: StateFlow<HomeUiState> = _state.asStateFlow()

  private var loadJob: Job? = null

  init {
    refresh()
  }

  fun refresh() {
    loadJob?.cancel()
    loadJob =
        viewModelScope.launch {
          _state.update { it.copy(isLoading = true, error = null) }
          try {
            val tracks = musicRepository.homeRecommendations()
            _state.update { it.copy(tracks = tracks, isLoading = false) }
          } catch (e: Exception) {
            _state.update {
              it.copy(isLoading = false, error = e.message ?: "Не удалось загрузить рекомендации")
            }
          }
        }
  }

  fun play(track: Track) {
    viewModelScope.launch {
      _state.update { it.copy(playingTrackId = track.key) }
      val queue = _state.value.tracks
      playbackCoordinator.playSingle(track, queue)
      _state.update { it.copy(playingTrackId = null) }
    }
  }

  fun playRadio(track: Track) {
    viewModelScope.launch {
      _state.update { it.copy(radioTrackId = track.key) }
      playbackCoordinator.playRadio(track)
      _state.update { it.copy(radioTrackId = null) }
    }
  }

  companion object {
    fun factory(
        musicRepository: MusicRepository,
        playbackCoordinator: PlaybackCoordinator,
    ): ViewModelProvider.Factory =
        object : ViewModelProvider.Factory {
          @Suppress("UNCHECKED_CAST")
          override fun <T : ViewModel> create(modelClass: Class<T>): T =
              HomeViewModel(musicRepository, playbackCoordinator) as T
        }
  }
}
