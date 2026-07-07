package com.reallyfun.quantis.ui.search

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

data class SearchUiState(
    val query: String = "",
    val tracks: List<Track> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null,
    val playingTrackId: String? = null,
    val radioTrackId: String? = null,
)

class SearchViewModel(
    private val musicRepository: MusicRepository,
    private val playbackCoordinator: PlaybackCoordinator,
) : ViewModel() {
  private val _state = MutableStateFlow(SearchUiState())
  val state: StateFlow<SearchUiState> = _state.asStateFlow()

  private var searchJob: Job? = null

  fun onQueryChange(value: String) {
    _state.update { it.copy(query = value) }
  }

  fun search() {
    val query = _state.value.query.trim()
    if (query.isEmpty()) return

    searchJob?.cancel()
    searchJob =
        viewModelScope.launch {
          _state.update { it.copy(isLoading = true, error = null) }
          try {
            val tracks = musicRepository.search(query)
            _state.update { it.copy(tracks = tracks, isLoading = false) }
          } catch (e: Exception) {
            _state.update {
              it.copy(
                  isLoading = false,
                  error = e.message ?: "Ошибка поиска",
              )
            }
          }
        }
  }

  fun play(track: Track) {
    viewModelScope.launch {
      _state.update { it.copy(playingTrackId = track.key) }
      playbackCoordinator.playSingle(track, _state.value.tracks)
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
              SearchViewModel(musicRepository, playbackCoordinator) as T
        }
  }
}
