from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget


class NavPanel(QWidget):
    home_clicked = Signal()
    search_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("navPanel")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self._home_btn = QPushButton("Главная")
        self._search_btn = QPushButton("Поиск")
        self._home_btn.clicked.connect(self.home_clicked.emit)
        self._search_btn.clicked.connect(self.search_clicked.emit)

        layout.addWidget(self._home_btn)
        layout.addWidget(self._search_btn)
        layout.addStretch()
