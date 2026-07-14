from __future__ import annotations

import math

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QRadialGradient
from PySide6.QtWidgets import QFrame, QWidget


class BackgroundFrame(QFrame):
    """Каркас окна: атмосфера темы + медленный aurora-pulse."""

    def __init__(
        self,
        wallpaper: str | None = None,
        variant: str = "neon",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("appShell")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self._variant = variant
        self._phase = 0.0
        _ = wallpaper

        self._content = QWidget(self)
        self._content.setObjectName("appContent")
        self._content.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self._content.setAutoFillBackground(False)
        self._content.setStyleSheet("background: transparent;")

        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def content_host(self) -> QWidget:
        return self._content

    def set_variant(self, variant: str) -> None:
        if self._variant != variant:
            self._variant = variant
            self.update()

    def _tick(self) -> None:
        if self._variant not in ("neon", "yellow_dark", "classic"):
            return
        self._phase = (self._phase + 0.012) % (math.tau)
        self.update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._content.setGeometry(self.rect())

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        w, h = rect.width(), rect.height()

        bases = {
            "light": QColor(210, 216, 226),
            "yellow_dark": QColor(14, 10, 5),
            "editorial": QColor(10, 10, 12),
            "classic": QColor(10, 12, 16),
            "neon": QColor(3, 5, 12),
        }
        painter.fillRect(rect, bases.get(self._variant, QColor(5, 6, 12)))

        # Мягкий вертикальный «глубинный» градиент
        depth = QLinearGradient(0, 0, 0, h)
        if self._variant == "light":
            depth.setColorAt(0.0, QColor(255, 255, 255, 40))
            depth.setColorAt(1.0, QColor(140, 150, 170, 50))
        elif self._variant == "yellow_dark":
            depth.setColorAt(0.0, QColor(40, 24, 8, 50))
            depth.setColorAt(1.0, QColor(0, 0, 0, 90))
        else:
            depth.setColorAt(0.0, QColor(20, 40, 70, 45))
            depth.setColorAt(0.55, QColor(0, 0, 0, 0))
            depth.setColorAt(1.0, QColor(0, 0, 0, 110))
        painter.fillRect(rect, depth)

        if self._variant == "editorial":
            painter.end()
            return

        pulse = 0.5 + 0.5 * math.sin(self._phase)
        pulse2 = 0.5 + 0.5 * math.sin(self._phase + 2.1)

        if self._variant == "neon":
            # Aurora — верхний правый cyan, нижний левый coral
            cx = w * (0.78 + 0.06 * math.sin(self._phase * 0.7))
            cy = h * (0.08 + 0.04 * pulse)
            glow = QRadialGradient(cx, cy, w * (0.42 + 0.04 * pulse))
            glow.setColorAt(0.0, QColor(46, 230, 255, int(34 + 14 * pulse)))
            glow.setColorAt(0.45, QColor(46, 230, 255, int(10 + 6 * pulse)))
            glow.setColorAt(1.0, QColor(46, 230, 255, 0))
            painter.fillRect(rect, glow)

            mx = w * (0.12 + 0.05 * math.cos(self._phase * 0.55))
            my = h * (0.85 - 0.05 * pulse2)
            coral = QRadialGradient(mx, my, w * (0.38 + 0.05 * pulse2))
            coral.setColorAt(0.0, QColor(255, 92, 122, int(28 + 12 * pulse2)))
            coral.setColorAt(0.5, QColor(255, 92, 122, 8))
            coral.setColorAt(1.0, QColor(255, 92, 122, 0))
            painter.fillRect(rect, coral)

            # Тонкий центральный teal bloom
            mid = QRadialGradient(w * 0.5, h * 0.45, w * 0.55)
            mid.setColorAt(0.0, QColor(20, 180, 200, int(8 + 6 * pulse)))
            mid.setColorAt(1.0, QColor(20, 180, 200, 0))
            painter.fillRect(rect, mid)

        elif self._variant == "yellow_dark":
            glow = QRadialGradient(w * 0.85, h * 0.05, w * 0.4)
            glow.setColorAt(0.0, QColor(255, 170, 0, int(26 + 10 * pulse)))
            glow.setColorAt(1.0, QColor(255, 170, 0, 0))
            painter.fillRect(rect, glow)
            warm = QRadialGradient(w * 0.15, h * 0.9, w * 0.35)
            warm.setColorAt(0.0, QColor(255, 100, 40, int(18 + 8 * pulse2)))
            warm.setColorAt(1.0, QColor(255, 100, 40, 0))
            painter.fillRect(rect, warm)

        elif self._variant == "classic":
            glow = QRadialGradient(w * 0.7, 0, w * 0.5)
            glow.setColorAt(0.0, QColor(90, 130, 180, int(18 + 8 * pulse)))
            glow.setColorAt(1.0, QColor(90, 130, 180, 0))
            painter.fillRect(rect, glow)

        # Виньетка
        radius = max(w, h) * 0.78
        vignette = QRadialGradient(rect.center(), radius)
        vignette.setColorAt(0.4, QColor(0, 0, 0, 0))
        if self._variant == "light":
            vignette.setColorAt(1.0, QColor(255, 255, 255, 70))
        else:
            vignette.setColorAt(1.0, QColor(0, 0, 0, 170))
        painter.fillRect(rect, vignette)
        painter.end()
