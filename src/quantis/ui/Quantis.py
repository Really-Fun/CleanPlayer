"""Главное окно приложения Quantis."""

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

from quantis.core import AppContext
from quantis.plugins.registry import PluginRegistry
from quantis.ui.AudioVisualizer import AudioVisualizer
from quantis.ui.MenuPlayWidget import PlayMenu
from quantis.ui.MenuTabsWidget import MenuTabs
from quantis.ui.Stack import Stack
from quantis.ui.title_bar import CustomTitleBar
from quantis.ui.ThemeManager import ThemeManager
from quantis.utils import get_asset_path


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

    def __init__(self, context: AppContext) -> None:
        super().__init__()
        self.context = context

        ThemeManager.apply_theme_to_app(self)
        self._settings = QSettings("ReallyFun", "Quantis")

        self._load_settings()
        self._setup_window()
        self._setup_widgets()
        self._connect_signals()
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

        self.background = QLabel(central)
        bg_path = self._settings.value(self._KEY_VIZ_BG)
        pm = QPixmap(get_asset_path(bg_path)) if bg_path else QPixmap()
        if pm.isNull():
            pm = QPixmap(get_asset_path("assets/background/default.jpg"))
        self.background.setPixmap(pm)
        self.background.setScaledContents(True)

        self.dark_overlay = QFrame(central)
        self.dark_overlay.setObjectName("darkOverlay")

        self.visualizer = AudioVisualizer(
            central,
            bar_count=56,
            height=120,
            delay_ms=self._viz_delay,
            color_rgb=self._viz_color,
            mode=self._viz_mode,
        )

        self.background.lower()
        self.dark_overlay.stackUnder(self.visualizer)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.title_bar = CustomTitleBar(self, title="Quantis")
        main_layout.addWidget(self.title_bar)
        
        self.setWindowTitle("Quantis")
        self.setWindowIcon(QIcon("assets/icons/logo1.jpg"))


        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.menu_tabs = MenuTabs(self)
        self.menu_tabs.setMaximumWidth(10)
        self.menu_tabs.setAttribute(Qt.WA_TranslucentBackground)
        content_layout.addWidget(self.menu_tabs)

        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.stack = Stack(self.context, self)
        right_layout.addWidget(self.stack, stretch=1)

        self.play_menu = PlayMenu(self.context)
        self.play_menu.setFixedHeight(90)
        self.play_menu.setAttribute(Qt.WA_TranslucentBackground)
        right_layout.addWidget(self.play_menu)

        content_layout.addLayout(right_layout)
        main_layout.addLayout(content_layout)

    def _connect_signals(self) -> None:
        """Подключает все сигналы."""
        self.menu_tabs.page_changed.connect(self.stack.switch_to)
        self.stack.home_page.playlist_opened.connect(self._open_playlist)

        self.context.event_bus.track_changed.connect(self._change_bg_from_track)

        self.play_menu.playlist_generated.connect(self.display_radio_on_home)

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
        """Инициализирует систему плагинов."""

        self.context.stack = self.stack
        self.context.menu_tabs = self.menu_tabs

        # Передаем настройки для плагинов
        self.context.plugin_settings = QSettings("ReallyFun", "Quantis/plugins")

        await self.context.plugin_registry.load_all(self.context)

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
        path = self.context.path_provider.get_cover_path(track)

        if os.path.exists(path):
            self._change_bg(path)

    def _toggle_viz(self, on: bool) -> None:
        self._settings.setValue(self._KEY_VIZ_TOGGLE, on)
        self.visualizer.show() if on else self.visualizer.hide()

    def _set_visualizer_delay(self, delay_ms: int) -> None:
        self.visualizer.set_delay_ms(delay_ms)
        self._settings.setValue(self._KEY_VIZ_DELAY, int(delay_ms))

    def _set_visualizer_color(self, rgb: tuple[int, int, int]) -> None:
        self.visualizer.set_color_rgb(rgb)
        self._settings.setValue(self._KEY_VIZ_R, int(rgb[0]))
        self._settings.setValue(self._KEY_VIZ_G, int(rgb[1]))
        self._settings.setValue(self._KEY_VIZ_B, int(rgb[2]))

    def _set_visualizer_mode(self, mode: str) -> None:
        self.visualizer.set_mode(mode)
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
        """Размещает окно по центру экрана."""
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            frame = self.frameGeometry()
            frame.moveCenter(available.center())
            self.move(frame.topLeft())

    def resizeEvent(self, event) -> None:
        self.background.resize(self.size())
        self.dark_overlay.resize(self.size())
        viz_h = self.visualizer.height()
        self.visualizer.setGeometry(
            0,
            (self.height() - viz_h) // 2,
            self.width(),
            viz_h,
        )
        super().resizeEvent(event)
