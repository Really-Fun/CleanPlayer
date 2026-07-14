"""Промо-карточка «Моя волна» на главной."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from quantis.ui import resources


class WavePromoCard(QFrame):
    """Яркий блок «Моя волна» — открыть / сразу слушать."""

    open_requested = Signal()
    play_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("wavePromoCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(112)
        self.setMaximumHeight(128)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._available = False
        self._track_count = 0
        self._source_label = "Yandex Music"

        root = QHBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(16)

        icon = QLabel()
        icon.setObjectName("wavePromoIcon")
        icon.setFixedSize(56, 56)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pix = QPixmap(resources.icon_path("radio.svg"))
        if not pix.isNull():
            icon.setPixmap(
                pix.scaled(
                    36,
                    36,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            icon.setText("♫")
        root.addWidget(icon, 0, Qt.AlignmentFlag.AlignVCenter)

        text = QVBoxLayout()
        text.setSpacing(4)
        self._title = QLabel("Моя волна")
        self._title.setObjectName("wavePromoTitle")
        text.addWidget(self._title)
        self._subtitle = QLabel("Персональное радио Yandex · нужен токен в Member")
        self._subtitle.setObjectName("wavePromoSubtitle")
        self._subtitle.setWordWrap(True)
        text.addWidget(self._subtitle)
        root.addLayout(text, stretch=1)

        self._play_btn = QPushButton("▶  Волна")
        self._play_btn.setObjectName("wavePromoPlayBtn")
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
            self._subtitle.setText(f"Загружаем волну · {self._source_label}…")
        elif error:
            self._subtitle.setText(error)
        elif available and track_count:
            self._subtitle.setText(
                f"{self._source_label} · {track_count} треков в потоке · нажми или ▶"
            )
        elif available:
            self._subtitle.setText(f"{self._source_label} · пока пусто, попробуй обновить")
        else:
            self._subtitle.setText("Добавь OAuth-токен Yandex во вкладке Member")
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
        path.addRoundedRect(rect, 22, 22)

        fill = QLinearGradient(rect.topLeft(), rect.bottomRight())
        fill.setColorAt(0.0, QColor(14, 48, 58, 230))
        fill.setColorAt(0.55, QColor(28, 16, 42, 225))
        fill.setColorAt(1.0, QColor(10, 12, 24, 240))
        painter.fillPath(path, fill)

        bloom = QLinearGradient(rect.topLeft(), rect.bottomRight())
        bloom.setColorAt(0.0, QColor(46, 230, 255, 50 if self._available else 16))
        bloom.setColorAt(0.6, QColor(255, 92, 122, 28 if self._available else 8))
        bloom.setColorAt(1.0, QColor(46, 230, 255, 0))
        painter.fillPath(path, bloom)

        pen = QPen(QColor(46, 230, 255, 90 if self._available else 35))
        pen.setWidthF(1.2)
        painter.setPen(pen)
        painter.drawPath(path)
        painter.end()
