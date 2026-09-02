"""Пользовательские настройки интерфейса (QSettings)."""

from __future__ import annotations

from PySide6.QtCore import QObject, QSettings, Signal

from quantis.models.repeat_mode import RepeatMode
from quantis.ui.resources import DEFAULT_UI_THEME, normalize_ui_theme


class UiPreferences(QObject):
    """Синглтон настроек UI."""

    changed = Signal()

    _instance: UiPreferences | None = None

    _KEY_HOME_FEATURED = "ui/show_home_featured_panel"
    _KEY_UI_THEME = "ui/theme"
    _KEY_DYNAMIC_WALLPAPER = "ui/dynamic_wallpaper"
    _KEY_WALLPAPER = "ui/wallpaper_path"
    _KEY_WALLPAPER_ENABLED = "ui/wallpaper_enabled"
    _KEY_NOW_PLAYING = "ui/show_now_playing_panel"
    _KEY_BACKGROUND_ECO = "ui/background_eco"
    _KEY_VOLUME = "playback/volume"
    _KEY_REPEAT_MODE = "playback/repeat_mode"

    def __new__(cls) -> UiPreferences:
        if cls._instance is None:
            obj = super().__new__(cls)
            obj._initialized = False
            cls._instance = obj
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        super().__init__()
        self._settings = QSettings("ReallyFun", "Quantis")
        self._initialized = True

    @staticmethod
    def _read_bool(raw: object, default: bool) -> bool:
        if isinstance(raw, str):
            return raw.lower() in ("true", "1", "yes")
        if raw is None:
            return default
        return bool(raw)

    @property
    def show_home_featured_panel(self) -> bool:
        return self._read_bool(
            self._settings.value(self._KEY_HOME_FEATURED, True),
            True,
        )

    def set_show_home_featured_panel(self, value: bool) -> None:
        if self.show_home_featured_panel == value:
            return
        self._settings.setValue(self._KEY_HOME_FEATURED, value)
        self.changed.emit()

    @property
    def show_now_playing_panel(self) -> bool:
        return self._read_bool(
            self._settings.value(self._KEY_NOW_PLAYING, True),
            True,
        )

    def set_show_now_playing_panel(self, value: bool) -> None:
        if self.show_now_playing_panel == value:
            return
        self._settings.setValue(self._KEY_NOW_PLAYING, value)
        self.changed.emit()

    @property
    def ui_theme(self) -> str:
        raw = self._settings.value(self._KEY_UI_THEME, DEFAULT_UI_THEME)
        return normalize_ui_theme(str(raw) if raw is not None else None)

    def set_ui_theme(self, theme_id: str) -> None:
        theme_id = normalize_ui_theme(theme_id)
        if self.ui_theme == theme_id:
            return
        self._settings.setValue(self._KEY_UI_THEME, theme_id)
        self.changed.emit()

    @property
    def dynamic_wallpaper_enabled(self) -> bool:
        return self._read_bool(
            self._settings.value(self._KEY_DYNAMIC_WALLPAPER, False),
            False,
        )

    def set_dynamic_wallpaper_enabled(self, value: bool) -> None:
        if self.dynamic_wallpaper_enabled == value:
            return
        self._settings.setValue(self._KEY_DYNAMIC_WALLPAPER, value)
        self.changed.emit()

    @property
    def wallpaper_path(self) -> str:
        raw = self._settings.value(self._KEY_WALLPAPER, "")
        return str(raw).strip() if raw else ""

    def set_wallpaper_path(self, path: str) -> None:
        normalized = path.strip()
        if self.wallpaper_path == normalized:
            return
        self._settings.setValue(self._KEY_WALLPAPER, normalized)
        self.changed.emit()

    @property
    def wallpaper_enabled(self) -> bool:
        return self._read_bool(
            self._settings.value(self._KEY_WALLPAPER_ENABLED, False),
            False,
        )

    def set_wallpaper_enabled(self, value: bool) -> None:
        if self.wallpaper_enabled == value:
            return
        self._settings.setValue(self._KEY_WALLPAPER_ENABLED, value)
        self.changed.emit()

    @property
    def background_eco_enabled(self) -> bool:
        """Экономия ресурсов, пока окно свёрнуто / не в фокусе (игры)."""
        return self._read_bool(
            self._settings.value(self._KEY_BACKGROUND_ECO, True),
            True,
        )

    def set_background_eco_enabled(self, value: bool) -> None:
        if self.background_eco_enabled == value:
            return
        self._settings.setValue(self._KEY_BACKGROUND_ECO, value)
        self.changed.emit()

    @property
    def volume(self) -> int:
        raw = self._settings.value(self._KEY_VOLUME, 80)
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return 80
        return max(0, min(100, value))

    def set_volume(self, value: int) -> None:
        clamped = max(0, min(100, int(value)))
        if self.volume == clamped:
            return
        self._settings.setValue(self._KEY_VOLUME, clamped)
        self.changed.emit()

    @property
    def repeat_mode(self) -> RepeatMode:
        raw = self._settings.value(self._KEY_REPEAT_MODE, RepeatMode.PLAYLIST.value)
        return RepeatMode.from_value(str(raw) if raw is not None else None)

    def set_repeat_mode(self, mode: RepeatMode) -> None:
        if self.repeat_mode == mode:
            return
        self._settings.setValue(self._KEY_REPEAT_MODE, mode.value)
        self.changed.emit()
