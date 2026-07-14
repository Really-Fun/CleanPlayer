from __future__ import annotations

from PySide6.QtCore import QEvent, QPropertyAnimation, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from quantis.core.bootstrap import ApplicationBundle
from quantis.ui import resources
from quantis.ui.controllers.dynamic_wallpaper import DynamicWallpaperController
from quantis.ui.preferences import UiPreferences
from quantis.ui.viewmodels.home_vm import HomeViewModel
from quantis.ui.viewmodels.player_vm import PlayerViewModel
from quantis.ui.viewmodels.search_vm import SearchViewModel
from quantis.ui.viewmodels.playlist_vm import PlaylistViewModel
from quantis.ui.views.home_page import HomePage
from quantis.ui.views.library_page import LibraryPage
from quantis.ui.views.member_page import MemberPage
from quantis.ui.views.playlist_page import PlaylistPage
from quantis.ui.views.player_bar import PlayerBar
from quantis.ui.views.search_page import SearchPage
from quantis.ui.views.settings_page import SettingsPage
from quantis.ui.views.widgets.app_header import AppHeader
from quantis.ui.views.widgets.background_frame import BackgroundFrame
from quantis.ui.views.widgets.side_nav import SideNavRail
from quantis.ui.views.widgets.wallpaper_backdrop import BodyWithWallpaper


