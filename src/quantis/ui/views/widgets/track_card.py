from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QEvent, QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QStyledItemDelegate, QStyle, QStyleOptionViewItem

from quantis.models import Track, TrackSource
from quantis.ui.preferences import UiPreferences
from quantis.ui.resources import THEME_EDITORIAL
from quantis.ui.models import TrackListModel


class TrackCardDelegate(QStyledItemDelegate):
    CARD_HEIGHT = 56
    CARD_RADIUS = 10
    COVER_SIZE = 40
    ACTION_SIZE = 26

    def __init__(
        self,
        parent=None,
        on_download: Callable[[int], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_download = on_download
        self._prefs = UiPreferences()
        self._prefs.changed.connect(self._on_theme_changed)

    def _on_theme_changed(self) -> None:
        parent = self.parent()
        if parent is not None and hasattr(parent, "viewport"):
            parent.viewport().update()
        elif parent is not None:
            parent.update()

    def sizeHint(self, option, index) -> QSize:
        view = option.widget
        width = 320
        if view is not None:
            if hasattr(view, "viewport"):
                width = max(view.viewport().width(), width)
            else:
                width = max(view.width(), width)
        return QSize(width, self.CARD_HEIGHT)

    def _action_rect(self, rect) -> QRect:
        inner = rect.adjusted(4, 2, -8, -2)
        return QRect(
            inner.right() - self.ACTION_SIZE,
            inner.center().y() - self.ACTION_SIZE // 2,
            self.ACTION_SIZE,
            self.ACTION_SIZE,
        )

    def editorEvent(self, event, model, option, index):
        if (
            self._on_download is not None
            and event.type() == QEvent.Type.MouseButtonRelease
            and event.button() == Qt.MouseButton.LeftButton
        ):
            track: Track | None = index.data(TrackListModel.TrackRole)
            if track is not None and not track.downloaded:
                if self._action_rect(option.rect).contains(event.pos()):
                    self._on_download(index.row())
                    return True
        return super().editorEvent(event, model, option, index)

    def paint(self, painter: QPainter, option, index) -> None:
        track: Track | None = index.data(TrackListModel.TrackRole)
        if track is None:
            super().paint(painter, option, index)
            return

        is_playing = bool(index.data(TrackListModel.IsPlayingRole))
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        rect = option.rect.adjusted(4, 2, -4, -2)
        editorial = self._prefs.ui_theme == THEME_EDITORIAL

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if editorial:
            self._paint_editorial(
                painter, rect, track, index.row(), is_playing, hovered, selected
            )
        else:
            self._paint_default(painter, rect, track, is_playing, hovered, selected)

        if self._on_download is None:
            return

        action_rect = self._action_rect(option.rect)
        if track.downloaded:
            painter.setBrush(QColor(34, 197, 94, 60))
            painter.setPen(QPen(QColor(34, 197, 94, 140), 1))
            painter.drawEllipse(action_rect)
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            painter.drawText(action_rect, Qt.AlignmentFlag.AlignCenter, "✓")
        elif hovered:
            painter.setBrush(QColor(255, 255, 255, 16))
            painter.setPen(QPen(QColor(255, 255, 255, 50), 1))
            painter.drawEllipse(action_rect)
            painter.setPen(QColor(248, 250, 252, 200))
            painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            painter.drawText(action_rect, Qt.AlignmentFlag.AlignCenter, "↓")

    def _paint_default(
        self,
        painter: QPainter,
        rect: QRect,
        track: Track,
        is_playing: bool,
        hovered: bool,
        selected: bool,
    ) -> None:
        if is_playing:
            painter.setBrush(QColor(0, 229, 255, 22))
            painter.setPen(QPen(QColor(0, 229, 255, 90), 1))
        elif hovered or selected:
            painter.setBrush(QColor(255, 255, 255, 12))
            painter.setPen(QPen(QColor(255, 255, 255, 28), 1))
        else:
            painter.setBrush(QColor(255, 255, 255, 5))
            painter.setPen(Qt.PenStyle.NoPen)

        painter.drawRoundedRect(rect, self.CARD_RADIUS, self.CARD_RADIUS)

        if is_playing:
            bar = QRect(rect.left() + 2, rect.top() + 10, 3, rect.height() - 20)
            painter.setBrush(QColor(0, 229, 255))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(bar, 2, 2)

        cover_rect = QRect(
            rect.left() + 12,
            rect.top() + (rect.height() - self.COVER_SIZE) // 2,
            self.COVER_SIZE,
            self.COVER_SIZE,
        )
        grad = QLinearGradient(cover_rect.topLeft(), cover_rect.bottomRight())
        source = str(track.source).lower()
        if source == TrackSource.YOUTUBE:
            grad.setColorAt(0.0, QColor(220, 50, 50))
            grad.setColorAt(1.0, QColor(140, 30, 30))
        else:
            grad.setColorAt(0.0, QColor(0, 180, 220))
            grad.setColorAt(1.0, QColor(80, 60, 200))
        painter.setBrush(grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(cover_rect, 8, 8)

        initial = (track.title or "?")[0].upper()
        painter.setPen(QColor(255, 255, 255, 230))
        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        painter.drawText(cover_rect, Qt.AlignmentFlag.AlignCenter, initial)

        action_w = self.ACTION_SIZE + 16 if self._on_download else 8
        text_left = cover_rect.right() + 12
        text_right = rect.right() - action_w
        title_rect = QRect(text_left, rect.top() + 10, text_right - text_left, 20)
        author_rect = QRect(text_left, rect.top() + 28, text_right - text_left, 16)

        title_color = QColor(0, 229, 255) if is_playing else QColor(248, 250, 252)
        painter.setPen(title_color)
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        elided_title = QFontMetrics(painter.font()).elidedText(
            track.title, Qt.TextElideMode.ElideRight, title_rect.width()
        )
        painter.drawText(
            title_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            elided_title,
        )

        painter.setPen(QColor(248, 250, 252, 120))
        painter.setFont(QFont("Segoe UI", 9))
        elided_author = QFontMetrics(painter.font()).elidedText(
            track.author, Qt.TextElideMode.ElideRight, author_rect.width()
        )
        painter.drawText(
            author_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            elided_author,
        )

    def _paint_editorial(
        self,
        painter: QPainter,
        rect: QRect,
        track: Track,
        row: int,
        is_playing: bool,
        hovered: bool,
        selected: bool,
    ) -> None:
        inner = rect.adjusted(1, 1, -1, -1)
        painter.fillRect(inner, QColor(12, 12, 14))

        if is_playing:
            glow = QLinearGradient(inner.topLeft(), inner.bottomRight())
            glow.setColorAt(0.0, QColor(0, 229, 255, 20))
            glow.setColorAt(0.5, QColor(230, 59, 46, 16))
            glow.setColorAt(1.0, QColor(255, 42, 127, 8))
            painter.fillRect(inner, glow)
            painter.setPen(QPen(QColor(0, 229, 255, 70)))
        elif hovered or selected:
            painter.setPen(QPen(QColor(255, 255, 255, 30)))
        else:
            painter.setPen(QPen(QColor(255, 255, 255, 12)))
        painter.drawRect(inner)

        if is_playing:
            painter.fillRect(inner.left(), inner.top() + 8, 3, inner.height() - 16, QColor(0, 229, 255, 220))
            painter.fillRect(inner.left() + 3, inner.top() + 8, 2, inner.height() - 16, QColor(230, 59, 46, 200))

        idx_font = QFont("Georgia", 28)
        idx_font.setWeight(QFont.Weight.Light)
        painter.setFont(idx_font)
        painter.setPen(QColor(255, 255, 255, 10))
        painter.drawText(
            inner.adjusted(0, 0, -12, 0),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            f"{row + 1:02d}",
        )

        action_w = self.ACTION_SIZE + 16 if self._on_download else 8
        text_left = inner.left() + 16
        text_right = inner.right() - action_w
        title_rect = QRect(text_left, inner.top() + 10, text_right - text_left, 22)
        author_rect = QRect(text_left, inner.top() + 30, text_right - text_left, 16)

        title_color = QColor(0, 229, 255) if is_playing else QColor(242, 240, 235)
        painter.setPen(title_color)
        painter.setFont(QFont("Georgia", 12))
        elided_title = QFontMetrics(painter.font()).elidedText(
            track.title, Qt.TextElideMode.ElideRight, title_rect.width()
        )
        painter.drawText(
            title_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            elided_title,
        )

        mono = QFont("Cascadia Mono", 8)
        mono.setWeight(QFont.Weight.Medium)
        painter.setFont(mono)
        painter.setPen(QColor(242, 240, 235, 100))
        elided_author = QFontMetrics(painter.font()).elidedText(
            track.author.upper(), Qt.TextElideMode.ElideRight, author_rect.width()
        )
        painter.drawText(
            author_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            elided_author,
        )
