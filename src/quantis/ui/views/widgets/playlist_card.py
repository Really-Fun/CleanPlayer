from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget, QSizePolicy

from quantis.models.playlist import Playlist
from quantis.ui.views.widgets.cover_art import load_cover_pixmap, paint_rounded_cover


class GradientCover(QWidget):
    """Обложка: файл (jpg/png/svg) или градиент с буквой."""

    def __init__(
        self,
        name: str,
        *,
        size: int = 120,
        image_path: str | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._name = name
        self._image_path = image_path
        self._size = size
        self._pixmap: QPixmap | None = None
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self._reload_pixmap()

    def set_content(self, name: str, image_path: str | None = None) -> None:
        if self._name == name and self._image_path == image_path:
            return
        self._name = name
        self._image_path = image_path
        self._reload_pixmap()
        self.update()

    def set_name(self, name: str) -> None:
        self.set_content(name, self._image_path)

    def _reload_pixmap(self) -> None:
        inner = max(8, self._size - 12)
        self._pixmap = load_cover_pixmap(self._image_path, inner)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        rect = self.rect().adjusted(0, 0, -1, -1)
        radius = min(12, rect.width() // 6)
        paint_rounded_cover(
            painter,
            rect,
            label=self._name,
            pixmap=self._pixmap,
            radius=radius,
        )
        painter.end()

class PlaylistCard(QFrame):
    """Карточка плейлиста в стиле стриминговых сервисов."""

    activated = Signal(object)

    def __init__(self, playlist: Playlist, parent=None) -> None:
        super().__init__(parent)
        self._playlist = playlist
        self.setObjectName("playlistCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(168, 210)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self._cover = GradientCover(
            playlist.name,
            size=120,
            image_path=playlist.cover_path,
        )
        layout.addWidget(self._cover, alignment=Qt.AlignmentFlag.AlignHCenter)

        title = QLabel(playlist.name)
        title.setObjectName("playlistCardTitle")
        title.setWordWrap(True)
        layout.addWidget(title)

        count = len(playlist)
        tracks_label = QLabel(self._tracks_label(count))
        tracks_label.setObjectName("playlistCardMeta")
        layout.addWidget(tracks_label)
        layout.addStretch()

    @property
    def playlist(self) -> Playlist:
        return self._playlist

    @staticmethod
    def _tracks_label(count: int) -> str:
        if count % 10 == 1 and count % 100 != 11:
            suffix = "трек"
        elif count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
            suffix = "трека"
        else:
            suffix = "треков"
        return f"{count} {suffix}"

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.activated.emit(self._playlist)
        super().mouseReleaseEvent(event)


class QuickPickTile(QFrame):
    """Широкая плитка быстрого доступа (как верхняя сетка Spotify)."""

    activated = Signal(object)

    def __init__(self, playlist: Playlist, parent=None) -> None:
        super().__init__(parent)
        self._playlist = playlist
        self.setObjectName("quickPickTile")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(64)
        self.setMinimumWidth(200)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 16, 0)
        layout.setSpacing(0)

        self._thumb = GradientCover(
            playlist.name,
            size=64,
            image_path=playlist.cover_path,
        )
        layout.addWidget(self._thumb)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(14, 10, 0, 10)
        text_col.setSpacing(2)
        title = QLabel(playlist.name)
        title.setObjectName("quickPickTitle")
        text_col.addWidget(title)
        meta = QLabel(PlaylistCard._tracks_label(len(playlist)))
        meta.setObjectName("quickPickMeta")
        text_col.addWidget(meta)
        layout.addLayout(text_col, stretch=1)

    @property
    def playlist(self) -> Playlist:
        return self._playlist

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.activated.emit(self._playlist)
        super().mouseReleaseEvent(event)