class QuantisMainWindow(QMainWindow):
    PAGE_HOME = 0
    PAGE_SEARCH = 1
    PAGE_LIBRARY = 2
    PAGE_MEMBER = 3
    PAGE_SETTINGS = 4
    PAGE_PLAYLIST = 5

    _PAGE_META = {
        PAGE_HOME: ("Главная", ""),
        PAGE_SEARCH: ("Поиск", ""),
        PAGE_LIBRARY: ("Библиотека", ""),
        PAGE_MEMBER: ("Member", ""),
        PAGE_SETTINGS: ("Настройки", ""),
    }

    def __init__(self, bundle: ApplicationBundle, parent=None) -> None:
        super().__init__(parent)

        app_font = QFont("Bahnschrift", 10)
        if not app_font.exactMatch():
            app_font = QFont("Segoe UI Variable Display", 10)
        if not app_font.exactMatch():
            app_font = QFont("Segoe UI", 10)
        QApplication.setFont(app_font)

        self._bundle = bundle
        self._bridge = bundle.async_bridge
        self.setWindowTitle("Quantis")
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
        )
        self.setMinimumSize(960, 640)
        self.resize(1200, 760)
        self._current_page = -1

        self._player_vm = PlayerViewModel(
            bundle.playback,
            bundle.player,
            bundle.event_bus,
        )
        self._search_vm = SearchViewModel(
            bundle.music.finder,
            bundle.playback,
            self._bridge,
            parent=self,
        )
        self._home_vm = HomeViewModel(
            bundle.history,
            bundle.playback,
            bundle.music,
            parent=self,
        )
        self._playlist_vm = PlaylistViewModel(
            bundle.playback,
            bridge=self._bridge,
            parent=self,
        )
        self._ui_prefs = UiPreferences()
        self._return_page_id = self.PAGE_HOME
        self._applied_theme = ""

        shell = BackgroundFrame(
            resources.wallpaper_path(),
            variant=self._ui_prefs.ui_theme,
        )
        self.setCentralWidget(shell)
        self._shell = shell

        root = QVBoxLayout(shell.content_host())
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._header = AppHeader()
        self._header.minimize_requested.connect(self.showMinimized)
        self._header.maximize_requested.connect(self._toggle_maximize)
        self._header.close_requested.connect(self.close)
        root.addWidget(self._header)

        self._body_shell = BodyWithWallpaper(
            resources.wallpaper_path(),
            variant=self._ui_prefs.ui_theme,
        )
        body = self._body_shell.layout_host
        body.setContentsMargins(10, 10, 10, 0)
        body.setSpacing(10)

        self._nav = SideNavRail()
        self._nav.page_changed.connect(self._on_page_changed)

        content_host = QWidget()
        content = QVBoxLayout(content_host)
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)

        self._stack = QStackedWidget()
        self._stack.setObjectName("pageStack")

        self._home_page = HomePage(self._home_vm, self._bridge, self._ui_prefs)
        self._library_page = LibraryPage(self._home_vm, self._bridge)
        # Search / Member / Settings / Playlist — лениво при первом открытии.
        self._search_page: SearchPage | None = None
        self._member_page: MemberPage | None = None
        self._settings_page: SettingsPage | None = None
        self._playlist_page: PlaylistPage | None = None

        self._stack.addWidget(self._home_page)
        self._stack.addWidget(QWidget())  # PAGE_SEARCH placeholder
        self._stack.addWidget(self._library_page)
        self._stack.addWidget(QWidget())  # PAGE_MEMBER placeholder
        self._stack.addWidget(QWidget())  # PAGE_SETTINGS placeholder
        self._stack.addWidget(QWidget())  # PAGE_PLAYLIST placeholder

        self._home_page.playlist_open_requested.connect(self._open_playlist_page)

        self._player_bar = PlayerBar(
            self._player_vm,
            bundle.music.provider,
            bridge=self._bridge,
            music=bundle.music,
            on_liked_changed=lambda: self._bridge.schedule(
                self._home_vm.refresh_liked(self._bridge)
            ),
        )

        content.addWidget(self._stack, stretch=1)
        content.addWidget(self._player_bar)

        body.addWidget(self._nav)
        body.addWidget(content_host, stretch=1)
        root.addWidget(self._body_shell, stretch=1)

        for view_model in (self._player_vm, self._search_vm, self._home_vm, self._playlist_vm):
            view_model.error_occurred.connect(self._show_error)

        bundle.event_bus.track_changed.connect(self._sync_playing_track)
        bundle.event_bus.history_updated.connect(self._on_history_updated)
        bundle.event_bus.error_occurred.connect(self._show_error)
        self._search_vm.download_finished.connect(
            lambda: self._home_vm.refresh_downloaded(self._bridge)
        )
        self._ui_prefs.changed.connect(self._on_prefs_changed)
        self._dynamic_wallpaper = DynamicWallpaperController(
            self._body_shell.backdrop,
            bundle.music,
            bundle.async_bridge,
            self._ui_prefs,
            bundle.event_bus,
            parent=self,
        )
        self._apply_ui_theme(self._ui_prefs.ui_theme)
        self._on_page_changed(self.PAGE_HOME)

    def _on_page_changed(self, page_id: int) -> None:
        if page_id < 0 or page_id >= self._stack.count():
            return
        if page_id == self.PAGE_PLAYLIST:
            return
        if page_id == self._current_page:
            return
        self._apply_page(page_id)

    def _replace_stack_page(self, index: int, widget: QWidget) -> None:
        old = self._stack.widget(index)
        self._stack.removeWidget(old)
        self._stack.insertWidget(index, widget)
        if old is not None:
            old.deleteLater()

    def _ensure_search_page(self) -> SearchPage:
        if self._search_page is None:
            self._search_page = SearchPage(self._search_vm, self._bridge)
            self._replace_stack_page(self.PAGE_SEARCH, self._search_page)
        return self._search_page

    def _ensure_member_page(self) -> MemberPage:
        if self._member_page is None:
            self._member_page = MemberPage(self._bridge)
            self._replace_stack_page(self.PAGE_MEMBER, self._member_page)
        return self._member_page

    def _ensure_settings_page(self) -> SettingsPage:
        if self._settings_page is None:
            self._settings_page = SettingsPage(self._ui_prefs, self._bridge)
            self._replace_stack_page(self.PAGE_SETTINGS, self._settings_page)
        return self._settings_page

    def _ensure_playlist_page(self) -> PlaylistPage:
        if self._playlist_page is None:
            self._playlist_page = PlaylistPage(self._playlist_vm, self._bridge)
            self._playlist_page.back_requested.connect(self._close_playlist_page)
            self._replace_stack_page(self.PAGE_PLAYLIST, self._playlist_page)
        return self._playlist_page

    def _apply_page(self, page_id: int) -> None:
        if page_id < 0 or page_id >= self._stack.count():
            return
        if page_id == self.PAGE_PLAYLIST:
            return
        if page_id == self._current_page:
            return
        if page_id == self.PAGE_SEARCH:
            self._ensure_search_page()
        elif page_id == self.PAGE_MEMBER:
            self._ensure_member_page()
        elif page_id == self.PAGE_SETTINGS:
            self._ensure_settings_page()
        previous = self._current_page
        self._current_page = page_id
        self._stack.setCurrentIndex(page_id)
        self._nav.set_active_page(page_id)
        self._fade_current_page()
        title, subtitle = self._PAGE_META.get(page_id, ("Quantis", ""))
        self._header.set_page(title, subtitle)
        if previous == self.PAGE_SEARCH and page_id != self.PAGE_SEARCH:
            self._search_vm.clear_results()
        if page_id in (self.PAGE_HOME, self.PAGE_LIBRARY):
            self._home_vm.request_load(self._bridge)

    def _fade_current_page(self) -> None:
        page = self._stack.currentWidget()
        if page is None:
            return
        effect = page.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(page)
            page.setGraphicsEffect(effect)
        effect.setOpacity(0.0)
        anim = QPropertyAnimation(effect, b"opacity", page)
        anim.setDuration(180)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.start()
        # Держим ссылку, иначе GC остановит анимацию
        page._quantis_fade = anim  # type: ignore[attr-defined]

    def _open_playlist_page(self, playlist) -> None:
        page = self._ensure_playlist_page()
        self._return_page_id = self._current_page
        self._playlist_vm.set_playlist(playlist)
        self._stack.setCurrentIndex(self.PAGE_PLAYLIST)
        count = len(playlist)
        self._header.set_page(playlist.name, f"{count} треков")
        _ = page

    def _close_playlist_page(self) -> None:
        if self._return_page_id == self.PAGE_PLAYLIST:
            self._return_page_id = self.PAGE_HOME
        page_id = self._return_page_id
        self._current_page = -1
        self._playlist_vm.clear()
        self._apply_page(page_id)

    def _sync_playing_track(self, track) -> None:
        self._search_vm.model.set_playing_track(track)
        self._home_vm.recent_model.set_playing_track(track)
        self._home_vm.recommendation_model.set_playing_track(track)
        self._library_page.set_playing_track(track)
        if self._playlist_page is not None:
            self._playlist_page.set_playing_track(track)
        self._home_page.refresh_featured()

    def _on_history_updated(self) -> None:
        from quantis.ui.async_ui import schedule

        schedule(self._home_vm.refresh_recent(self._bridge), self._bridge)

    def _on_prefs_changed(self) -> None:
        theme = self._ui_prefs.ui_theme
        if theme != self._applied_theme:
            self._apply_ui_theme(theme)
        self._apply_wallpaper()
        self._player_bar.refresh_theme()
        if self._ui_prefs.dynamic_wallpaper_enabled:
            self._dynamic_wallpaper.refresh_for_track(self._bundle.playback.current_track)

    def _apply_wallpaper(self) -> None:
        path = resources.wallpaper_path()
        self._body_shell.set_wallpaper(path or None)

    def _apply_ui_theme(self, theme_id: str) -> None:
        self._applied_theme = theme_id
        self.setStyleSheet(resources.load_stylesheet(theme_id))
        self._shell.set_variant(theme_id)
        self._body_shell.set_variant(theme_id)
        self._player_bar.refresh_theme()

    def _toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            self._header.set_maximized(self.isMaximized())

    def _show_error(self, message: str) -> None:
        import logging

        logging.getLogger(__name__).warning("Quantis: %s", message)


Quantis = QuantisMainWindow
