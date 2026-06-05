"""Главное окно приложения Quantis с явным внедрением зависимостей."""

from __future__ import annotations

import asyncio
import os

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QGuiApplication, QIcon, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)
from qasync import asyncSlot

from quantis.player import Player
from quantis.plugins import EventBus, PluginRegistry
from quantis.providers import PathProvider
from quantis.ui.MenuPlayWidget import PlayMenu
from quantis.ui.MenuTabsWidget import MenuTabs
from quantis.ui.Stack import Stack
from quantis.ui.ThemeManager import ThemeManager
from quantis.ui.title_bar import CustomTitleBar
from quantis.utils import get_asset_path
from quantis.services import AsyncFinder, AsyncDownloader, AsyncStreamer, TrackHistoryService
from quantis.services.AsyncRecomendation import AsyncRecomendation
from quantis.ui.HomePage import HomePage
from quantis.ui.PlaylistPage import PlaylistPage
from quantis.ui.SearchPage import SearchPage
from quantis.ui.SettingsPage import SettingsPage
from quantis.ui.UserPage import UserPage
from quantis.ui.PluginsManagerPage import PluginsManagerPage


class Quantis(QMainWindow):
    """Главное окно: меню, контент, плеер, визуализатор."""

    _KEY_VIZ_TOGGLE = "visualizer/toggle"
    _KEY_VIZ_DELAY = "visualizer/delay_ms"
    _KEY_VIZ_MODE = "visualizer/mode"
    _KEY_VIZ_R = "visualizer/color_r"
    _KEY_VIZ_G = "visualizer/color_g"
    _KEY_VIZ_B = "visualizer/color_b"
    _KEY_VIZ_BG = "visualizer/bg"
    _KEY_COVER_TOGGLE = "background/cover_toggle"

    def __init__(self, loop: asyncio.AbstractEventLoop | None = None) -> None:
        super().__init__()
        self._loop = loop or asyncio.get_event_loop()

        # 1. Инициализация независимых CORE-сервисов (Бэкенд)
        self.event_bus = EventBus()
        self.finder = AsyncFinder()
        self.downloader = AsyncDownloader()
        self.recommendation = AsyncRecomendation()
        self.path_provider = PathProvider()
        self.plugin_registry = PluginRegistry()

        # Инициализация Player (зависит напрямую от цикла и базовых сервисов)
        self.player = Player(
            self.event_bus,
            path_provider=self.path_provider,
            streamer=AsyncStreamer(),
            history_service=TrackHistoryService(),
            loop=self._loop
        )

        # 2. Инициализация настроек приложения (До сборки UI)
        self._settings = QSettings("ReallyFun", "Quantis")
        self._load_settings()

        # 3. Настройка и сборка графического интерфейса
        ThemeManager.apply_theme_to_app(self)
        self._setup_window()
        self._setup_widgets()
        self._connect_signals()

        # 4. Применение начального состояния
        self._apply_initial_state()

    # ── Инициализация ─────────────────────────────────────────────────────────

    def _load_settings(self) -> None:
        """Читает настройки из QSettings и сохраняет в атрибуты."""
        s = self._settings
        self.viz_toggle = s.value(self._KEY_VIZ_TOGGLE, False, type=bool)
        self.cover_wallpaper_toggle = s.value(self._KEY_COVER_TOGGLE, False, type=bool)
        self._viz_delay = int(s.value(self._KEY_VIZ_DELAY, 25))
        self._viz_mode = str(s.value(self._KEY_VIZ_MODE, "smooth"))
        viz_r = int(s.value(self._KEY_VIZ_R, 0))
        viz_g = int(s.value(self._KEY_VIZ_G, 220))
        viz_b = int(s.value(self._KEY_VIZ_B, 255))
        self._viz_color = (viz_r, viz_g, viz_b)

    def _setup_window(self) -> None:
        """Настраивает размер, заголовок и позицию окна."""
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setWindowTitle("Quantis")
        self.setWindowIcon(QIcon("assets/icons/logo1.jpg"))
        self.resize(800, 640)
        self.setMaximumSize(1920, 1080)
        self._center_on_screen()

    def _setup_widgets(self) -> None:
        """Создаёт и компонует все виджеты главного окна."""
        central = QWidget(self)
        central.setObjectName("central")
        self.setCentralWidget(central)

        # Фоновые обои
        self.background = QLabel(central)
        bg_path = self._settings.value(self._KEY_VIZ_BG)
        pm = QPixmap(get_asset_path(bg_path)) if bg_path else QPixmap()
        if pm.isNull():
            pm = QPixmap(get_asset_path("assets/background/default.jpg"))
        self.background.setPixmap(pm)
        self.background.setScaledContents(True)

        self.dark_overlay = QFrame(central)
        self.dark_overlay.setObjectName("darkOverlay")
        self.background.lower()

        # Главный вертикальный Layout (Кастомный тайтлбар + контент)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.title_bar = CustomTitleBar(self, title="Quantis")
        main_layout.addWidget(self.title_bar)

        # Горизонтальный контент-лейаут (Боковое меню + правая рабочая область)
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Вкладки бокового меню
        self.menu_tabs = MenuTabs(self)
        self.menu_tabs.setMaximumWidth(10)
        self.menu_tabs.setAttribute(Qt.WA_TranslucentBackground)
        content_layout.addWidget(self.menu_tabs)

        # Правая область: Стек страниц + Нижний плеер
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Чистый Стек страниц с использованием лямбда-фабрик (DI)
        self.stack = Stack(self)
        self.stack.register_page(Stack.PAGE_HOME, lambda: HomePage(self.recommendation))
        self.stack.register_page(Stack.PAGE_SEARCH, lambda: SearchPage(self.finder, self.player))
        self.stack.register_page(Stack.PAGE_PLAYLIST, lambda: PlaylistPage(self.player, self.event_bus))
        self.stack.register_page(Stack.PAGE_SETTINGS, lambda: SettingsPage())
        self.stack.register_page(Stack.PAGE_USER, lambda: UserPage(), go_back=Stack.PAGE_HOME)
        self.stack.register_page(Stack.PAGE_PLUGINS, lambda: PluginsManagerPage())

        right_layout.addWidget(self.stack, stretch=1)

        # Нижняя панель управления плеером
        self.play_menu = PlayMenu(self.player, self.event_bus)
        self.play_menu.setFixedHeight(90)
        self.play_menu.setAttribute(Qt.WA_TranslucentBackground)
        right_layout.addWidget(self.play_menu)

        content_layout.addLayout(right_layout)
        main_layout.addLayout(content_layout)

    def _connect_signals(self) -> None:
        """Подключает все сигналы напрямую к сервисам."""
        self.menu_tabs.page_changed.connect(self.stack.switch_to)
        self.stack.home_page.playlist_opened.connect(self._open_playlist)

        # Прямой коннект к шине событий бэкенда
        self.event_bus.track_changed.connect(self._change_bg_from_track)
        self.play_menu.playlist_generated.connect(self.display_radio_on_home)

        # Сигналы со страницы настроек
        sp = self.stack.settings_page
        sp.background_changed.connect(self._change_bg)
        sp.visualizer_toggled.connect(self._toggle_viz)
        sp.visualizer_delay_changed.connect(self._set_visualizer_delay)
        sp.visualizer_color_changed.connect(self._set_visualizer_color)
        sp.visualizer_mode_changed.connect(self._set_visualizer_mode)
        sp.cover_wallpaper_toggled.connect(self._change_dynamic_wallpaper)

    def _apply_initial_state(self) -> None:
        """Применяет сохранённые настройки к UI."""
        self.menu_tabs.set_active_page("home")
        self._toggle_viz(self.viz_toggle)

        sp = self.stack.settings_page
        sp.set_toggle_flags(self.viz_toggle, self.cover_wallpaper_toggle)
        sp.set_visualizer_settings(self._viz_delay, self._viz_color, self._viz_mode)

        asyncio.ensure_future(self._setup_plugins())

    async def _setup_plugins(self) -> None:
        """Инициализирует систему плагинов через безопасный Plugin API контекст."""
        plugin_settings = QSettings("ReallyFun", "Quantis/plugins")

        # Передаем только то, что плагинам разрешено трогать
        await self.plugin_registry.load_all(
            player=self.player,
            event_bus=self.event_bus,
            stack=self.stack,
            settings=plugin_settings
        )

    # ── Слоты ─────────────────────────────────────────────────────────────────

    @asyncSlot(object)
    async def _open_playlist(self, playlist) -> None:
        await self.stack.open_playlist(playlist)

    def _change_bg(self, path: str) -> None:
        pm = QPixmap(path)
        self._settings.setValue(self._KEY_VIZ_BG, path)
        if not pm.isNull():
            self.background.setPixmap(pm)

    def _change_bg_from_track(self, track) -> None:
        if not self.cover_wallpaper_toggle:
            return
        path = self.path_provider.get_cover_path(track)
        if os.path.exists(path):
            self._change_bg(path)

    def _toggle_viz(self, on: bool) -> None:
        self._settings.setValue(self._KEY_VIZ_TOGGLE, on)

    def _set_visualizer_delay(self, delay_ms: int) -> None:
        self._settings.setValue(self._KEY_VIZ_DELAY, int(delay_ms))

    def _set_visualizer_color(self, rgb: tuple[int, int, int]) -> None:
        self._settings.setValue(self._KEY_VIZ_R, int(rgb[0]))
        self._settings.setValue(self._KEY_VIZ_G, int(rgb[1]))
        self._settings.setValue(self._KEY_VIZ_B, int(rgb[2]))

    def _set_visualizer_mode(self, mode: str) -> None:
        self._settings.setValue(self._KEY_VIZ_MODE, str(mode))

    def _change_dynamic_wallpaper(self, flag: bool) -> None:
        self._settings.setValue(self._KEY_COVER_TOGGLE, flag)
        self.cover_wallpaper_toggle = flag

    def display_radio_on_home(self, playlist) -> None:
        self.stack.home_page.add_recommendation_section(playlist)
        self.stack.switch_to("home")
        self.menu_tabs.set_active_page("home")

    # ── Qt overrides ──────────────────────────────────────────────────────────

    def _center_on_screen(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            frame = self.frameGeometry()
            frame.moveCenter(available.center())
            self.move(frame.topLeft())

    def resizeEvent(self, event) -> None:
        self.background.resize(self.size())
        self.dark_overlay.resize(self.size())
        super().resizeEvent(event)