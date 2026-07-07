package com.reallyfun.quantis.ui.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.reallyfun.quantis.data.prefs.TokenStore
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class SettingsUiState(
    val yandexToken: String = "",
    val saved: Boolean = false,
)

class SettingsViewModel(private val tokenStore: TokenStore) : ViewModel() {
  private val _state = MutableStateFlow(SettingsUiState())
  val state: StateFlow<SettingsUiState> = _state.asStateFlow()

  init {
    viewModelScope.launch {
      tokenStore.yandexToken.collect { token ->
        _state.update { it.copy(yandexToken = token.orEmpty()) }
      }
    }
  }

  fun onTokenChange(value: String) {
    _state.update { it.copy(yandexToken = value, saved = false) }
  }

  fun save() {
    viewModelScope.launch {
      tokenStore.setYandexToken(_state.value.yandexToken)
      _state.update { it.copy(saved = true) }
    }
  }

  companion object {
    fun factory(tokenStore: TokenStore): ViewModelProvider.Factory =
        object : ViewModelProvider.Factory {
          @Suppress("UNCHECKED_CAST")
          override fun <T : ViewModel> create(modelClass: Class<T>): T =
              SettingsViewModel(tokenStore) as T
        }
  }
}
