package com.reallyfun.quantis.data.network

import io.ktor.client.HttpClient
import io.ktor.client.engine.android.Android
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.plugins.logging.LogLevel
import io.ktor.client.plugins.logging.Logger
import io.ktor.client.plugins.logging.Logging
import io.ktor.serialization.kotlinx.json.json
import kotlinx.serialization.json.Json

object HttpClients {
  val json: Json =
      Json {
        ignoreUnknownKeys = true
        isLenient = true
        explicitNulls = false
      }

  fun create(): HttpClient =
      HttpClient(Android) {
        install(ContentNegotiation) { json(json) }
        install(Logging) {
          level = LogLevel.INFO
          logger =
              object : Logger {
                override fun log(message: String) {
                  android.util.Log.d("QuantisHttp", message)
                }
              }
        }
      }
}
