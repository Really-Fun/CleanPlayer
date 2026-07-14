"""Загрузка и отрисовка обложек треков и плейлистов."""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import (
    QColor,
    QFont,
    QIcon,
    QImageReader,
    QLinearGradient,
    QPainter,
    QPixmap,
)

from quantis.models.track import Track
from quantis.providers.path_provider import PathProvider

_GRAD_YT = (QColor(220, 50, 50), QColor(140, 30, 30))
_GRAD_YA = (QColor(0, 180, 220), QColor(80, 60, 200))

# Общий LRU: ключ "(path|track)|size" → pixmap. Ограничивает рост ОЗУ.
_COVER_CACHE_MAX = 96
_cover_lru: OrderedDict[str, QPixmap | None] = OrderedDict()


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


def clear_cover_cache() -> None:
    _cover_lru.clear()


def invalidate_cover_path(path: str | Path | None) -> None:
    if not path:
        return
    prefix = str(Path(path).resolve() if Path(path).exists() else Path(path))
    dead = [key for key in _cover_lru if key.startswith(prefix)]
    for key in dead:
        _cover_lru.pop(key, None)


def playlist_cover_path(playlist) -> str | None:
    """Обложка плейлиста: своя → иначе обложка первого трека."""
    cover = getattr(playlist, "cover_path", None)
    if cover:
        path = Path(cover)
        if path.is_file() or path.suffix.lower() == ".svg":
            return str(path)
    tracks = getattr(getattr(playlist, "tracks", None), "values", None)
    if tracks:
        return str(track_cover_file(tracks[0]))
    return cover


def _cache_get(key: str) -> QPixmap | None | object:
    """Возвращает pixmap / None / sentinel object если ключа нет."""
    if key not in _cover_lru:
        return _MISSING
    _cover_lru.move_to_end(key)
    return _cover_lru[key]


_MISSING = object()


def _cache_put(key: str, value: QPixmap | None) -> QPixmap | None:
    _cover_lru[key] = value
    _cover_lru.move_to_end(key)
    while len(_cover_lru) > _COVER_CACHE_MAX:
        _cover_lru.popitem(last=False)
    return value


def load_cover_pixmap(path: str | Path | None, size: int) -> QPixmap | None:
    """Декодирует обложку сразу в нужный размер (без полного jpg в ОЗУ)."""
    if not path:
        return None
    file_path = Path(path)
    cache_key = f"{file_path.resolve() if file_path.exists() else file_path}|{size}"
    cached = _cache_get(cache_key)
    if cached is not _MISSING:
        return cached  # type: ignore[return-value]

    if not file_path.is_file():
        return _cache_put(cache_key, None)

    if file_path.suffix.lower() == ".svg":
        pixmap = QIcon(str(file_path)).pixmap(QSize(size, size))
        return _cache_put(cache_key, None if pixmap.isNull() else pixmap)

    reader = QImageReader(str(file_path))
    reader.setAutoTransform(True)
    original = reader.size()
    if original.isValid() and (original.width() > size or original.height() > size):
        # KeepAspectRatioByExpanding ≈ scale so shorter side == size
        w, h = original.width(), original.height()
        if w < h:
            target = QSize(size, max(1, int(h * size / w)))
        else:
            target = QSize(max(1, int(w * size / h)), size)
        reader.setScaledSize(target)

    image = reader.read()
    if image.isNull():
        return _cache_put(cache_key, None)

    pixmap = QPixmap.fromImage(image)
    if pixmap.width() != size or pixmap.height() != size:
        pixmap = pixmap.scaled(
            size,
            size,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.FastTransformation,
        )
        if pixmap.width() > size or pixmap.height() > size:
            x = max(0, (pixmap.width() - size) // 2)
            y = max(0, (pixmap.height() - size) // 2)
            pixmap = pixmap.copy(x, y, size, size)
    return _cache_put(cache_key, pixmap)


def load_track_cover(track: Track, size: int) -> QPixmap | None:
    return load_cover_pixmap(track_cover_file(track), size)


def load_wallpaper_pixmap(path: str | Path | None, max_side: int = 1920) -> QPixmap:
    """Декодирует обои с ограничением длинной стороны (экономия ОЗУ на 4K)."""
    if not path:
        return QPixmap()
    file_path = Path(path)
    if not file_path.is_file():
        return QPixmap()

    reader = QImageReader(str(file_path))
    reader.setAutoTransform(True)
    original = reader.size()
    if original.isValid():
        w, h = original.width(), original.height()
        longest = max(w, h)
        if longest > max_side:
            scale = max_side / longest
            reader.setScaledSize(QSize(max(1, int(w * scale)), max(1, int(h * scale))))

    image = reader.read()
    if image.isNull():
        return QPixmap()
    return QPixmap.fromImage(image)


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
