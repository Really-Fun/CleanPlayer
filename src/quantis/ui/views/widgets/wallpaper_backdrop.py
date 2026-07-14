from __future__ import annotations

from pathlib import Path
from time import monotonic

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap, QRadialGradient
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer, QVideoFrame, QVideoSink
from PySide6.QtWidgets import QHBoxLayout, QWidget

from quantis.ui.views.widgets.cover_art import load_wallpaper_pixmap

# Лимит fps для видео-фона: меньше кадров → меньше QImage в ОЗУ/CPU.
_VIDEO_MIN_INTERVAL_SEC = 1.0 / 15.0
_WALLPAPER_MAX_SIDE = 1920


class _VideoSurface(QWidget):
    """Видео через QVideoSink — рисуется под UI, без нативного оверлея."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._sink = QVideoSink(self)
        self._scaled = QImage()
        self._opacity = 0.28
        self._last_frame_at = 0.0
        self._sink.videoFrameChanged.connect(self._on_frame)

    @property
    def sink(self) -> QVideoSink:
        return self._sink

    def set_opacity(self, value: float) -> None:
        self._opacity = max(0.05, min(1.0, value))
        self.update()

    def clear(self) -> None:
        self._scaled = QImage()
        self._last_frame_at = 0.0
        self.update()

    def _on_frame(self, frame: QVideoFrame) -> None:
        if not frame.isValid():
            return
        now = monotonic()
        if now - self._last_frame_at < _VIDEO_MIN_INTERVAL_SEC:
            return
        self._last_frame_at = now

        mapped = QVideoFrame(frame)
        if not mapped.map(QVideoFrame.MapMode.ReadOnly):
            return
        try:
            image = mapped.toImage()
        finally:
            mapped.unmap()

        if image.isNull():
            return

        target = self.size()
        if target.width() <= 0 or target.height() <= 0:
            return

        # Сразу даунскейл до размера виджета — полный кадр не храним.
        self._scaled = image.scaled(
            target,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.FastTransformation,
        )
        self.update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        # Размер изменился — следующий кадр пересоберёт scaled под новый size.
        if not self._scaled.isNull():
            self._scaled = QImage()

    def paintEvent(self, event) -> None:
        if self._scaled.isNull():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setOpacity(self._opacity)
        rect = self.rect()
        x = (rect.width() - self._scaled.width()) // 2
        y = (rect.height() - self._scaled.height()) // 2
        painter.drawImage(x, y, self._scaled)
        painter.setOpacity(1.0)

        radius = max(rect.width(), rect.height()) * 0.7
        vignette = QRadialGradient(rect.center(), radius)
        vignette.setColorAt(0.4, QColor(0, 0, 0, 0))
        vignette.setColorAt(1.0, QColor(0, 0, 0, 140))
        painter.fillRect(rect, vignette)
        painter.end()


class WallpaperBackdrop(QWidget):
    """Слой обоев: статичный jpg или видео-клип (только в зоне контента)."""

    def __init__(
        self,
        wallpaper: str | Path | None = None,
        variant: str = "neon",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("wallpaperBackdrop")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._variant = variant
        self._wallpaper_path: str | None = str(wallpaper) if wallpaper else None
        self._cached = QPixmap()
        self._cache_size = (0, 0)
        self._dynamic_enabled = False
        self._video_active = False

        self._video_surface = _VideoSurface(self)
        self._video_surface.hide()

        self._video_player = QMediaPlayer(self)
        self._video_audio = QAudioOutput(self)
        self._video_audio.setVolume(0.0)
        self._video_player.setAudioOutput(self._video_audio)
        self._video_player.setVideoSink(self._video_surface.sink)
        loops = getattr(QMediaPlayer, "Loops", None)
        if loops is not None:
            self._video_player.setLoops(loops.Infinite)
        else:
            self._video_player.mediaStatusChanged.connect(self._loop_video)
        self._video_player.errorOccurred.connect(self._on_video_error)

        if self._wallpaper_path:
            self._rebuild_cache(force=True)

    def set_variant(self, variant: str) -> None:
        if self._variant != variant:
            self._variant = variant
            self.update()

    def set_wallpaper(self, path: str | Path | None) -> None:
        new_path = str(path) if path else None
        if new_path == self._wallpaper_path and not self._cached.isNull():
            return
        self._wallpaper_path = new_path
        self._cache_size = (0, 0)
        self._cached = QPixmap()
        self._rebuild_cache(force=True)
        self.update()

    def set_dynamic_wallpaper_enabled(self, enabled: bool) -> None:
        self._dynamic_enabled = enabled
        if not enabled:
            self.stop_video()
        else:
            # Видео активно — освобождаем статичный кэш.
            self._cached = QPixmap()
            self._cache_size = (0, 0)
            self.update()

    def play_video_url(self, url: str) -> None:
        if not self._dynamic_enabled or not url:
            return
        self._video_active = True
        self._cached = QPixmap()
        self._cache_size = (0, 0)
        self._video_surface.show()
        self.lower()
        self._video_player.setSource(QUrl(url))
        self._video_player.play()
        self.update()

    def stop_video(self) -> None:
        self._video_active = False
        self._video_player.stop()
        self._video_surface.clear()
        self._video_surface.hide()
        if not self._dynamic_enabled:
            self._rebuild_cache(force=True)
        self.update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._video_surface.setGeometry(self.rect())
        if not self._video_active and not self._dynamic_enabled:
            self._rebuild_cache()

    def _loop_video(self, status: QMediaPlayer.MediaStatus) -> None:
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._video_player.setPosition(0)
            self._video_player.play()

    def _on_video_error(self, _error: QMediaPlayer.Error, message: str) -> None:
        import logging

        logging.getLogger(__name__).warning("Видео-фон: %s", message)
        self.stop_video()

    def _rebuild_cache(self, *, force: bool = False) -> None:
        size = self.size()
        if size.width() <= 0 or size.height() <= 0 or not self._wallpaper_path:
            self._cached = QPixmap()
            return
        if (
            not force
            and (size.width(), size.height()) == self._cache_size
            and not self._cached.isNull()
        ):
            return

        # Декод с лимитом стороны, сразу в размер окна — полный 4K не держим.
        source = load_wallpaper_pixmap(self._wallpaper_path, _WALLPAPER_MAX_SIDE)
        if source.isNull():
            self._cached = QPixmap()
            return
        self._cached = source.scaled(
            size,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.FastTransformation,
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
        if self._video_active:
            return

        if self._cached.isNull() and self._wallpaper_path and not self._dynamic_enabled:
            self._rebuild_cache(force=True)

        if self._dynamic_enabled or self._variant == "editorial" or self._cached.isNull():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        rect = self.rect()
        painter.setOpacity(self._wallpaper_opacity())
        x = (rect.width() - self._cached.width()) // 2
        y = (rect.height() - self._cached.height()) // 2
        painter.drawPixmap(x, y, self._cached)
        painter.end()


class BodyWithWallpaper(QWidget):
    """Контентная зона: обои/видео сзади, nav + страницы спереди."""

    def __init__(
        self,
        wallpaper: str | Path | None = None,
        variant: str = "neon",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("bodyWithWallpaper")
        self._backdrop = WallpaperBackdrop(wallpaper, variant, self)
        self._foreground = QWidget(self)
        self._foreground.setObjectName("bodyForeground")
        self._foreground.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self._foreground.setAutoFillBackground(False)
        self._foreground.setStyleSheet("background: transparent;")
        self._layout = QHBoxLayout(self._foreground)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

    @property
    def backdrop(self) -> WallpaperBackdrop:
        return self._backdrop

    @property
    def layout_host(self):
        return self._layout

    def set_variant(self, variant: str) -> None:
        self._backdrop.set_variant(variant)

    def set_wallpaper(self, path: str | Path | None) -> None:
        self._backdrop.set_wallpaper(path)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        rect = self.rect()
        self._backdrop.setGeometry(rect)
        self._foreground.setGeometry(rect)
        self._backdrop.lower()
        self._foreground.raise_()
