from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from quantis.models import Track
from quantis.ui.views.widgets.cover_art import load_track_cover, track_cover_file
from quantis.ui.views.widgets.playlist_card import GradientCover


class FeaturedTrackPanel(QFrame):
    """Hero «Продолжить» — обложка + мета + CTA (стриминговый стиль)."""

    play_requested = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("featuredPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setMinimumHeight(196)
        self.setMaximumHeight(220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._track: Track | None = None
        self._index = 0
        self._is_playing = False

        root = QHBoxLayout(self)
        root.setContentsMargins(22, 22, 22, 22)
        root.setSpacing(22)

        self._cover = GradientCover("Quantis", size=152, radius=18)
        root.addWidget(self._cover, 0, Qt.AlignmentFlag.AlignVCenter)

        col = QVBoxLayout()
        col.setSpacing(6)
        col.setContentsMargins(0, 8, 0, 8)

        self._eyebrow = QLabel("ПРОДОЛЖИТЬ СЛУШАТЬ")
        self._eyebrow.setObjectName("featuredEyebrow")
        col.addWidget(self._eyebrow)

        self._title = QLabel("Выбери трек")
        self._title.setObjectName("featuredTitle")
        self._title.setWordWrap(True)
        col.addWidget(self._title)

        self._author = QLabel("Открой поиск или плейлист — и волна начнётся")
        self._author.setObjectName("featuredAuthor")
        self._author.setWordWrap(True)
        col.addWidget(self._author)

        col.addStretch(1)

        self._play_btn = QPushButton("▶  Слушать")
        self._play_btn.setObjectName("featuredPlayBtn")
        self._play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._play_btn.clicked.connect(lambda: self.play_requested.emit(self._index))
        col.addWidget(self._play_btn, 0, Qt.AlignmentFlag.AlignLeft)

        root.addLayout(col, stretch=1)

    def set_track(self, track: Track | None, index: int = 0, *, playing: bool = False) -> None:
        self._track = track
        self._index = index
        self._is_playing = playing
        self._play_btn.setEnabled(track is not None)
        self._play_btn.setText("❚❚  Пауза" if playing else "▶  Слушать")

        if track is None:
            self._title.setText("Готов к сессии")
            self._author.setText("Открой поиск или плейлист — и волна начнётся")
            self._cover.set_content("Quantis", None)
        else:
            self._title.setText(track.title)
            self._author.setText(track.author)
            path = str(track_cover_file(track))
            # Прогрев кэша
            load_track_cover(track, 152)
            self._cover.set_content(track.title, path)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(rect, 28, 28)

        fill = QLinearGradient(rect.topLeft(), rect.bottomRight())
        if self._is_playing:
            fill.setColorAt(0.0, QColor(18, 42, 58, 235))
            fill.setColorAt(0.55, QColor(36, 18, 40, 230))
            fill.setColorAt(1.0, QColor(10, 12, 24, 240))
        else:
            fill.setColorAt(0.0, QColor(12, 18, 32, 235))
            fill.setColorAt(1.0, QColor(8, 10, 20, 245))
        painter.fillPath(path, fill)

        bloom = QLinearGradient(rect.topLeft(), rect.bottomRight())
        bloom.setColorAt(0.0, QColor(46, 230, 255, 40 if self._is_playing else 18))
        bloom.setColorAt(0.5, QColor(255, 92, 122, 22 if self._is_playing else 10))
        bloom.setColorAt(1.0, QColor(46, 230, 255, 0))
        painter.fillPath(path, bloom)

        pen = QPen(QColor(46, 230, 255, 80 if self._is_playing else 42))
        pen.setWidthF(1.2)
        painter.setPen(pen)
        painter.drawPath(path)
        painter.end()
