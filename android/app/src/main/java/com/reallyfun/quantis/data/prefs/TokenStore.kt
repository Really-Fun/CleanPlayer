package com.reallyfun.quantis.data.prefs

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "quantis_prefs")

class TokenStore(private val context: Context) {
  private val yandexTokenKey = stringPreferencesKey("yandex_token")

  val yandexToken: Flow<String?> =
      context.dataStore.data.map { prefs -> prefs[yandexTokenKey]?.takeIf { it.isNotBlank() } }

  suspend fun setYandexToken(token: String) {
    context.dataStore.edit { prefs ->
      if (token.isBlank()) {
        prefs.remove(yandexTokenKey)
      } else {
        prefs[yandexTokenKey] = token.trim()
      }
    }
  }
}
