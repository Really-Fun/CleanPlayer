"""Сервис истории прослушивания.

Слой бизнес-логики между Player и репозиторием БД.
"""

from __future__ import annotations

import asyncio
from time import monotonic

from quantis.database import sync_history
from quantis.models import RecentlyPlayedPlaylist, Track, YandexTrack, YoutubeTrack
from quantis.providers import TrackManager


class TrackHistoryService:
    """Сервис сохранения/чтения прогресса треков.

    Реализован как Singleton, чтобы в приложении использовалась одна БД-сессия.
    """

    _instance: "TrackHistoryService | None" = None

    def __new__(cls) -> "TrackHistoryService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, save_interval_sec: float = 5.0) -> None:
        if getattr(self, "_initialized", False):
            return
        self._save_interval_sec = max(1.0, save_interval_sec)
        self._last_saved_by_key: dict[str, float] = {}
        self._track_manager = TrackManager()
        self._initialized = True

    @staticmethod
    def build_track_key(track: Track) -> str:
        """Строит стабильный ключ трека для БД."""
        return f"{track.source}:{track.track_id}"

    async def get_resume_position(self, track: Track) -> int:
        """Возвращает сохраненную позицию для продолжения трека."""
        track_key = self.build_track_key(track)
        return await asyncio.to_thread(sync_history.get_saved_position, track_key)

    async def save_progress(
        self,
        track: Track,
        position_ms: int,
        duration_ms: int,
        *,
        force: bool = False,
    ) -> None:
        """Сохраняет прогресс трека с ограничением частоты записи."""
        track_key = self.build_track_key(track)
        now = monotonic()
        last_saved = self._last_saved_by_key.get(track_key, 0.0)
        if not force and now - last_saved < self._save_interval_sec:
            return

        await asyncio.to_thread(
            sync_history.upsert_progress,
            track_key=track_key,
            title=track.title,
            author=track.author,
            source=str(track.source),
            position_ms=position_ms,
            duration_ms=duration_ms,
            listen_increment=0,
        )
        self._last_saved_by_key[track_key] = now

    async def mark_track_finished(
        self, track: Track, position_ms: int, duration_ms: int
    ) -> None:
        """Сохраняет финальное состояние и увеличивает число прослушиваний."""
        track_key = self.build_track_key(track)
        await asyncio.to_thread(
            sync_history.upsert_progress,
            track_key=track_key,
            title=track.title,
            author=track.author,
            source=str(track.source),
            position_ms=position_ms,
            duration_ms=duration_ms,
            listen_increment=1,
        )
        self._last_saved_by_key[track_key] = monotonic()

    async def get_recent_playlist(
        self, limit: int = 24
    ) -> RecentlyPlayedPlaylist | None:
        """Формирует системный плейлист недавно прослушанных треков."""
        entries = await asyncio.to_thread(sync_history.fetch_recent_entries, limit)
        if not entries:
            return None
        tracks = await asyncio.to_thread(self._build_tracks_from_entries, entries)
        return RecentlyPlayedPlaylist(tracks=tracks)

    async def close(self) -> None:
        """Заглушка для совместимости при завершении приложения."""

    def _build_tracks_from_entries(self, entries: list[dict]) -> list[Track]:
        tracks: list[Track] = []
        for entry in entries:
            source, track_id = self._split_track_key(entry["track_key"], entry["source"])
            downloaded = self._track_manager.is_downloaded(str(track_id))
            if source == "yandex":
                tracks.append(
                    YandexTrack(
                        track_id=int(track_id) if str(track_id).isdigit() else track_id,
                        title=entry["title"],
                        author=entry["author"],
                        downloaded=downloaded,
                        listen_count=int(entry["listen_count"]),
                    )
                )
            else:
                tracks.append(
                    YoutubeTrack(
                        track_id=str(track_id),
                        title=entry["title"],
                        author=entry["author"],
                        downloaded=downloaded,
                        listen_count=int(entry["listen_count"]),
                    )
                )
        return tracks

    @staticmethod
    def _split_track_key(track_key: str, source_fallback: str) -> tuple[str, str]:
        """Разбивает ключ ``source:id`` на составляющие."""
        if ":" not in track_key:
            return source_fallback or "youtube", track_key
        source, raw_id = track_key.split(":", 1)
        return source or source_fallback, raw_id
