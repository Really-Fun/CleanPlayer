"""Строка плейлиста в таблице: обложка + название + число треков."""

from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QStyle, QStyledItemDelegate

from quantis.models.playlist import Playlist
from quantis.ui.models.playlist_list_model import PlaylistListModel
from quantis.ui.views.widgets.cover_art import load_cover_pixmap, playlist_cover_path
from quantis.ui.views.widgets.delegate_paint_kit import FONT_AUTHOR, FONT_TITLE
from quantis.ui.views.widgets.playlist_card import playlist_tracks_label


class PlaylistRowDelegate(QStyledItemDelegate):
    CARD_HEIGHT = 56
    COVER_SIZE = 40

    _C_BG_HOVER = QColor(255, 255, 255, 12)
    _C_BG_IDLE = QColor(255, 255, 255, 6)
    _C_BORDER = QColor(255, 255, 255, 22)
    _C_BORDER_HOVER = QColor(46, 230, 255, 50)
    _C_TITLE = QColor(248, 250, 252)
    _C_META = QColor(226, 232, 240, 120)

    def sizeHint(self, option, index) -> QSize:
        view = option.widget
        width = 320
        if view is not None and hasattr(view, "viewport"):
            width = max(view.viewport().width(), width)
        return QSize(width, self.CARD_HEIGHT)

    def paint(self, painter: QPainter, option, index) -> None:
        playlist: Playlist | None = index.data(PlaylistListModel.PlaylistRole)
        if playlist is None:
            return

        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        rect = option.rect.adjusted(0, 2, 0, -2)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        path = QPainterPath()
        path.addRoundedRect(rect, 12, 12)
        painter.fillPath(
            path, self._C_BG_HOVER if hovered or selected else self._C_BG_IDLE
        )
        pen = QPen(self._C_BORDER_HOVER if hovered or selected else self._C_BORDER)
        pen.setWidthF(1.0)
        painter.setPen(pen)
        painter.drawPath(path)

        cover = QRect(
            rect.x() + 8,
            rect.center().y() - self.COVER_SIZE // 2,
            self.COVER_SIZE,
            self.COVER_SIZE,
        )
        pixmap = load_cover_pixmap(playlist_cover_path(playlist), self.COVER_SIZE)
        painter.save()
        clip = QPainterPath()
        clip.addRoundedRect(cover, 8, 8)
        painter.setClipPath(clip)
        if pixmap is not None and not pixmap.isNull():
            painter.drawPixmap(cover, pixmap)
        else:
            painter.fillRect(cover, QColor(255, 255, 255, 18))
            painter.setPen(QColor(248, 250, 252, 200))
            painter.drawText(
                cover, Qt.AlignmentFlag.AlignCenter, (playlist.name[:1] or "?").upper()
            )
        painter.restore()

        text_left = cover.right() + 12
        title_rect = QRect(text_left, rect.y() + 8, rect.right() - text_left - 12, 22)
        meta_rect = QRect(text_left, title_rect.bottom() - 2, title_rect.width(), 18)

        painter.setPen(self._C_TITLE)
        painter.setFont(FONT_TITLE)
        painter.drawText(
            title_rect,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            QFontMetrics(FONT_TITLE).elidedText(
                playlist.name, Qt.TextElideMode.ElideRight, title_rect.width()
            ),
        )
        painter.setPen(self._C_META)
        painter.setFont(FONT_AUTHOR)
        painter.drawText(
            meta_rect,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            playlist_tracks_label(len(playlist)),
        )
