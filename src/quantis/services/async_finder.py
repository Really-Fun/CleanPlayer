"""
Асинхронный поиск треков по платформам:
Yandex
Youtube
"""

from abc import ABC, abstractmethod
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

import yandex_music.exceptions

from quantis.config import Clients
from quantis.models import Track, YandexTrack, YoutubeTrack

logger = logging.getLogger(__name__)


class AsyncFinderInterface(ABC):
    @abstractmethod
    async def get_tracks(self, title: str, value: int = 5) -> list[Track]: ...

    @abstractmethod
    async def get_track(self, id: int) -> Track | None: ...


class AsyncYandexFinder(AsyncFinderInterface):
    def __init__(self):
        self.client = Clients().get_yandex_client()

    async def get_tracks(self, title: str, value: int = 5) -> list[Track]:
        if self.client is None:
            return []
        try:
            search_result = await self.client.search(
                title, type_="track",
            )
            if not search_result or not search_result.tracks:
                return []
                
            results = search_result.tracks.results[:value]
            return [
                YandexTrack(
                    track_id=str(track.id),
                    title=track.title,
                    author=" & ".join(artist.name for artist in track.artists if artist.name),
                    downloaded=False,
                )
                for track in results
            ]
        except yandex_music.exceptions.NetworkError:
            logger.exception("Ошибка сети при поиске на Yandex: %s", title)
            return []
        except yandex_music.exceptions.YandexMusicError:
            logger.exception("Ошибка Yandex Music API при поиске: %s", title)
            return []

    async def get_track(self, id: int) -> Track | None:
        if self.client is None:
            return None
        try:
            track_info = await self.client.tracks(id)
            track = track_info[0]
            return YandexTrack(
                track["id"],
                track["title"],
                " & ".join(artist["name"] for artist in track["artists"]),
                downloaded=False,
            )
        except yandex_music.exceptions.YandexMusicError:
            logger.exception("Ошибка Yandex Music API при получении трека: %s", id)
            return None


class AsyncYoutubeFinder(AsyncFinderInterface):
    def __init__(self, executor: ThreadPoolExecutor) -> None:
        self.client = Clients().get_youtube_client()
        self._executor = executor

    async def get_tracks(self, title: str, value: int = 5) -> list[Track]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor, self._sync_get_tracks, title, value
        )

    async def get_track(self, id: str | int) -> Track | None:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor, self._sync_get_track, id
        )

    def _sync_get_tracks(self, title: str, value: int = 5) -> list[Track]:
        try:
            results = self.client.search(query=title, filter="songs", limit=value)
            if not results:
                results = [self.client.get_song(videoId=title)["videoDetails"]]
        except Exception as e:
            logger.debug("Ошибка поиска YTMusic для '%s': %s", title, e)
            return []

        tracks = []
        for track in results:
            try:
                authors = " | ".join([author["name"] for author in track.get("artists", [])])
            except Exception:
                authors = "Unknown Artist"
                
            tracks.append(
                YoutubeTrack(
                    track_id=track.get("videoId"),
                    title=track.get("title"),
                    author=authors,
                    downloaded=False,
                )
            )
        return tracks

    def _sync_get_track(self, id: str | int) -> Track | None:
        try:
            results = self.client.get_song(str(id))
            if not results:
                return None
            video_details = results.get("videoDetails", {})
            track_id = video_details.get("videoId") or id
            track_title = video_details.get("title", "")
            authors = " | ".join([author["name"] for author in video_details.get("artists", [])])
            return YoutubeTrack(
                track_id=track_id, title=track_title, author=authors, downloaded=False
            )
        except Exception as e:
            logger.error("Ошибка YTMusic при получении трека %s: %s", id, e)
            return None


class AsyncFinder(AsyncFinderInterface):
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="FinderPool")
        self._yandex_finder = AsyncYandexFinder()
        self._youtube_finder = AsyncYoutubeFinder(self._executor)

    async def get_tracks(self, title: str, value: int = 5) -> list[Track]:
        """Ищет треки на Яндексе и YouTube ОДНОВРЕМЕННО."""

        yandex_task = asyncio.create_task(self._yandex_finder.get_tracks(title, value))
        youtube_task = asyncio.create_task(self._youtube_finder.get_tracks(title, value))
        
        yandex_tracks, youtube_tracks = await asyncio.gather(
            yandex_task, youtube_task, return_exceptions=True
        )
        
        if isinstance(yandex_tracks, Exception):
            yandex_tracks = []
        if isinstance(youtube_tracks, Exception):
            youtube_tracks = []
            
        return yandex_tracks + youtube_tracks

    async def get_track(self, id: str | int) -> Track | None:
        """Ищет трек по ID на обеих платформах."""
        yandex_track = await self._yandex_finder.get_track(id)
        if yandex_track is not None:
            return yandex_track
        return await self._youtube_finder.get_track(id)
        
    def shutdown(self):
        """Очищает пул потоков при закрытии приложения."""
        self._executor.shutdown(wait=False)