from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from quantis.config.credentials import save_yandex_token, yandex_token
from quantis.core.async_bridge import AsyncBridge
from quantis.plugins import PluginRegistry
from quantis.plugins.loader import resolve_plugins_dir
from quantis.ui.preferences import UiPreferences
from quantis.ui.resources import UI_THEME_LABELS
from quantis.ui.wallpapers import (
    scan_wallpapers,
    user_backgrounds_dir,
    wallpaper_display_name,
)
from quantis.ui.views.widgets.glass_panel import GlassPanel

class SettingsPage(QWidget):
    def __init__(
        self,
        preferences: UiPreferences | None = None,
        bridge: AsyncBridge | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._prefs = preferences or UiPreferences()
        self._bridge = bridge
        self._registry = PluginRegistry.instance()
        self._plugin_checkboxes: dict[str, QCheckBox] = {}
        self.setObjectName("settingsPage")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("settingsScroll")
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 8, 16, 20)
        layout.setSpacing(12)

        panel = GlassPanel()
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(24, 22, 24, 22)
        panel_layout.setSpacing(20)

        panel_layout.addWidget(QLabel("Интерфейс", objectName="settingsSectionLabel"))

        theme_row, theme_body = self._row("Тема", "Внешний вид приложения")
        self._theme_combo = QComboBox()
        self._theme_combo.setObjectName("themeCombo")
        self._theme_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        for theme_id, label in UI_THEME_LABELS.items():
            self._theme_combo.addItem(label, theme_id)
        self._theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        theme_body.addWidget(self._theme_combo)
        panel_layout.addWidget(theme_row)

        self._home_featured_cb = QCheckBox("Панель «Сейчас» на главной")
        self._home_featured_cb.setObjectName("settingsCheck")
        self._home_featured_cb.setCursor(Qt.CursorShape.PointingHandCursor)
        self._home_featured_cb.toggled.connect(self._on_home_featured_toggled)
        panel_layout.addWidget(self._home_featured_cb)

        static_wall_row, static_wall_body = self._row(
            "Обои",
            f"Положите jpg/png в папку: {user_backgrounds_dir()}",
        )
        self._wallpaper_combo = QComboBox()
        self._wallpaper_combo.setObjectName("themeCombo")
        self._wallpaper_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self._wallpaper_combo.currentIndexChanged.connect(self._on_wallpaper_changed)
        static_wall_body.addWidget(self._wallpaper_combo)
        self._wallpaper_status = QLabel()
        self._wallpaper_status.setObjectName("settingsRowDesc")
        static_wall_body.addWidget(self._wallpaper_status)
        panel_layout.addWidget(static_wall_row)

        wallpaper_row, wallpaper_body = self._row(
            "Динамические обои",
            "Видео-клип YouTube вместо jpg-фона (зона под страницами, без звука)",
        )
        self._dynamic_wallpaper_cb = QCheckBox("Включить видео-фон при воспроизведении")
        self._dynamic_wallpaper_cb.setObjectName("settingsCheck")
        self._dynamic_wallpaper_cb.setCursor(Qt.CursorShape.PointingHandCursor)
        self._dynamic_wallpaper_cb.toggled.connect(self._on_dynamic_wallpaper_toggled)
        wallpaper_body.addWidget(self._dynamic_wallpaper_cb)
        panel_layout.addWidget(wallpaper_row)

        panel_layout.addWidget(QLabel("Сервисы", objectName="settingsSectionLabel"))

        yandex_row, yandex_body = self._row(
            "Yandex Music",
            "Токен хранится в системном keyring",
        )
        token_row = QHBoxLayout()
        self._yandex_token = QLineEdit()
        self._yandex_token.setObjectName("settingLineEdit")
        self._yandex_token.setPlaceholderText("Вставьте OAuth-токен")
        self._yandex_token.setEchoMode(QLineEdit.EchoMode.Password)
        self._save_token_btn = QPushButton("Сохранить")
        self._save_token_btn.setObjectName("searchButton")
        self._save_token_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_token_btn.clicked.connect(self._on_save_yandex_token)
        token_row.addWidget(self._yandex_token, stretch=1)
        token_row.addWidget(self._save_token_btn)
        yandex_body.addLayout(token_row)
        self._token_status = QLabel()
        self._token_status.setObjectName("settingsRowDesc")
        yandex_body.addWidget(self._token_status)
        panel_layout.addWidget(yandex_row)

        panel_layout.addWidget(QLabel("Плагины", objectName="settingsSectionLabel"))

        plugins_row, plugins_body = self._row(
            "Расширения",
            f"Папка: {resolve_plugins_dir()}",
        )
        self._plugins_layout = QVBoxLayout()
        self._plugins_layout.setSpacing(6)
        self._plugins_empty = QLabel(
            "Плагины не найдены. Создайте папку с plugin.py и manifest.json в plugins_dir/"
        )
        self._plugins_empty.setObjectName("settingsRowDesc")
        self._plugins_empty.setWordWrap(True)
        self._plugins_layout.addWidget(self._plugins_empty)
        plugins_body.addLayout(self._plugins_layout)
        panel_layout.addWidget(plugins_row)

        panel_layout.addStretch()
        layout.addWidget(panel)
        layout.addStretch()

        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self._prefs.changed.connect(self._sync_from_preferences)
        self._registry.plugin_changed.connect(self._on_plugin_registry_changed)
        self._sync_from_preferences()
        self._refresh_plugins()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._refresh_wallpapers()
        self._refresh_plugins()

    def _row(self, title: str, desc: str) -> tuple[QFrame, QVBoxLayout]:
        frame = QFrame()
        frame.setObjectName("settingsRow")
        col = QVBoxLayout(frame)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(8)
        col.addWidget(QLabel(title, objectName="settingsRowTitle"))
        col.addWidget(QLabel(desc, objectName="settingsRowDesc"))
        return frame, col

    def _sync_from_preferences(self) -> None:
        self._home_featured_cb.blockSignals(True)
        self._home_featured_cb.setChecked(self._prefs.show_home_featured_panel)
        self._home_featured_cb.blockSignals(False)

        self._dynamic_wallpaper_cb.blockSignals(True)
        self._dynamic_wallpaper_cb.setChecked(self._prefs.dynamic_wallpaper_enabled)
        self._dynamic_wallpaper_cb.blockSignals(False)

        self._theme_combo.blockSignals(True)
        index = self._theme_combo.findData(self._prefs.ui_theme)
        if index >= 0:
            self._theme_combo.setCurrentIndex(index)
        self._theme_combo.blockSignals(False)

        self._refresh_wallpapers(block_signals=True)
        self._update_token_status()

    def _update_token_status(self) -> None:
        if yandex_token():
            self._token_status.setText("Токен сохранён")
        else:
            self._token_status.setText("Без токена поиск Yandex недоступен")

    def _on_home_featured_toggled(self, checked: bool) -> None:
        self._prefs.set_show_home_featured_panel(checked)

    def _on_dynamic_wallpaper_toggled(self, checked: bool) -> None:
        self._prefs.set_dynamic_wallpaper_enabled(checked)

    def _refresh_wallpapers(self, *, block_signals: bool = False) -> None:
        if block_signals:
            self._wallpaper_combo.blockSignals(True)

        current = self._prefs.wallpaper_path
        self._wallpaper_combo.clear()
        self._wallpaper_combo.addItem("По умолчанию", "")

        files = scan_wallpapers()
        for path in files:
            self._wallpaper_combo.addItem(
                wallpaper_display_name(path),
                str(path.resolve()),
            )

        if not files:
            self._wallpaper_status.setText(
                "В папке background/user пока нет изображений — добавьте jpg или png"
            )
        else:
            user_count = sum(
                1 for p in files if str(p.parent.resolve()) == str(user_backgrounds_dir().resolve())
            )
            self._wallpaper_status.setText(
                f"Найдено обоев: {len(files)} (ваших: {user_count})"
            )

        index = self._wallpaper_combo.findData(current)
        if index < 0 and current:
            self._wallpaper_combo.addItem(f"⚠ {Path(current).name}", current)
            index = self._wallpaper_combo.findData(current)
        self._wallpaper_combo.setCurrentIndex(index if index >= 0 else 0)

        if block_signals:
            self._wallpaper_combo.blockSignals(False)

    def _on_wallpaper_changed(self, index: int) -> None:
        path = self._wallpaper_combo.itemData(index)
        self._prefs.set_wallpaper_path(str(path) if path else "")

    def _on_theme_changed(self, index: int) -> None:
        theme_id = self._theme_combo.itemData(index)
        if theme_id:
            self._prefs.set_ui_theme(str(theme_id))

    def _on_save_yandex_token(self) -> None:
        try:
            save_yandex_token(self._yandex_token.text())
            self._yandex_token.clear()
            self._token_status.setText("Токен сохранён")
        except ValueError as exc:
            self._token_status.setText(str(exc))
        except Exception as exc:
            self._token_status.setText(f"Ошибка: {exc}")

    def _on_plugin_registry_changed(self, _plugin_id: str) -> None:
        self._refresh_plugins()

    def _refresh_plugins(self) -> None:
        self._registry.rescan()
        while self._plugins_layout.count():
            item = self._plugins_layout.takeAt(0)
            widget = item.widget()
            if widget is not None and widget is not self._plugins_empty:
                widget.deleteLater()
        self._plugin_checkboxes.clear()

        infos = sorted(self._registry.get_all(), key=lambda i: i.meta.name.lower())
        if not infos:
            self._plugins_layout.addWidget(self._plugins_empty)
            self._plugins_empty.show()
            return

        self._plugins_empty.hide()

        for info in infos:
            meta = info.meta
            row = QWidget()
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(2)

            cb = QCheckBox(f"{meta.name}  v{meta.version}")
            cb.setObjectName("settingsCheck")
            cb.setCursor(Qt.CursorShape.PointingHandCursor)
            cb.blockSignals(True)
            cb.setChecked(info.is_active)
            cb.blockSignals(False)

            invalid = not meta.is_valid
            if invalid or info.error:
                cb.setEnabled(False)
            else:
                plugin_id = meta.plugin_id
                cb.toggled.connect(
                    lambda checked, pid=plugin_id: self._on_plugin_toggled(pid, checked)
                )

            row_layout.addWidget(cb)
            if meta.description:
                row_layout.addWidget(
                    QLabel(meta.description, objectName="settingsRowDesc")
                )
            if meta.author and meta.author != "Unknown":
                row_layout.addWidget(
                    QLabel(f"Автор: {meta.author}", objectName="settingsRowDesc")
                )
            if info.error:
                err = QLabel(info.error, objectName="settingsRowDesc")
                err.setStyleSheet("color: #e57373;")
                row_layout.addWidget(err)

            self._plugin_checkboxes[meta.plugin_id] = cb
            self._plugins_layout.addWidget(row)

    def _on_plugin_toggled(self, plugin_id: str, enabled: bool) -> None:
        if self._bridge is None:
            return
        self._registry.rescan()
        if enabled:
            self._bridge.schedule(self._registry.enable(plugin_id))
        else:
            self._bridge.schedule(self._registry.disable(plugin_id))
