"""Модель трека

Треки могут быть двух типов:
1. Треки Яндекса
2. Треки YouTube

Классы:
1. TrackSource — перечисление платформ
2. Track      — базовый датакласс трека
3. YandexTrack — трек Яндекс.Музыки
4. YoutubeTrack — трек YouTube
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class TrackSource(StrEnum):
    """Перечисление поддерживаемых платформ.

    Используется вместо хардкода строк ``"yandex"`` / ``"youtube"`` по всему коду.
    Совместимо со строками: ``TrackSource.YANDEX == "yandex"`` → ``True``.
    """

    YANDEX  = "yandex"
    YOUTUBE = "youtube"


@dataclass
class Track:
    """Базовый датакласс трека."""

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
        if isinstance(other, self.__class__):
            return self.track_id == other.track_id
        if hasattr(other, "title") and hasattr(other, "author"):
            return (self.title, self.author) == (other.title, other.author)
        return False

    def __hash__(self) -> int:
        return hash(self.track_id)


@dataclass
class YandexTrack(Track):
    """Трек Яндекс.Музыки."""

    source: str = TrackSource.YANDEX


@dataclass
class YoutubeTrack(Track):
    """Трек YouTube."""

    source: str = TrackSource.YOUTUBE
    extension: str = "m4a"
