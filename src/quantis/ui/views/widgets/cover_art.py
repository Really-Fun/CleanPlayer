"""Загрузка и отрисовка обложек треков и плейлистов."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPixmap

from quantis.models.track import Track
from quantis.providers.path_provider import PathProvider

_GRAD_YT = (QColor(220, 50, 50), QColor(140, 30, 30))
_GRAD_YA = (QColor(0, 180, 220), QColor(80, 60, 200))


def gradient_for_name(name: str) -> tuple[QColor, QColor]:
    seed = sum(ord(ch) for ch in name) or 1
    hues = [
        (0, 229, 255),
        (230, 59, 46),
        (255, 42, 127),
        (120, 90, 255),
        (255, 170, 0),
        (46, 204, 113),
        (155, 89, 182),
    ]
    a = hues[seed % len(hues)]
    b = hues[(seed * 3 + 2) % len(hues)]
    return QColor(*a), QColor(*b)


def track_cover_file(track: Track) -> Path:
    return Path(PathProvider().get_cover_path(track))


def load_cover_pixmap(path: str | Path | None, size: int) -> QPixmap | None:
    if not path:
        return None
    file_path = Path(path)
    if not file_path.is_file():
        return None
    if file_path.suffix.lower() == ".svg":
        pixmap = QIcon(str(file_path)).pixmap(QSize(size, size))
        return None if pixmap.isNull() else pixmap
    pixmap = QPixmap(str(file_path))
    if pixmap.isNull():
        return None
    return pixmap.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )


def paint_rounded_cover(
    painter: QPainter,
    rect,
    *,
    label: str,
    pixmap: QPixmap | None = None,
    source_key: str = "",
    radius: int = 8,
) -> None:
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    if pixmap is not None and not pixmap.isNull():
        painter.setClipRect(rect)
        painter.drawPixmap(rect, pixmap)
        painter.setClipping(False)
    else:
        key = str(source_key).lower()
        if key == "youtube":
            c1, c2 = _GRAD_YT
        elif key == "yandex":
            c1, c2 = _GRAD_YA
        else:
            c1, c2 = gradient_for_name(label)
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0.0, c1)
        grad.setColorAt(1.0, c2)
        painter.setBrush(grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, radius, radius)
        initial = (label[:1] or "?").upper()
        painter.setPen(QColor(255, 255, 255, 230))
        painter.setFont(QFont("Segoe UI", max(9, rect.width() // 4), QFont.Weight.Bold))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, initial)

    painter.restore()
