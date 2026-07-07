package com.reallyfun.quantis

import android.Manifest
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import com.reallyfun.quantis.ui.QuantisRoot

class MainActivity : ComponentActivity() {
  private val notificationPermissionLauncher =
      registerForActivityResult(ActivityResultContracts.RequestPermission()) { }

  override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    requestNotificationPermissionIfNeeded()
    enableEdgeToEdge()
    val app = application as QuantisApplication
    setContent {
      QuantisRoot(
          musicRepository = app.musicRepository,
          playbackCoordinator = app.playbackCoordinator,
          playerController = app.playerController,
          tokenStore = app.tokenStore,
      )
    }
  }

  private fun requestNotificationPermissionIfNeeded() {
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
      notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
    }
  }
}
