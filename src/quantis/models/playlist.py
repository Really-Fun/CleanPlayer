"""Модель плейлиста

Плейлисты пользователя - это плейлисты, которые создают пользователи.
Плейлисты системы - это плейлисты, которые создаются системой.

Плейлисты пользователя хранятся в файле playlists/user_playlists.json

Классы:
1. Playlist - абстрактный класс плейлиста
2. UserPlaylist - класс плейлиста пользователя
3. DownloadPlaylist - класс плейлиста системы
4. RecentlyPlayedPlaylist - системный плейлист недавно прослушанных
"""
from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable, Tuple

from quantis.models.track import Track, YandexTrack, YoutubeTrack
from quantis.providers import PathProvider, TrackManager
from quantis.types.upgrade_cycle import UpgradeCycle
from quantis.utils import get_asset_path


class Playlist(ABC):
    def __init__(
        self, name: str, tracks: Iterable[Track], cover_path: str | None = None
    ) -> None:
        self.tracks = UpgradeCycle(tracks)
        self.name = name
        self.cover_path = cover_path

    def move_next_track(self) -> Track:
        """Переключаемся на следующий трек

        Returns:
            Track: следующий трек
        """
        return next(self.tracks)

    def move_previous_track(self) -> Track:
        """Переключаемся на предыдущий трек

        Returns:
            Track: предыдущий трек
        """
        return self.tracks.move_previous()

    def get_current_track(self) -> Track:
        """Получаем текущий трек

        Returns:
            Track: текущий трек
        """
        return self.tracks.peek_current()

    def get_track(self, index: int) -> Track:
        """Получаем трек по индексу

        Returns:
            Track: трек
        """
        return self.tracks.values[index]

    def delete_track(self, track: Track) -> bool:
        """Удаляем трек из плейлиста.

        Args:
            track (Track): трек для удаления

        Returns:
            bool: ``True`` если трек найден и удален, иначе ``False``.
        """
        return self.tracks.remove(track)

    def set_current_track(self, index: int) -> None:
        """Устанавливаем текущий трек плейлиста.

        Args:
            index (int): индекс (позиция) трека в плейлисте

        Returns:
            _type_: _description_
        """
        self.tracks.set_index(index)

    @staticmethod
    def load_playlist(playlist_path: str) -> tuple[str, list[Track], str | None]:
        """Загружаем плейлист из файла.

        Args:
            playlist_path (str): путь к файлу плейлиста

        Returns:
            tuple: название плейлиста и список треков
        """
        with open(playlist_path, encoding="utf-8") as file:
            playlist = json.load(file)
            name = str(playlist["name"])
            cover_path = playlist.get("cover_path", None)
            track_manager = TrackManager()
            tracks = [
                track_manager.get_track_from_playlist(
                    *(track["id"], track["title"], track["author"])
                )
                for track in playlist["tracks"]
            ]
        return name, tracks, cover_path

    @abstractmethod
    def get_tracks(self) -> Tuple[Track, ...]:
        """Получаем список треков из плейлиста

        Returns:
            Tuple[Track]: список треков
        """
        pass

    def __len__(self) -> int:
        return len(self.tracks)

    def __str__(self) -> str:
        return f"{self.name} - {len(self.tracks)}"

    __repr__ = __str__

class RecommendationPlaylist(Playlist):
    """Плейлист рекомендаций."""

    def __init__(
        self,
        name: str = "Рекомендации",
        tracks: Iterable[Track] | None = None,
        cover_path: str = get_asset_path("assets/icons/recomendation.svg"),
    ) -> None:
        super().__init__(name, tracks or (), cover_path)

    def get_tracks(self) -> Tuple[Track, ...]:
        """Получаем список треков из плейлиста

        Returns:
            Tuple[Track, ...]: список треков
        """
        return tuple(self.tracks.values)


