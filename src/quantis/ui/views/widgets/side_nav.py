from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QButtonGroup, QFrame, QToolButton, QVBoxLayout, QWidget

from quantis.ui import resources


class SideNavRail(QFrame):
    """Минималистичная боковая навигация."""

    page_changed = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sideNavRail")
        self.setFixedWidth(72)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 16, 10, 16)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        logo = QToolButton()
        logo.setObjectName("navLogoMark")
        logo.setIcon(resources.load_icon("play.svg"))
        logo.setIconSize(QSize(22, 22))
        logo.setEnabled(False)
        logo.setToolTip("Quantis")
        layout.addWidget(logo, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(12)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        self._items: list[tuple[str, str, int]] = [
            ("recent.svg", "Главная", 0),
            ("search.svg", "Поиск", 1),
            ("download.svg", "Библиотека", 2),
            ("settings.svg", "Настройки", 3),
        ]

        for index, (icon, tooltip, page_id) in enumerate(self._items):
            button = QToolButton()
            button.setObjectName("navIconButton")
            button.setCheckable(True)
            button.setAutoRaise(True)
            button.setToolTip(tooltip)
            button.setIcon(resources.load_icon(icon))
            button.setIconSize(QSize(22, 22))
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setProperty("navIndex", index)
            button.clicked.connect(
                lambda checked=False, pid=page_id: self.page_changed.emit(pid)
            )
            self._group.addButton(button, page_id)
            layout.addWidget(button, 0, Qt.AlignmentFlag.AlignHCenter)

        layout.addStretch()
        self.set_active_page(0)

    def set_active_page(self, page_id: int) -> None:
        button = self._group.button(page_id)
        if button is not None and not button.isChecked():
            self._group.blockSignals(True)
            button.setChecked(True)
            self._group.blockSignals(False)
