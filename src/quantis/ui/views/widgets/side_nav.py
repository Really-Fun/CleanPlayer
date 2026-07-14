from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QRect,
    QSize,
    Qt,
    Signal,
    Property,
)
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QButtonGroup, QFrame, QToolButton, QVBoxLayout, QWidget

from quantis.ui import resources


class SideNavRail(QFrame):
    """Плавающая стеклянная рейка с анимированным индикатором активной вкладки."""

    page_changed = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sideNavRail")
        self.setFixedWidth(76)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 16, 10, 16)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: dict[int, QToolButton] = {}

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
            layout.addWidget(
                self._make_button(icon, tooltip, page_id),
                0,
                Qt.AlignmentFlag.AlignHCenter,
            )

        layout.addStretch()

        for icon, tooltip, page_id in bottom_items:
            layout.addWidget(
                self._make_button(icon, tooltip, page_id),
                0,
                Qt.AlignmentFlag.AlignHCenter,
            )

        self._indicator_y = 0.0
        self._indicator_h = 44.0
        self._anim = QPropertyAnimation(self, b"indicatorY", self)
        self._anim.setDuration(280)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.set_active_page(0)

    def _get_indicator_y(self) -> float:
        return self._indicator_y

    def _set_indicator_y(self, value: float) -> None:
        self._indicator_y = value
        self.update()

    indicatorY = Property(float, _get_indicator_y, _set_indicator_y)

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
        self._buttons[page_id] = button
        return button

    def set_active_page(self, page_id: int) -> None:
        button = self._group.button(page_id)
        if button is None:
            return
        if not button.isChecked():
            self._group.blockSignals(True)
            button.setChecked(True)
            self._group.blockSignals(False)
        self._move_indicator_to(button)

    def _move_indicator_to(self, button: QToolButton) -> None:
        geo = button.geometry()
        target = float(geo.y())
        self._indicator_h = float(geo.height())
        if abs(self._indicator_y - target) < 0.5:
            self._indicator_y = target
            self.update()
            return
        self._anim.stop()
        self._anim.setStartValue(self._indicator_y)
        self._anim.setEndValue(target)
        self._anim.start()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        checked = self._group.checkedButton()
        if checked is not None:
            self._indicator_y = float(checked.geometry().y())
            self._indicator_h = float(checked.geometry().height())
            self.update()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        checked = self._group.checkedButton()
        if checked is not None:
            self._indicator_y = float(checked.geometry().y())
            self._indicator_h = float(checked.geometry().height())

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Мягкая капсула-индикатор за активной кнопкой
        margin_x = 8
        rect = QRect(
            margin_x,
            int(self._indicator_y),
            self.width() - margin_x * 2,
            int(self._indicator_h),
        )
        path = QPainterPath()
        path.addRoundedRect(rect, 14, 14)
        painter.fillPath(path, QColor(46, 230, 255, 36))

        # Тонкая cyan-черта слева
        bar = QRect(4, rect.y() + 10, 3, rect.height() - 20)
        bar_path = QPainterPath()
        bar_path.addRoundedRect(bar, 2, 2)
        painter.fillPath(bar_path, QColor(46, 230, 255, 210))
        painter.end()
