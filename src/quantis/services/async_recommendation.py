"""Асинхронный сервис рекомендаций треков (YouTube Radio / Watch Playlist)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from quantis.config import Clients
from quantis.models import RecommendationPlaylist, Track, YoutubeTrack
from quantis.models.track import clock_to_ms, seconds_to_ms

from .async_finder import AsyncYoutubeFinder

logger = logging.getLogger(__name__)


class AsyncRecommendation:
    """Генерирует радио на основе трека через YouTube Music Watch Playlist."""

    def __init__(
        self,
        youtube_finder: AsyncYoutubeFinder,
        client: Any | None = None,
    ) -> None:
        self._finder = youtube_finder
        self._client = client

    @property
    def _yt(self):
        if self._client is None:
            self._client = Clients().get_youtube_client()
        return self._client

    async def generate_radio_from_track(self, track: Track) -> RecommendationPlaylist:
        video_id = track.track_id
        if not isinstance(track, YoutubeTrack):
            video_id = await self._get_youtube_id(track)

        result = await asyncio.get_running_loop().run_in_executor(
            self._finder.executor,
            lambda: self._yt.get_watch_playlist(videoId=video_id, limit=10),
        )

        tracks = [
            YoutubeTrack(
                track_id=track_info["videoId"],
                title=track_info["title"],
                author=", ".join(a["name"] for a in track_info.get("artists", [])),
                downloaded=False,
                duration_ms=seconds_to_ms(track_info.get("lengthSeconds"))
                or clock_to_ms(track_info.get("duration")),
            )
            for track_info in result.get("tracks", [])
        ]

        return RecommendationPlaylist(name=track.title + track.author, tracks=tracks)

    async def _get_youtube_id(self, track: Track) -> str:
        """Ищет YouTube ID для не-YouTube трека."""
        results = await self._finder.get_tracks(f"{track.title} {track.author}", value=1)
        return results[0].track_id


# Алиас для обратной совместимости
AsyncRecomendation = AsyncRecommendation
