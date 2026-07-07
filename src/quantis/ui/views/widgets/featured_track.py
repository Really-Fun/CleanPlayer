from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter
from PySide6.QtWidgets import QFrame, QPushButton, QVBoxLayout

from quantis.models import Track


class FeaturedTrackPanel(QFrame):
    """Крупная карточка «сейчас слушай» — главная фишка домашней страницы."""

    play_requested = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("featuredPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setMinimumWidth(300)
        self._track: Track | None = None
        self._index = 0
        self._is_playing = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(0)
        layout.addStretch()

        self._play_btn = QPushButton("▶  Слушать")
        self._play_btn.setObjectName("featuredPlayBtn")
        self._play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._play_btn.clicked.connect(lambda: self.play_requested.emit(self._index))
        layout.addWidget(self._play_btn, 0, Qt.AlignmentFlag.AlignLeft)

    def set_track(self, track: Track | None, index: int = 0, *, playing: bool = False) -> None:
        self._track = track
        self._index = index
        self._is_playing = playing
        self._play_btn.setEnabled(track is not None)
        self._play_btn.setText("▶  Слушать" if not playing else "❚❚  Пауза")
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)

        painter.fillRect(rect, QColor(12, 12, 14))

        if self._is_playing:
            glow = QLinearGradient(rect.topLeft(), rect.bottomRight())
            glow.setColorAt(0.0, QColor(0, 229, 255, 28))
            glow.setColorAt(0.5, QColor(230, 59, 46, 22))
            glow.setColorAt(1.0, QColor(255, 42, 127, 12))
            painter.fillRect(rect, glow)

        painter.fillRect(rect.left(), rect.top() + 24, 3, 48, QColor(0, 229, 255, 200))
        painter.fillRect(rect.left() + 3, rect.top() + 24, 2, 48, QColor(230, 59, 46, 200))

        mono = QFont("Cascadia Mono", 9)
        mono.setWeight(QFont.Weight.Medium)
        painter.setFont(mono)
        painter.setPen(QColor(0, 229, 255) if self._is_playing else QColor(230, 59, 46))
        painter.drawText(rect.adjusted(20, 24, -20, 0), Qt.AlignmentFlag.AlignTop, "СЕЙЧАС")

        if self._track is None:
            display = QFont("Georgia", 28)
            display.setWeight(QFont.Weight.Normal)
            painter.setFont(display)
            painter.setPen(QColor(242, 240, 235, 90))
            painter.drawText(
                rect.adjusted(20, 56, -20, -80),
                Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
                "Выбери трек\nиз списка →",
            )
            painter.end()
            return

        idx_font = QFont("Georgia", 64)
        idx_font.setWeight(QFont.Weight.Light)
        painter.setFont(idx_font)
        painter.setPen(QColor(255, 255, 255, 12))
        painter.drawText(
            rect.adjusted(20, 48, -20, -100),
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight,
            f"{self._index + 1:02d}",
        )

        title_font = QFont("Georgia", 26)
        title_font.setWeight(QFont.Weight.Normal)
        painter.setFont(title_font)
        painter.setPen(QColor(242, 240, 235))
        title_rect = rect.adjusted(20, 52, -20, -90)
        painter.drawText(
            title_rect,
            Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
            self._track.title,
        )

        painter.setFont(mono)
        painter.setPen(QColor(242, 240, 235, 120))
        painter.drawText(
            rect.adjusted(20, 0, -20, 72),
            Qt.AlignmentFlag.AlignBottom,
            self._track.author.upper(),
        )

        painter.end()
