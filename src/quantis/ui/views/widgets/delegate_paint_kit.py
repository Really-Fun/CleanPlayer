"""Кэшированные ресурсы для делегатов списков треков."""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont

# Цвета — Aurora
C_BG_HOVER = QColor(255, 255, 255, 16)
C_BG_PLAYING = QColor(108, 92, 231, 28)
C_BG_ALT = QColor(255, 255, 255, 4)
C_ACCENT = QColor(108, 92, 231)
C_TITLE = QColor(242, 244, 248)
C_TITLE_PLAYING = QColor(108, 92, 231)
C_SUBTITLE = QColor(138, 146, 166)
C_INDEX = QColor(138, 146, 166)
C_INDEX_PLAYING = QColor(108, 92, 231)
C_YT = QColor(255, 78, 69)
C_YA = QColor(255, 219, 77)
C_PILL_TEXT = QColor(20, 22, 28)

_UI = "Bahnschrift"
FONT_TITLE = QFont(_UI, 10, QFont.Weight.DemiBold)
FONT_AUTHOR = QFont(_UI, 9)
FONT_INDEX = QFont(_UI, 11, QFont.Weight.Medium)
FONT_PILL = QFont(_UI, 8, QFont.Weight.Bold)
FONT_COVER = QFont(_UI, 11, QFont.Weight.Bold)
FONT_ACTION = QFont(_UI, 10, QFont.Weight.Bold)
FONT_EDITORIAL_TITLE = QFont("Georgia", 12)
FONT_EDITORIAL_AUTHOR = QFont("Cascadia Mono", 8, QFont.Weight.Medium)
FONT_EDITORIAL_INDEX = QFont("Georgia", 28, QFont.Weight.Light)

SOURCE_LABELS = {
    "youtube": "YT",
    "yandex": "YA",
}

SOURCE_COLORS = {
    "youtube": C_YT,
    "yandex": C_YA,
}
