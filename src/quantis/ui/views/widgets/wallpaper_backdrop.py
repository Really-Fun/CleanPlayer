from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap, QRadialGradient
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer, QVideoFrame, QVideoSink
from PySide6.QtWidgets import QHBoxLayout, QWidget


class _VideoSurface(QWidget):
    """Видео через QVideoSink — рисуется под UI, без нативного оверлея."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._sink = QVideoSink(self)
        self._image = QImage()
        self._opacity = 0.28
        self._sink.videoFrameChanged.connect(self._on_frame)

    @property
    def sink(self) -> QVideoSink:
        return self._sink

    def set_opacity(self, value: float) -> None:
        self._opacity = max(0.05, min(1.0, value))
        self.update()

    def clear(self) -> None:
        self._image = QImage()
        self.update()

    def _on_frame(self, frame: QVideoFrame) -> None:
        if not frame.isValid():
            return
        mapped = QVideoFrame(frame)
        if not mapped.map(QVideoFrame.MapMode.ReadOnly):
            return
        try:
            self._image = mapped.toImage()
        finally:
            mapped.unmap()
        self.update()

    def paintEvent(self, event) -> None:
        if self._image.isNull():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setOpacity(self._opacity)
        rect = self.rect()
        scaled = self._image.scaled(
            rect.size(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = (rect.width() - scaled.width()) // 2
        y = (rect.height() - scaled.height()) // 2
        painter.drawImage(x, y, scaled)
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
        self._wallpaper = QPixmap(str(wallpaper)) if wallpaper else QPixmap()
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

    def set_variant(self, variant: str) -> None:
        if self._variant != variant:
            self._variant = variant
            self.update()

    def set_dynamic_wallpaper_enabled(self, enabled: bool) -> None:
        self._dynamic_enabled = enabled
        if not enabled:
            self.stop_video()
        else:
            self.update()

    def play_video_file(self, path: str | Path) -> None:
        if not self._dynamic_enabled:
            return
        file_path = Path(path)
        if not file_path.is_file():
            return
        self._video_active = True
        self._video_surface.show()
        self.lower()
        self._video_player.setSource(QUrl.fromLocalFile(str(file_path.resolve())))
        self._video_player.play()
        self.update()

    def stop_video(self) -> None:
        self._video_active = False
        self._video_player.stop()
        self._video_surface.clear()
        self._video_surface.hide()
        self.update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._video_surface.setGeometry(self.rect())
        self._rebuild_cache()

    def _loop_video(self, status: QMediaPlayer.MediaStatus) -> None:
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._video_player.setPosition(0)
            self._video_player.play()

    def _on_video_error(self, _error: QMediaPlayer.Error, message: str) -> None:
        import logging

        logging.getLogger(__name__).warning("Видео-фон: %s", message)
        self.stop_video()

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
        if self._video_active:
            return

        if self._cached.isNull() and not self._wallpaper.isNull():
            self._rebuild_cache()

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

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        rect = self.rect()
        self._backdrop.setGeometry(rect)
        self._foreground.setGeometry(rect)
        self._backdrop.lower()
        self._foreground.raise_()
