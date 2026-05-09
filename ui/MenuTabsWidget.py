"""Боковая панель навигации.

Кнопки переключения страниц, настройки, папка, профиль.
Навигация осуществляется через строковые ``page_id`` (те же, что в :class:`Stack`).
"""

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QSize, Signal, QUrl
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from utils import asset_path
from core import AppContext


class MenuTabs(QWidget):
    """Левая панель навигации. Эмитит ``page_changed(str)`` при смене страницы."""

    page_changed = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setFixedWidth(100)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # ── Панель ───────────────────────────────────────────────────────────
        panel = QFrame(self)
        panel.setObjectName("navPanel")

        self._nav_layout = QVBoxLayout(panel)
        self._nav_layout.setContentsMargins(8, 10, 8, 10)
        self._nav_layout.setSpacing(8)
        self._nav_layout.setAlignment(Qt.AlignTop)

        # page_id → кнопка навигации (только чекбельные кнопки в центре)
        self._nav_button_map: dict[str, QPushButton] = {}

        # ── Кнопки навигации ──────────────────────────────────────────────────
        self.btn_home = self._add_nav_button("🏠", "home")
        self.btn_search = self._add_nav_button("🔍", "search")
        self.btn_library = self._add_nav_button("🎵", "playlist")
        self.btn_plugin = self._add_nav_button("🧩", "plugins")

        self.btn_home.setChecked(True)

        # ── Нижние кнопки инструментов ────────────────────────────────────────
        self.btn_settings = self._make_tool_button(
            asset_path("assets/icons/setting.png")
        )
        self.btn_settings.clicked.connect(lambda: self._switch("settings"))

        self.btn_folder = self._make_tool_button(asset_path("assets/icons/folder.png"))
        self.btn_folder.clicked.connect(self._open_app_folder)

        self.btn_account = self._make_tool_button(
            asset_path("assets/icons/account.png")
        )
        self.btn_account.clicked.connect(lambda: self._switch("user"))

        self._nav_layout.addStretch(1)

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.btn_settings)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.btn_folder)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.btn_account)
        self._nav_layout.addLayout(bottom_layout)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(panel)

    # ── Публичный API ─────────────────────────────────────────────────────────

    def set_active_page(self, page_id: str) -> None:
        """Устанавливает визуально активную вкладку без эмита сигнала."""
        for pid, btn in self._nav_button_map.items():
            btn.setChecked(pid == page_id)

    def add_nav_button(self, label: str, page_id: str) -> QPushButton:
        """Добавляет кнопку навигации (для плагинов).

        Args:
            label:    Текст или emoji на кнопке.
            page_id:  ID страницы, которую открывает кнопка.

        Returns:
            Созданная кнопка (можно кастомизировать после добавления).
        """
        # Вставляем перед stretch/нижними кнопками
        stretch_index = self._nav_layout.count() - 1  # stretch стоит предпоследним
        btn = self._make_nav_button(label)
        btn.clicked.connect(lambda: self._switch(page_id))
        self._nav_button_map[page_id] = btn
        self._nav_layout.insertWidget(stretch_index, btn)
        return btn

    # ── Внутренние методы ─────────────────────────────────────────────────────

    def _add_nav_button(self, label: str, page_id: str) -> QPushButton:
        """Создаёт и добавляет кнопку навигации при инициализации."""
        btn = self._make_nav_button(label)
        btn.clicked.connect(lambda: self._switch(page_id))
        self._nav_button_map[page_id] = btn
        self._nav_layout.addWidget(btn)
        return btn

    def _switch(self, page_id: str) -> None:
        self.set_active_page(page_id)
        self.page_changed.emit(page_id)

    @staticmethod
    def _make_nav_button(text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedHeight(36)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setObjectName("navButton")
        btn.setCheckable(True)
        return btn

    @staticmethod
    def _make_tool_button(icon_path: str, size: int = 32) -> QToolButton:
        btn = QToolButton()
        btn.setIcon(QIcon(icon_path))
        btn.setIconSize(QSize(size - 4, size - 4))
        btn.setFixedSize(size, size)
        btn.setAutoRaise(True)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setObjectName("roundButton")
        return btn

    @staticmethod
    def _open_app_folder() -> None:
        """Открывает директорию приложения в проводнике."""
        if getattr(sys, "frozen", False):
            app_dir = Path(sys.executable).resolve().parent
        else:
            app_dir = Path(__file__).resolve().parent.parent
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(app_dir)))
