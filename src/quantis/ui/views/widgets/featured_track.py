from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
)

from quantis.models import Track
from quantis.ui.views.widgets.cover_art import load_track_cover, track_cover_file
from quantis.ui.views.widgets.home_pill_badge import HomePillBadge
from quantis.ui.views.widgets.playlist_card import GradientCover


class FeaturedTrackPanel(QFrame):
    """Компактный блок «Продолжить слушать»."""

    play_requested = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("featuredPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setMinimumHeight(108)
        self.setMaximumHeight(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._track: Track | None = None
        self._index = 0
        self._is_playing = False

        root = QHBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(14)

        self._cover = GradientCover("Quantis", size=88, radius=12)
        root.addWidget(self._cover, 0, Qt.AlignmentFlag.AlignVCenter)

        col = QVBoxLayout()
        col.setSpacing(3)
        col.setContentsMargins(0, 2, 0, 2)

        self._eyebrow = HomePillBadge("Продолжить слушать", variant="continue")
        col.addWidget(self._eyebrow, 0, Qt.AlignmentFlag.AlignLeft)

        self._title = QLabel("Выбери трек")
        self._title.setObjectName("featuredTitle")
        self._title.setWordWrap(True)
        col.addWidget(self._title)

        self._author = QLabel("Открой поиск или плейлист")
        self._author.setObjectName("featuredAuthor")
        self._author.setWordWrap(True)
        col.addWidget(self._author)

        col.addStretch(1)
        root.addLayout(col, stretch=1)

        self._play_btn = QToolButton()
        self._play_btn.setObjectName("featuredPlayBtn")
        self._play_btn.setText("▶")
        self._play_btn.setToolTip("Слушать")
        self._play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._play_btn.clicked.connect(lambda: self.play_requested.emit(self._index))
        root.addWidget(self._play_btn, 0, Qt.AlignmentFlag.AlignVCenter)

    def set_track(self, track: Track | None, index: int = 0, *, playing: bool = False) -> None:
        self._track = track
        self._index = index
        self._is_playing = playing
        self._play_btn.setEnabled(track is not None)
        self._play_btn.setText("❚❚" if playing else "▶")
        self._play_btn.setToolTip("Пауза" if playing else "Слушать")

        if track is None:
            self._title.setText("Готов к сессии")
            self._author.setText("Открой поиск или плейлист")
            self._cover.set_content("Quantis", None)
        else:
            self._title.setText(track.title)
            self._author.setText(track.author)
            path = str(track_cover_file(track))
            load_track_cover(track, 88)
            self._cover.set_content(track.title, path)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(rect, 14, 14)

        alpha = 14 if self._is_playing else 10
        painter.fillPath(path, QColor(255, 255, 255, alpha))

        border_alpha = 70 if self._is_playing else 40
        pen = QPen(QColor(255, 92, 122, border_alpha))
        pen.setWidthF(1.0)
        painter.setPen(pen)
        painter.drawPath(path)
        painter.end()