class DownloadPlaylist(Playlist):
    """плейлист скачанных треков из music"""

    def __init__(
        self,
        name: str = "Скачанные",
        tracks: Iterable[Track] | None = None,
        cover_path: str = get_asset_path("assets/icons/download.svg"),
    ) -> None:
        super().__init__(name, tracks or (), cover_path)

    def get_tracks(self) -> Tuple[Track, ...]:
        """Получаем список треков из плейлиста

        Returns:
            Tuple[Track]: список треков
        """
        return tuple(self.tracks.values)

    def delete_track(self, track: Track) -> bool:
        path = PathProvider().get_track_path(track)
        try:
            os.remove(path)
            super().delete_track(track)
        except FileNotFoundError:
            pass
        except OSError:
            pass
        return True
    
    @classmethod
    def get_playlist_from_path(cls, path_to_playlist: str) -> "DownloadPlaylist | None":
        """Получаем плейлист из файла

        Args:
            path_to_playlist (str): путь к файлу плейлиста

        Returns:
            DownloadPlaylist: плейлист
        """
        return DownloadPlaylist(
            name="Скачанные", tracks=cls.get_tracks_from_music_dir()
        )

    @staticmethod
    def get_tracks_from_music_dir() -> Tuple[Track, ...]:
        """Получаем список треков из директории music.

        Returns:
            Tuple[Track]: список треков
        """
        music_dir = Path("music")
        if not music_dir.is_dir():
            return ()
        tracks = []
        for track_file in os.listdir(music_dir):
            try:
                name, ext = os.path.splitext(track_file)
                ext = ext.replace(".", "")
                parts = name.split("_", 2)
                if len(parts) < 3:
                    continue
                track_id, track_title, track_author = parts
                if track_id.isdigit():
                    tracks.append(
                        YandexTrack(
                            track_id=track_id,
                            title=track_title,
                            author=track_author,
                            downloaded=True,
                        )
                    )
                else:
                    tracks.append(
                        YoutubeTrack(
                            track_id=track_id,
                            title=track_title,
                            author=track_author,
                            downloaded=True,
                            extension=ext,
                        )
                    )
            except Exception:
                continue
        return tuple(tracks)


class RecentlyPlayedPlaylist(Playlist):
    """Системный плейлист недавно прослушанных треков."""

    def __init__(
        self,
        name: str = "Недавно прослушанные",
        tracks: Iterable[Track] | None = None,
        cover_path: str = get_asset_path("assets/icons/recent.svg"),
    ) -> None:
        super().__init__(name, tracks or (), cover_path)

    def get_tracks(self) -> Tuple[Track, ...]:
        """Возвращает треки недавно прослушанного плейлиста."""
        return tuple(self.tracks.values)

    @classmethod
    def get_playlist_from_path(
        cls, path_to_playlist: str
    ) -> "RecentlyPlayedPlaylist | None":
        """Плейлист строится из БД, поэтому чтение с диска не используется."""
        return None


class LikedPlaylist(Playlist):
    """Системный плейлист любимых треков."""

    def __init__(
        self,
        name: str = "Любимые",
        tracks: Iterable[Track] | None = None,
        cover_path: str = get_asset_path("assets/icons/heart.svg"),
    ) -> None:
        super().__init__(name, tracks or (), cover_path)

    def get_tracks(self) -> Tuple[Track, ...]:
        return tuple(self.tracks.values)


class WavePlaylist(Playlist):
    """Моя волна — персональное радио (Yandex / позже YouTube)."""

    def __init__(
        self,
        name: str = "Моя волна",
        tracks: Iterable[Track] | None = None,
        cover_path: str = get_asset_path("assets/icons/radio.svg"),
        *,
        source: str = "yandex",
        station: str = "user:onyourwave",
        batch_id: str | None = None,
    ) -> None:
        super().__init__(name, tracks or (), cover_path)
        self.source = source
        self.station = station
        self.batch_id = batch_id

    def get_tracks(self) -> Tuple[Track, ...]:
        return tuple(self.tracks.values)

    def append_tracks(self, tracks: Iterable[Track]) -> int:
        """Добавляет новые треки в конец (без дублей). Возвращает число добавленных."""
        existing = {str(t.track_id) for t in self.tracks.values}
        extra = [t for t in tracks if str(t.track_id) not in existing]
        if not extra:
            return 0
        self.tracks.values = tuple(list(self.tracks.values) + extra)
        return len(extra)


class UserPlaylist(Playlist):
    @classmethod
    def get_playlist_from_path(cls, path_to_playlist: str) -> "UserPlaylist | None":
        """Получаем плейлист из файла

        Args:
            path_to_playlist (str): путь к файлу плейлиста

        Returns:
            UserPlaylist: плейлист
        """
        if os.path.exists(path_to_playlist):
            return UserPlaylist(*cls.load_playlist(path_to_playlist))
        else:
            return None

    def get_tracks(self) -> Tuple[Track, ...]:
        """Получаем список треков из плейлиста

        Returns:
            Tuple[Track, ...]: список треков
        """
        return tuple(self.tracks.values)