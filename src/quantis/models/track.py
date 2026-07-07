"""Модель трека

Классы:
1. TrackSource — перечисление платформ
2. Track — базовый дата класс трека
3. YandexTrack — трек ЯндексМузыки
4. YoutubeTrack — трек YouTube
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class TrackSource(StrEnum):
    """Перечисление поддерживаемых платформ.

    Используется вместо строк ``"yandex"`` / ``"youtube"`` по всему коду.
    Совместимо со строками: ``TrackSource.YANDEX == "yandex"`` → ``True``.
    """

    YANDEX  = "yandex"
    YOUTUBE = "youtube"


@dataclass(eq=False)
class Track:
    """Базовый дата класс трека."""

    track_id: int | str
    title: str
    author: str
    downloaded: bool = False
    source: str = ""
    listen_count: int = 0

    def __repr__(self) -> str:
        return f"{self.source}:{self.track_id}"

    def __str__(self) -> str:
        return f"{self.source} : {self.title} - {self.author}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Track):
            return False
        return (
            str(self.source) == str(other.source)
            and str(self.track_id) == str(other.track_id)
        )

    def __hash__(self) -> int:
        return hash((str(self.source), str(self.track_id)))


@dataclass(eq=False)
class YandexTrack(Track):
    """Трек Яндекс.Музыки."""

    source: str = TrackSource.YANDEX


@dataclass(eq=False)
class YoutubeTrack(Track):
    """Трек YouTube."""

    source: str = TrackSource.YOUTUBE
    extension: str = "m4a"