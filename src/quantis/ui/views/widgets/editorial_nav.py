from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QButtonGroup, QFrame, QPushButton, QVBoxLayout, QWidget


class EditorialNavRail(QFrame):
    """Навигация справа с нумерацией — в духе SoundCloud / editorial."""

    page_changed = Signal(int)

    _ITEMS = (
        ("01", "Главная", 0),
        ("02", "Поиск", 1),
        ("03", "Библиотека", 2),
        ("04", "Настройки", 3),
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("editorialNav")
        self.setFixedWidth(168)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addSpacing(20)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: list[QPushButton] = []

        for num, label, page_id in self._ITEMS:
            btn = QPushButton(f"{num}  {label}")
            btn.setObjectName("navEditorialBtn")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty("navNum", num)
            btn.clicked.connect(lambda checked=False, pid=page_id: self.page_changed.emit(pid))
            self._group.addButton(btn, page_id)
            self._buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()

        rule = QFrame()
        rule.setObjectName("navEditorialRule")
        rule.setFixedHeight(1)
        layout.addWidget(rule)

        footer = QPushButton("QUANTIS")
        footer.setObjectName("navWordmark")
        footer.setEnabled(False)
        layout.addWidget(footer)
        layout.addSpacing(14)

        self.set_active_page(0)

    def set_active_page(self, page_id: int) -> None:
        button = self._group.button(page_id)
        if button is not None and not button.isChecked():
            self._group.blockSignals(True)
            button.setChecked(True)
            self._group.blockSignals(False)
