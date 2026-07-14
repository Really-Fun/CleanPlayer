"""Пользовательские настройки интерфейса (QSettings)."""



from __future__ import annotations



from PySide6.QtCore import QObject, QSettings, Signal



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

            self._settings.value(self._KEY_HOME_FEATURED, False),

            False,

        )



    def set_show_home_featured_panel(self, value: bool) -> None:

        if self.show_home_featured_panel == value:

            return

        self._settings.setValue(self._KEY_HOME_FEATURED, value)

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

