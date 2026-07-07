from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPixmap, QRadialGradient
from PySide6.QtWidgets import QFrame


class BackgroundFrame(QFrame):
    """Фон: мягкие обои и виньетка."""

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
        self._wallpaper = QPixmap(str(wallpaper)) if wallpaper else QPixmap()
        self._cached = QPixmap()
        self._cache_size = (0, 0)

    def set_variant(self, variant: str) -> None:
        if self._variant != variant:
            self._variant = variant
            self.update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._rebuild_cache()

    def _rebuild_cache(self) -> None:
        size = self.size()
        if size.width() <= 0 or size.height() <= 0 or self._wallpaper.isNull():
            self._cached = QPixmap()
            return
        if (size.width(), size.height()) == self._cache_size and not self._cached.isNull():
            return
        self._cached = self._wallpaper.scaled(
            size,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._cache_size = (size.width(), size.height())

    def _wallpaper_opacity(self) -> float:
        return {
            "classic": 0.12,
            "neon": 0.11,
            "editorial": 0.0,
            "light": 0.14,
            "yellow_dark": 0.11,
        }.get(self._variant, 0.10)

    def paintEvent(self, event) -> None:
        if self._cached.isNull() and not self._wallpaper.isNull():
            self._rebuild_cache()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        rect = self.rect()

        bases = {
            "light": QColor(198, 204, 214),
            "yellow_dark": QColor(16, 12, 6),
            "editorial": QColor(12, 12, 14),
            "classic": QColor(14, 16, 20),
            "neon": QColor(4, 3, 12),
        }
        painter.fillRect(rect, bases.get(self._variant, QColor(5, 6, 12)))

        if self._variant != "editorial" and not self._cached.isNull():
            painter.setOpacity(self._wallpaper_opacity())
            x = (rect.width() - self._cached.width()) // 2
            y = (rect.height() - self._cached.height()) // 2
            painter.drawPixmap(x, y, self._cached)
            painter.setOpacity(1.0)

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
