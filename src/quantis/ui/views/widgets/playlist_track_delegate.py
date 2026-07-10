"""Делегат строки плейлиста: # / обложка / название / источник."""

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPixmap
from PySide6.QtWidgets import QStyle, QStyledItemDelegate

from quantis.models.track import Track
from quantis.ui.models import TrackListModel
from quantis.ui.views.widgets.cover_art import load_cover_pixmap, paint_rounded_cover, track_cover_file
from quantis.ui.views.widgets.delegate_paint_kit import (
    C_ACCENT,
    C_BG_ALT,
    C_BG_HOVER,
    C_BG_PLAYING,
    C_INDEX,
    C_INDEX_PLAYING,
    C_PILL_TEXT,
    C_SUBTITLE,
    C_TITLE,
    C_TITLE_PLAYING,
    FONT_AUTHOR,
    FONT_INDEX,
    FONT_PILL,
    FONT_TITLE,
    SOURCE_COLORS,
    SOURCE_LABELS,
)


class PlaylistTrackDelegate(QStyledItemDelegate):
    ROW_HEIGHT = 56
    INDEX_WIDTH = 36
    COVER_SIZE = 40
    SOURCE_WIDTH = 52
    PILL_H = 20
    PILL_RADIUS = 10

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._fm_title = QFontMetrics(FONT_TITLE)
        self._fm_author = QFontMetrics(FONT_AUTHOR)
        self._fm_index = QFontMetrics(FONT_INDEX)
        self._cover_cache: dict[str, QPixmap | None] = {}

    def sizeHint(self, option, index) -> QSize:
        width = 320
        view = option.widget
        if view is not None and hasattr(view, "viewport"):
            width = max(view.viewport().width(), width)
        return QSize(width, self.ROW_HEIGHT)

    def _cover_pixmap(self, track: Track) -> QPixmap | None:
        key = f"{track.source}:{track.track_id}"
        if key not in self._cover_cache:
            self._cover_cache[key] = load_cover_pixmap(track_cover_file(track), self.COVER_SIZE)
        return self._cover_cache[key]

    def paint(self, painter: QPainter, option, index) -> None:
        track = index.data(TrackListModel.TrackRole)
        if track is None:
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        is_playing = bool(index.data(TrackListModel.IsPlayingRole))
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        row = index.row()
        rect = option.rect

        if is_playing:
            painter.fillRect(rect, C_BG_PLAYING)
        elif hovered or selected:
            painter.fillRect(rect, C_BG_HOVER)
        elif row % 2 == 1:
            painter.fillRect(rect, C_BG_ALT)

        if is_playing:
            painter.fillRect(
                QRect(rect.left(), rect.top() + 8, 3, rect.height() - 16),
                C_ACCENT,
            )

        inner = rect.adjusted(8, 0, -8, 0)
        idx_rect = QRect(inner.left(), inner.top(), self.INDEX_WIDTH, inner.height())
        source_rect = QRect(
            inner.right() - self.SOURCE_WIDTH + 1,
            inner.top(),
            self.SOURCE_WIDTH,
            inner.height(),
        )
        cover_rect = QRect(
            idx_rect.right() + 10,
            inner.top() + (inner.height() - self.COVER_SIZE) // 2,
            self.COVER_SIZE,
            self.COVER_SIZE,
        )
        text_left = cover_rect.right() + 12
        text_right = source_rect.left() - 12
        text_w = max(0, text_right - text_left)

        painter.setFont(FONT_INDEX)
        painter.setPen(C_INDEX_PLAYING if is_playing else C_INDEX)
        painter.drawText(idx_rect, Qt.AlignmentFlag.AlignCenter, f"{row + 1}")

        paint_rounded_cover(
            painter,
            cover_rect,
            label=track.title or track.author or "?",
            pixmap=self._cover_pixmap(track),
            source_key=str(track.source),
        )

        title_rect = QRect(text_left, inner.top() + 11, text_w, 20)
        author_rect = QRect(text_left, inner.top() + 30, text_w, 16)

        painter.setFont(FONT_TITLE)
        painter.setPen(C_TITLE_PLAYING if is_playing else C_TITLE)
        painter.drawText(
            title_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self._fm_title.elidedText(
                track.title or "—",
                Qt.TextElideMode.ElideRight,
                text_w,
            ),
        )

        painter.setFont(FONT_AUTHOR)
        painter.setPen(C_SUBTITLE)
        painter.drawText(
            author_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self._fm_author.elidedText(
                track.author or "—",
                Qt.TextElideMode.ElideRight,
                text_w,
            ),
        )

        source_key = str(track.source).lower()
        label = SOURCE_LABELS.get(source_key, source_key[:2].upper())
        pill_color = SOURCE_COLORS.get(source_key, QColor(255, 255, 255, 40))
        pill_w = max(self.PILL_H, self._fm_index.horizontalAdvance(label) + 14)
        pill_rect = QRect(
            source_rect.center().x() - pill_w // 2,
            source_rect.center().y() - self.PILL_H // 2,
            pill_w,
            self.PILL_H,
        )
        painter.setBrush(pill_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(pill_rect, self.PILL_RADIUS, self.PILL_RADIUS)
        painter.setFont(FONT_PILL)
        painter.setPen(C_PILL_TEXT)
        painter.drawText(pill_rect, Qt.AlignmentFlag.AlignCenter, label)
        painter.restore()
