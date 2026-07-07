from __future__ import annotations

from PySide6.QtCore import Qt
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
from quantis.ui.preferences import UiPreferences
from quantis.ui.resources import UI_THEME_LABELS
from quantis.ui.views.widgets.glass_panel import GlassPanel


class SettingsPage(QWidget):
    def __init__(
        self,
        preferences: UiPreferences | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._prefs = preferences or UiPreferences()
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

        panel_layout.addStretch()
        layout.addWidget(panel)
        layout.addStretch()

        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self._prefs.changed.connect(self._sync_from_preferences)
        self._sync_from_preferences()

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

        self._theme_combo.blockSignals(True)
        index = self._theme_combo.findData(self._prefs.ui_theme)
        if index >= 0:
            self._theme_combo.setCurrentIndex(index)
        self._theme_combo.blockSignals(False)

        self._update_token_status()

    def _update_token_status(self) -> None:
        if yandex_token():
            self._token_status.setText("Токен сохранён")
        else:
            self._token_status.setText("Без токена поиск Yandex недоступен")

    def _on_home_featured_toggled(self, checked: bool) -> None:
        self._prefs.set_show_home_featured_panel(checked)

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
