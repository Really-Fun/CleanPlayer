from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap
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


def playlist_tracks_label(count: int) -> str:
    if count % 10 == 1 and count % 100 != 11:
        suffix = "трек"
    elif count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        suffix = "трека"
    else:
        suffix = "треков"
    return f"{count} {suffix}"


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

        tracks_label = QLabel(playlist_tracks_label(len(playlist)))
        tracks_label.setObjectName("playlistCardMeta")
        layout.addWidget(tracks_label)

    @property
    def playlist(self) -> Playlist:
        return self._playlist

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
    """Стеклянная плитка быстрого доступа — как карточка «Моя волна»."""

    activated = Signal(object)

    def __init__(self, playlist: Playlist, parent=None) -> None:
        super().__init__(parent)
        self._playlist = playlist
        self._hovered = False
        self.setObjectName("quickPickTile")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(248, 72)

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
        title.setWordWrap(False)
        title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        text_col.addWidget(title)
        meta = QLabel(playlist_tracks_label(len(playlist)))
        meta.setObjectName("quickPickMeta")
        text_col.addWidget(meta)
        layout.addLayout(text_col, stretch=1)

    @property
    def playlist(self) -> Playlist:
        return self._playlist

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(rect, 14, 14)
        painter.fillPath(path, QColor(255, 255, 255, 14 if self._hovered else 10))
        pen = QPen(QColor(46, 230, 255, 70 if self._hovered else 40))
        pen.setWidthF(1.0)
        painter.setPen(pen)
        painter.drawPath(path)
        painter.end()

    def enterEvent(self, event) -> None:
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.activated.emit(self._playlist)
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event) -> None:
        event.ignore()


class QuickPickShelf(QWidget):
    """Горизонтальная полка стеклянных плиток — колесо мыши листает вбок."""

    playlist_activated = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("quickPickShelf")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(84)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("quickPickShelfScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setFixedHeight(84)
        self._scroll.viewport().installEventFilter(self)

        self._host = QWidget()
        self._host.setObjectName("quickPickShelfHost")
        self._row = QHBoxLayout(self._host)
        self._row.setContentsMargins(0, 6, 8, 6)
        self._row.setSpacing(10)
        self._row.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self._scroll.setWidget(self._host)
        self._host.installEventFilter(self)
        outer.addWidget(self._scroll)

    def wheelEvent(self, event) -> None:
        bar = self._scroll.horizontalScrollBar()
        if bar.maximum() > bar.minimum():
            delta = event.angleDelta().y() or event.angleDelta().x()
            bar.setValue(bar.value() - delta)
            event.accept()
            return
        super().wheelEvent(event)

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.Type.Wheel:
            bar = self._scroll.horizontalScrollBar()
            if bar.maximum() > bar.minimum():
                delta = event.angleDelta().y() or event.angleDelta().x()
                bar.setValue(bar.value() - delta)
                return True
        return super().eventFilter(watched, event)

    def set_playlists(self, playlists: list[Playlist]) -> None:
        while self._row.count():
            item = self._row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if not playlists:
            empty = QLabel("Появится после первых прослушиваний")
            empty.setObjectName("homeEmptyHint")
            self._row.addWidget(empty)
            return

        for playlist in playlists:
            tile = QuickPickTile(playlist)
            tile.activated.connect(self.playlist_activated.emit)
            self._row.addWidget(tile)
        self._row.addStretch(1)


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
            empty = QLabel(
                "Создай плейлист кнопкой «+ Плейлист» или добавь трек из плеера"
            )
            empty.setObjectName("homeEmptyHint")
            self._row.addWidget(empty)
            return

        for playlist in playlists:
            card = PlaylistCard(playlist)
            card.activated.connect(self.playlist_activated.emit)
            self._row.addWidget(card)
        self._row.addStretch(1)
