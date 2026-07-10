"""Кэшированные ресурсы для делегатов списков треков."""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont

# Цвета
C_BG_HOVER = QColor(255, 255, 255, 14)
C_BG_PLAYING = QColor(0, 229, 255, 18)
C_BG_ALT = QColor(255, 255, 255, 4)
C_ACCENT = QColor(0, 229, 255)
C_TITLE = QColor(248, 250, 252)
C_TITLE_PLAYING = QColor(0, 229, 255)
C_SUBTITLE = QColor(248, 250, 252, 110)
C_INDEX = QColor(255, 255, 255, 90)
C_INDEX_PLAYING = QColor(0, 229, 255)
C_YT = QColor(220, 50, 50, 180)
C_YA = QColor(0, 180, 220, 180)
C_PILL_TEXT = QColor(255, 255, 255, 220)

# Шрифты (создаются один раз)
FONT_TITLE = QFont("Segoe UI", 10, QFont.Weight.DemiBold)
FONT_AUTHOR = QFont("Segoe UI", 9)
FONT_INDEX = QFont("Segoe UI", 11, QFont.Weight.Medium)
FONT_PILL = QFont("Segoe UI", 8, QFont.Weight.Bold)
FONT_COVER = QFont("Segoe UI", 11, QFont.Weight.Bold)
FONT_ACTION = QFont("Segoe UI", 10, QFont.Weight.Bold)
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
