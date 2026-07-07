from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from quantis.ui.views.widgets.brand_mark import BrandMark


class AppHeader(QFrame):
    """Компактная шапка: логотип + название страницы."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("appHeader")
        self.setFixedHeight(64)

        row = QHBoxLayout(self)
        row.setContentsMargins(20, 0, 24, 0)
        row.setSpacing(14)

        self._brand = BrandMark()
        row.addWidget(self._brand, 0, Qt.AlignmentFlag.AlignVCenter)

        text_col = QVBoxLayout()
        text_col.setSpacing(0)
        text_col.setContentsMargins(0, 0, 0, 0)

        self._title = QLabel("Quantis")
        self._title.setObjectName("headerGreeting")
        self._subtitle = QLabel("")
        self._subtitle.setObjectName("headerSub")
        self._subtitle.setVisible(False)

        text_col.addWidget(self._title)
        text_col.addWidget(self._subtitle)
        row.addLayout(text_col, stretch=1)

    def set_page(self, title: str, subtitle: str = "") -> None:
        self._title.setText(title)
        if subtitle:
            self._subtitle.setText(subtitle)
            self._subtitle.setVisible(True)
        else:
            self._subtitle.setVisible(False)
