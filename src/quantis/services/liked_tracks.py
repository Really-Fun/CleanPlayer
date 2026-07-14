"""Сервис любимых треков."""

from __future__ import annotations

import asyncio

from quantis.database import sync_history
from quantis.models import LikedPlaylist, Track, YandexTrack, YoutubeTrack
from quantis.providers import TrackManager
from quantis.services.TrackHistoryService import TrackHistoryService


class LikedTracksService:
    """CRUD для плейлиста «Любимые»."""

    _instance: LikedTracksService | None = None

    def __new__(cls) -> LikedTracksService:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._track_manager = TrackManager()
        self._initialized = True

    async def is_liked(self, track: Track) -> bool:
        key = TrackHistoryService.build_track_key(track)
        return await asyncio.to_thread(sync_history.is_track_liked, key)

    async def set_liked(self, track: Track, liked: bool) -> None:
        await asyncio.to_thread(
            sync_history.set_track_liked,
            track_key=TrackHistoryService.build_track_key(track),
            title=track.title,
            author=track.author,
            source=str(track.source),
            liked=liked,
        )

    async def toggle(self, track: Track) -> bool:
        liked = await self.is_liked(track)
        await self.set_liked(track, not liked)
        return not liked

    async def get_playlist(self) -> LikedPlaylist:
        entries = await asyncio.to_thread(sync_history.fetch_liked_entries)
        tracks = await asyncio.to_thread(self._build_tracks, entries)
        return LikedPlaylist(tracks=tracks)

    def _build_tracks(self, entries: list[dict]) -> list[Track]:
        tracks: list[Track] = []
        for entry in entries:
            source, track_id = TrackHistoryService._split_track_key(
                entry["track_key"], entry["source"]
            )
            downloaded = self._track_manager.is_downloaded(str(track_id))
            if source == "yandex":
                tracks.append(
                    YandexTrack(
                        track_id=int(track_id) if str(track_id).isdigit() else track_id,
                        title=entry["title"],
                        author=entry["author"],
                        downloaded=downloaded,
                    )
                )
            else:
                tracks.append(
                    YoutubeTrack(
                        track_id=track_id,
                        title=entry["title"],
                        author=entry["author"],
                        downloaded=downloaded,
                    )
                )
        return tracks
