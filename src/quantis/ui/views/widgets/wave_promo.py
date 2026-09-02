"""Промо-карточка «Моя волна» на главной."""

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

from quantis.ui.views.widgets.home_pill_badge import HomePillBadge


class WavePromoCard(QFrame):
    """Компактная строка «Моя волна»."""

    open_requested = Signal()
    play_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("wavePromoCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(68)
        self.setMaximumHeight(76)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._available = False
        self._track_count = 0
        self._source_label = "Yandex Music"

        root = QHBoxLayout(self)
        root.setContentsMargins(14, 10, 12, 10)
        root.setSpacing(12)

        text = QVBoxLayout()
        text.setSpacing(4)
        text.setContentsMargins(0, 0, 0, 0)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        self._badge = HomePillBadge("Моя волна", variant="wave")
        title_row.addWidget(self._badge, 0, Qt.AlignmentFlag.AlignVCenter)
        self._count_label = QLabel("")
        self._count_label.setObjectName("wavePromoCount")
        title_row.addWidget(self._count_label, 0, Qt.AlignmentFlag.AlignVCenter)
        title_row.addStretch(1)
        text.addLayout(title_row)

        self._subtitle = QLabel("Персональное радио · нужен токен Yandex")
        self._subtitle.setObjectName("wavePromoSubtitle")
        self._subtitle.setWordWrap(True)
        text.addWidget(self._subtitle)
        root.addLayout(text, stretch=1)

        self._play_btn = QToolButton()
        self._play_btn.setObjectName("wavePromoPlayBtn")
        self._play_btn.setText("▶")
        self._play_btn.setToolTip("Слушать волну")
        self._play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._play_btn.setEnabled(False)
        self._play_btn.clicked.connect(self.play_requested.emit)
        root.addWidget(self._play_btn, 0, Qt.AlignmentFlag.AlignVCenter)

    def set_state(
        self,
        *,
        available: bool,
        track_count: int = 0,
        source: str = "yandex",
        loading: bool = False,
        error: str | None = None,
    ) -> None:
        self._available = available
        self._track_count = track_count
        self._source_label = "Yandex Music" if source == "yandex" else source
        self._play_btn.setEnabled(available and track_count > 0 and not loading)

        if loading:
            self._subtitle.setText(f"Загружаем · {self._source_label}…")
            self._count_label.setText("")
        elif error:
            self._subtitle.setText(error)
            self._count_label.setText("")
        elif available and track_count:
            self._subtitle.setText(
                f"{self._source_label} · нажми на карточку, чтобы открыть плейлист"
            )
            self._count_label.setText(f"{track_count} в потоке")
        elif available:
            self._subtitle.setText(f"{self._source_label} · пока пусто")
            self._count_label.setText("")
        else:
            self._subtitle.setText("Добавь OAuth-токен Yandex во вкладке Member")
            self._count_label.setText("")
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._available:
            self.open_requested.emit()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(rect, 14, 14)

        painter.fillPath(path, QColor(255, 255, 255, 10 if self._available else 6))

        pen = QPen(QColor(46, 230, 255, 55 if self._available else 22))
        pen.setWidthF(1.0)
        painter.setPen(pen)
        painter.drawPath(path)
        painter.end()
