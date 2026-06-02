"""Асинхронный сервис рекомендаций треков (YouTube Radio / Watch Playlist)."""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from ytmusicapi import YTMusic

from quantis.config import Clients
from quantis.models import RecommendationPlaylist, Track, YoutubeTrack

from .AsyncFinder import AsyncYoutubeFinder

logger = logging.getLogger(__name__)


class AsyncRecommendation:
    """Генерирует радио на основе трека через YouTube Music Watch Playlist."""

    def __init__(self) -> None:
        self.client: YTMusic = Clients().get_youtube_client()
        self.finder: AsyncYoutubeFinder = AsyncYoutubeFinder()

    async def generate_radio_from_track(self, track: Track) -> RecommendationPlaylist:
        video_id = track.track_id
        if not isinstance(track, YoutubeTrack):
            video_id = await self._get_youtube_id(track)

        with ThreadPoolExecutor() as thread:
            result = await asyncio.get_running_loop().run_in_executor(
                thread,
                lambda: self.client.get_watch_playlist(videoId=video_id, limit=10),
            )

        tracks = [
            YoutubeTrack(
                track_id=track_info["videoId"],
                title=track_info["title"],
                author=", ".join(a["name"] for a in track_info.get("artists", [])),
                downloaded=False,
            )
            for track_info in result.get("tracks", [])
        ]

        return RecommendationPlaylist(name=track.title + track.author, tracks=tracks)

    async def _get_youtube_id(self, track: Track) -> str:
        """Ищет YouTube ID для не-YouTube трека."""
        results = await self.finder.get_tracks(
            f"{track.title} {track.author}", value=1
        )
        return results[0].track_id


# Алиас для обратной совместимости
AsyncRecomendation = AsyncRecommendation

