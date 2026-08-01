from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from quantis.models.playlist import Playlist
from quantis.ui.views.widgets.cover_art import (
    gradient_for_name,
    load_cover_pixmap,
    paint_rounded_cover,
    playlist_cover_path,
)


class GradientCover(QWidget):
    """Обложка: файл или градиент с буквой."""

    def __init__(
        self,
        name: str,
        *,
        size: int = 140,
        image_path: str | None = None,
        radius: int = 16,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._name = name
        self._image_path = image_path
        self._size = size
        self._radius = radius
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
        self._pixmap = load_cover_pixmap(self._image_path, self._size)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        paint_rounded_cover(
            painter,
            self.rect(),
            label=self._name,
            pixmap=self._pixmap,
            radius=self._radius,
        )
        painter.end()


class PlaylistCard(QFrame):
    """Карточка плейлиста — обложка крупно, подпись снизу (shelf-стиль)."""

    activated = Signal(object)

    def __init__(self, playlist: Playlist, parent=None) -> None:
        super().__init__(parent)
        self._playlist = playlist
        self.setObjectName("playlistCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedWidth(156)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Maximum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self._cover = GradientCover(
            playlist.name,
            size=156,
            image_path=playlist_cover_path(playlist),
            radius=18,
        )
        layout.addWidget(self._cover)

        title = QLabel(playlist.name)
        title.setObjectName("playlistCardTitle")
        title.setWordWrap(True)
        title.setMaximumHeight(36)
        layout.addWidget(title)

        tracks_label = QLabel(self._tracks_label(len(playlist)))
        tracks_label.setObjectName("playlistCardMeta")
        layout.addWidget(tracks_label)

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

    def enterEvent(self, event) -> None:
        self.setProperty("hovered", True)
        self.style().unpolish(self)
        self.style().polish(self)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.setProperty("hovered", False)
        self.style().unpolish(self)
        self.style().polish(self)
        super().leaveEvent(event)


class QuickPickTile(QFrame):
    """Плитка быстрого доступа — цветной акцент + обложка."""

    activated = Signal(object)

    def __init__(self, playlist: Playlist, parent=None) -> None:
        super().__init__(parent)
        self._playlist = playlist
        self.setObjectName("quickPickTile")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(72)
        self.setMinimumWidth(180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._accent = gradient_for_name(playlist.name)[0]

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 14, 0)
        layout.setSpacing(0)

        self._thumb = GradientCover(
            playlist.name,
            size=72,
            image_path=playlist_cover_path(playlist),
            radius=14,
        )
        layout.addWidget(self._thumb)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(14, 12, 0, 12)
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

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(self.rect().adjusted(0, 0, -1, -1), 14, 14)
        painter.fillPath(path, QColor(12, 16, 28, 210))
        # Цветная полоска слева
        bar = QPainterPath()
        bar.addRoundedRect(0, 10, 4, self.height() - 20, 2, 2)
        accent = QColor(self._accent)
        accent.setAlpha(200)
        painter.fillPath(bar, accent)
        painter.end()
        super().paintEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.activated.emit(self._playlist)
        super().mouseReleaseEvent(event)


class PlaylistShelf(QWidget):
    """Горизонтальная полка карточек плейлистов."""

    playlist_activated = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("playlistShelf")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("playlistShelfScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setFixedHeight(232)

        self._host = QWidget()
        self._host.setObjectName("playlistShelfHost")
        self._row = QHBoxLayout(self._host)
        self._row.setContentsMargins(0, 4, 8, 4)
        self._row.setSpacing(16)
        self._row.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._scroll.setWidget(self._host)
        outer.addWidget(self._scroll)

    def set_playlists(self, playlists: list[Playlist]) -> None:
        while self._row.count():
            item = self._row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if not playlists:
            empty = QLabel("Создай плейлист кнопкой «+ Плейлист» или добавь трек из плеера")
            empty.setObjectName("homeEmptyHint")
            self._row.addWidget(empty)
            return

        for playlist in playlists:
            card = PlaylistCard(playlist)
            card.activated.connect(self.playlist_activated.emit)
            self._row.addWidget(card)
        self._row.addStretch(1)
