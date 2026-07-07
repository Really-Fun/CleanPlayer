from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPixmap, QRadialGradient
from PySide6.QtWidgets import QFrame, QWidget


class BackgroundFrame(QFrame):
    """Каркас окна: базовый цвет темы и виньетка (без jpg — обои в BodyWithWallpaper)."""

    def __init__(
        self,
        wallpaper: str | Path | None = None,
        variant: str = "neon",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("appShell")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self._variant = variant
        # wallpaper arg kept for API compat; decorative jpg lives in WallpaperBackdrop
        _ = wallpaper

        self._content = QWidget(self)
        self._content.setObjectName("appContent")
        self._content.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self._content.setAutoFillBackground(False)
        self._content.setStyleSheet("background: transparent;")

    def content_host(self) -> QWidget:
        return self._content

    def set_variant(self, variant: str) -> None:
        if self._variant != variant:
            self._variant = variant
            self.update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._content.setGeometry(self.rect())

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        rect = self.rect()

        bases = {
            "light": QColor(198, 204, 214),
            "yellow_dark": QColor(16, 12, 6),
            "editorial": QColor(12, 12, 14),
            "classic": QColor(14, 16, 20),
            "neon": QColor(4, 3, 12),
        }
        painter.fillRect(rect, bases.get(self._variant, QColor(5, 6, 12)))

        radius = max(rect.width(), rect.height()) * 0.72
        vignette = QRadialGradient(rect.center(), radius)
        vignette.setColorAt(0.45, QColor(0, 0, 0, 0))
        if self._variant == "light":
            vignette.setColorAt(1.0, QColor(255, 255, 255, 80))
        else:
            vignette.setColorAt(1.0, QColor(0, 0, 0, 160))
        painter.fillRect(rect, vignette)

        if self._variant == "editorial":
            painter.end()
            return

        if self._variant == "neon":
            glow = QRadialGradient(
                rect.width() * 0.88, rect.height() * 0.0, rect.width() * 0.45
            )
            glow.setColorAt(0.0, QColor(0, 229, 255, 22))
            glow.setColorAt(1.0, QColor(0, 229, 255, 0))
            painter.fillRect(rect, glow)
            magenta = QRadialGradient(
                rect.width() * 0.1, rect.height() * 0.9, rect.width() * 0.4
            )
            magenta.setColorAt(0.0, QColor(255, 42, 127, 18))
            magenta.setColorAt(1.0, QColor(255, 42, 127, 0))
            painter.fillRect(rect, magenta)

        painter.end()
