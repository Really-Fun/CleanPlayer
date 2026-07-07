package com.reallyfun.quantis.ui

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.reallyfun.quantis.data.prefs.TokenStore
import com.reallyfun.quantis.domain.MusicRepository
import com.reallyfun.quantis.domain.PlaybackCoordinator
import com.reallyfun.quantis.player.PlayerController
import com.reallyfun.quantis.ui.home.HomeScreen
import com.reallyfun.quantis.ui.home.HomeViewModel
import com.reallyfun.quantis.ui.player.PlayerBar
import com.reallyfun.quantis.ui.search.SearchScreen
import com.reallyfun.quantis.ui.search.SearchViewModel
import com.reallyfun.quantis.ui.settings.SettingsScreen
import com.reallyfun.quantis.ui.settings.SettingsViewModel
import com.reallyfun.quantis.ui.theme.QuantisTheme

private object Routes {
  const val HOME = "home"
  const val SEARCH = "search"
  const val SETTINGS = "settings"
}

@Composable
fun QuantisRoot(
    musicRepository: MusicRepository,
    playbackCoordinator: PlaybackCoordinator,
    playerController: PlayerController,
    tokenStore: TokenStore,
) {
  QuantisTheme {
    val navController = rememberNavController()
    val backStack by navController.currentBackStackEntryAsState()
    val currentRoute = backStack?.destination?.route ?: Routes.HOME
    val playerState by playerController.state.collectAsState()

    val homeViewModel: HomeViewModel =
        viewModel(factory = HomeViewModel.factory(musicRepository, playbackCoordinator))
    val searchViewModel: SearchViewModel =
        viewModel(factory = SearchViewModel.factory(musicRepository, playbackCoordinator))
    val settingsViewModel: SettingsViewModel =
        viewModel(factory = SettingsViewModel.factory(tokenStore))

    Scaffold(
        bottomBar = {
          Column {
            PlayerBar(
                state = playerState,
                onTogglePlayPause = playerController::togglePlayPause,
                onSkipPrevious = playerController::skipToPrevious,
                onSkipNext = playerController::skipToNext,
            )
            NavigationBar {
              NavigationBarItem(
                  selected = currentRoute == Routes.HOME,
                  onClick = { navController.navigate(Routes.HOME) },
                  icon = { Icon(Icons.Default.Home, contentDescription = null) },
                  label = { Text("Главная") },
              )
              NavigationBarItem(
                  selected = currentRoute == Routes.SEARCH,
                  onClick = { navController.navigate(Routes.SEARCH) },
                  icon = { Icon(Icons.Default.Search, contentDescription = null) },
                  label = { Text("Поиск") },
              )
              NavigationBarItem(
                  selected = currentRoute == Routes.SETTINGS,
                  onClick = { navController.navigate(Routes.SETTINGS) },
                  icon = { Icon(Icons.Default.Settings, contentDescription = null) },
                  label = { Text("Настройки") },
              )
            }
          }
        },
    ) { padding ->
      NavHost(
          navController = navController,
          startDestination = Routes.HOME,
          modifier = Modifier.padding(padding),
      ) {
        composable(Routes.HOME) {
          HomeScreen(viewModel = homeViewModel)
        }
        composable(Routes.SEARCH) {
          SearchScreen(viewModel = searchViewModel)
        }
        composable(Routes.SETTINGS) {
          SettingsScreen(viewModel = settingsViewModel)
        }
      }
    }
  }
}
