from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QButtonGroup, QFrame, QToolButton, QVBoxLayout, QWidget

from quantis.ui import resources


class SideNavRail(QFrame):
    """Компактная боковая навигация без декоративных кнопок."""

    page_changed = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sideNavRail")
        self.setFixedWidth(80)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 14, 8, 14)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        # Верх: основные разделы. Низ: Member + Настройки.
        top_items: list[tuple[str, str, int]] = [
            ("recent.svg", "Главная", 0),
            ("search.svg", "Поиск", 1),
            ("download.svg", "Библиотека", 2),
        ]
        bottom_items: list[tuple[str, str, int]] = [
            ("member.svg", "Member", 3),
            ("settings.svg", "Настройки", 4),
        ]
        self._items = top_items + bottom_items

        for icon, tooltip, page_id in top_items:
            layout.addWidget(self._make_button(icon, tooltip, page_id), 0, Qt.AlignmentFlag.AlignHCenter)

        layout.addStretch()

        for icon, tooltip, page_id in bottom_items:
            layout.addWidget(self._make_button(icon, tooltip, page_id), 0, Qt.AlignmentFlag.AlignHCenter)

        self.set_active_page(0)

    def _make_button(self, icon: str, tooltip: str, page_id: int) -> QToolButton:
        button = QToolButton()
        button.setObjectName("navIconButton")
        button.setCheckable(True)
        button.setAutoRaise(True)
        button.setToolTip(tooltip)
        button.setIcon(resources.load_icon(icon))
        button.setIconSize(QSize(20, 20))
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setProperty("navIndex", page_id)
        button.clicked.connect(
            lambda checked=False, pid=page_id: self.page_changed.emit(pid)
        )
        self._group.addButton(button, page_id)
        return button

    def set_active_page(self, page_id: int) -> None:
        button = self._group.button(page_id)
        if button is not None and not button.isChecked():
            self._group.blockSignals(True)
            button.setChecked(True)
            self._group.blockSignals(False)
