"""Карточка плейлиста для главной страницы (минималистичная)."""

import os

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPixmap,
)
from PySide6.QtWidgets import (
    QLabel,
    QMenu,
    QVBoxLayout,
    QWidget,
)

from quantis.providers import PathProvider
from quantis.utils import get_ru_words_for_number

_CARD_W = 150        # Чуть сузили, так как теперь нет громоздкого фона
_CARD_H = 200
_COVER_SIZE = 142    # Картинка остается четкой
_COVER_RADIUS = 12   # Красивое скругление углов


class PlaylistPreview(QWidget):
    """Минималистичное превью плейлиста: только обложка и текст."""

    clicked = Signal(object)
    rename_requested = Signal(object)
    delete_requested = Signal(object)

    def __init__(self, playlist, parent=None):
        super().__init__(parent)

        self._path = PathProvider()
        self._playlist = playlist

        self.setFixedSize(_CARD_W, _CARD_H)
        self.setCursor(Qt.PointingHandCursor)

        # ── Макет (без отступов по бокам, чтобы текст был всклянь с обложкой) ──
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(6)

        # ── Обложка ──
        self._cover_label = QLabel()
        self._cover_label.setObjectName("playlistCoverLabelOnly")
        self._cover_label.setFixedSize(_COVER_SIZE, _COVER_SIZE)
        self._cover_label.setStyleSheet("background: transparent; border: none; padding: 0px;")

        self._cover_pixmap: QPixmap | None = None
        self._load_cover()
        self._apply_cover_to_label()
        lay.addWidget(self._cover_label, alignment=Qt.AlignCenter)

        # ── Название ──
        self._title = QLabel(playlist.name if playlist else "—")
        self._title.setObjectName("playlistTitle")

        metrics = self._title.fontMetrics()
        elided_title = metrics.elidedText(self._title.text(), Qt.ElideRight, _CARD_W - 8)
        self._title.setText(elided_title)
        lay.addWidget(self._title)

        # ── Подпись ──
        count = len(playlist.tracks.values) if playlist else 0
        self._count = QLabel(self._build_subtitle(count))
        self._count.setObjectName("playlistCount")

        metrics_count = self._count.fontMetrics()
        elided_count = metrics_count.elidedText(self._count.text(), Qt.ElideRight, _CARD_W - 8)
        self._count.setText(elided_count)
        lay.addWidget(self._count)

        lay.addStretch()

    def _apply_cover_to_label(self) -> None:
        """Рендерит закругленную обложку на 100% прозрачном холсте."""
        canvas = QPixmap(_COVER_SIZE, _COVER_SIZE)
        canvas.fill(QColor(0, 0, 0, 0))

        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        path = QPainterPath()
        path.addRoundedRect(0, 0, _COVER_SIZE, _COVER_SIZE, _COVER_RADIUS, _COVER_RADIUS)
        painter.setClipPath(path)

        if self._cover_pixmap and not self._cover_pixmap.isNull():
            painter.drawPixmap(0, 0, self._cover_pixmap)
        else:
            # Спокойный темный фон, если нет картинки
            grad = QLinearGradient(0, 0, _COVER_SIZE, _COVER_SIZE)
            grad.setColorAt(0.0, QColor(25, 28, 38))
            grad.setColorAt(1.0, QColor(15, 16, 22))
            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.NoPen)
            painter.drawRect(0, 0, _COVER_SIZE, _COVER_SIZE)

            painter.setPen(QColor(0, 220, 255, 100))
            painter.setFont(QFont("Segoe UI", 32, QFont.Bold))
            painter.drawText(QRectF(0, 0, _COVER_SIZE, _COVER_SIZE), Qt.AlignCenter, "♫")

        painter.end()
        self._cover_label.setPixmap(canvas)

    def _load_cover(self) -> None:
        cover_path = self._resolve_cover()
        if cover_path and os.path.isfile(cover_path):
            pm = QPixmap(cover_path)
            if not pm.isNull():
                self._cover_pixmap = pm.scaled(
                    _COVER_SIZE,
                    _COVER_SIZE,
                    Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation,
                )

    def _resolve_cover(self) -> str | None:
        pl = self._playlist
        if not pl:
            return None
        if pl.cover_path and os.path.isfile(pl.cover_path):
            return pl.cover_path
        tracks = pl.tracks.values
        if tracks:
            path = self._path.get_cover_path(tracks[0])
            if os.path.isfile(path):
                pl.cover_path = path
                return path
        return None

    def set_cover_pixmap(self, pm: QPixmap) -> None:
        self._cover_pixmap = pm.scaled(
            _COVER_SIZE,
            _COVER_SIZE,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        )
        self._apply_cover_to_label()

    # ── Клик и контекстное меню ──

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self._playlist:
            self.clicked.emit(self._playlist)
        elif event.button() == Qt.RightButton and self._playlist:
            self._show_context_menu(event.globalPos())
        super().mousePressEvent(event)

    def _show_context_menu(self, global_pos) -> None:
        menu = QMenu(self)
        rename_action = menu.addAction("Переименовать")
        delete_action = menu.addAction("Удалить")
        chosen = menu.exec(global_pos)
        if chosen == rename_action:
            self.rename_requested.emit(self._playlist)
        elif chosen == delete_action:
            self.delete_requested.emit(self._playlist)

    def _build_subtitle(self, track_count: int) -> str:
        base = get_ru_words_for_number(track_count)
        if not self._playlist:
            return base
        total_listens = sum(
            max(0, int(getattr(t, "listen_count", 0)))
            for t in self._playlist.tracks.values
        )
        if total_listens <= 0:
            return base
        return f"{base} · {self._format_listens(total_listens)}"

    @staticmethod
    def _format_listens(listens: int) -> str:
        tail_100 = listens % 100
        tail_10 = listens % 10
        if 11 <= tail_100 <= 14:
            word = "прослушиваний"
        elif tail_10 == 1:
            word = "прослушивание"
        elif 2 <= tail_10 <= 4:
            word = "прослушивания"
        else:
            word = "прослушиваний"
        return f"{listens} {word}"