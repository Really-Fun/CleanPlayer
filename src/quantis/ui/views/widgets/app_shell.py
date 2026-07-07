from __future__ import annotations

from PySide6.QtWidgets import QWidget


class AppShell(QWidget):
    """Корневой виджет окна. Фон задаётся через QSS (#appShell)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("appShell")
