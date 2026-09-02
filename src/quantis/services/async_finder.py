"""
Асинхронный поиск треков по платформам:
Yandex
Youtube
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from concurrent.futures import ThreadPoolExecutor

import yandex_music.exceptions

from quantis.config import Clients
from quantis.config.credentials import yandex_token
from quantis.models import Track, YoutubeTrack
from quantis.services.yandex_finder import yandex_track_from_api, yandex_tracks_from_search

logger = logging.getLogger(__name__)


class AsyncFinderInterface(ABC):
    @abstractmethod
    async def get_tracks(self, title: str, value: int = 5) -> list[Track]: ...

    @abstractmethod
    async def get_track(self, track_id: str | int) -> Track | None: ...


class AsyncYandexFinder(AsyncFinderInterface):
    def __init__(self, executor: ThreadPoolExecutor | None = None) -> None:
        self._executor = executor

    def _client(self):
        if not yandex_token():
            return None
        return Clients().get_yandex_client()

    async def get_tracks(self, title: str, value: int = 5) -> list[Track]:
        client = self._client()
        if client is None:
            logger.warning("Yandex: токен не задан в keyring — поиск только YouTube")
            return []
        try:
            search_result = await client.search(title, type_="track")
            return yandex_tracks_from_search(search_result, value)
        except yandex_music.exceptions.NetworkError:
            logger.exception("Ошибка сети при поиске на Yandex: %s", title)
            return []
        except yandex_music.exceptions.TimedOutError:
            logger.warning("Таймаут Yandex при поиске: %s", title)
            return []
        except yandex_music.exceptions.YandexMusicError:
            logger.exception("Ошибка Yandex Music API при поиске: %s", title)
            return []

    async def get_track(self, track_id: str | int) -> Track | None:
        try:
            yandex_id = int(track_id)
        except (ValueError, TypeError):
            return None

        client = self._client()
        if client is None:
            return None
        try:
            track_info = await client.tracks(yandex_id)
            if not track_info:
                return None
            return yandex_track_from_api(track_info[0])
        except yandex_music.exceptions.YandexMusicError:
            logger.exception(
                "Ошибка Yandex Music API при получении трека: %s", track_id
            )
            return None


class AsyncYoutubeFinder(AsyncFinderInterface):
    def __init__(self, executor: ThreadPoolExecutor) -> None:
        self._client = None
        self._executor = executor

    @property
    def client(self):
        if self._client is None:
            self._client = Clients().get_youtube_client()
        return self._client

    @property
    def executor(self) -> ThreadPoolExecutor:
        return self._executor

    async def get_tracks(self, title: str, value: int = 5) -> list[Track]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor, self._sync_get_tracks, title, value
        )

    async def get_track(self, track_id: str | int) -> Track | None:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor, self._sync_get_track, track_id
        )

    async def get_track_from_url(self, url: str) -> Track | None:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor, self._sync_get_track_from_url, url
        )

    def _sync_get_track_from_url(self, url: str) -> Track | None:
        from quantis.services.url_resolver import parse_track_id, parse_youtube_video_id

        parsed = parse_track_id(url)
        if parsed is not None:
            source, track_id = parsed
            if source == "youtube":
                return self._sync_get_track_from_yt_dlp(url, track_id)
            return None

        video_id = parse_youtube_video_id(url)
        if video_id:
            return self._sync_get_track_from_yt_dlp(url, video_id)
        return None

    def _sync_get_track_from_yt_dlp(self, url: str, video_id: str) -> Track | None:
        from yt_dlp import YoutubeDL

        opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
        }
        try:
            with YoutubeDL(opts) as yt:
                info = yt.extract_info(url, download=False)
            if not info:
                return self._sync_get_track(video_id)
            resolved_id = str(info.get("id") or video_id)
            title = str(info.get("title") or "")
            artists = info.get("artist") or info.get("uploader") or ""
            if not artists:
                channel = info.get("channel")
                artists = str(channel) if channel else "Unknown Artist"
            return YoutubeTrack(
                track_id=resolved_id,
                title=title,
                author=str(artists),
                downloaded=False,
            )
        except Exception as exc:
            logger.debug("yt-dlp не разобрал URL %s: %s", url, exc)
            return self._sync_get_track(video_id)

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
                authors = " | ".join(
                    author["name"] for author in track.get("artists", [])
                )
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

    def _sync_get_track(self, track_id: str | int) -> Track | None:
        try:
            results = self.client.get_song(str(track_id))
            if not results:
                return None
            video_details = results.get("videoDetails", {})
            resolved_id = video_details.get("videoId") or track_id
            track_title = video_details.get("title", "")
            authors = " | ".join(
                author["name"] for author in video_details.get("artists", [])
            )
            return YoutubeTrack(
                track_id=resolved_id,
                title=track_title,
                author=authors,
                downloaded=False,
            )
        except Exception as e:
            logger.error("Ошибка YTMusic при получении трека %s: %s", track_id, e)
            return None


class AsyncFinder(AsyncFinderInterface):
    _SOURCE_TIMEOUT_SEC = 10.0
    _DEFAULT_PER_SOURCE = 12

    def __init__(self, executor: ThreadPoolExecutor | None = None) -> None:
        from quantis.core.worker_pool import get_worker_pool

        self._owns_executor = False
        self._executor = executor or get_worker_pool()
        self._yandex_finder = AsyncYandexFinder(self._executor)
        self._youtube_finder = AsyncYoutubeFinder(self._executor)

    @property
    def youtube(self) -> AsyncYoutubeFinder:
        """YouTube-файндер для переиспользования в других сервисах."""
        return self._youtube_finder

    async def _fetch_source(
        self, source: str, title: str, value: int
    ) -> tuple[str, list[Track]]:
        timeout = self._SOURCE_TIMEOUT_SEC
        try:
            if source == "yandex":
                tracks = await asyncio.wait_for(
                    self._yandex_finder.get_tracks(title, value), timeout=timeout
                )
            else:
                tracks = await asyncio.wait_for(
                    self._youtube_finder.get_tracks(title, value), timeout=timeout
                )
            return source, tracks
        except TimeoutError:
            logger.warning("Таймаут поиска %s: %s", source, title)
            return source, []
        except Exception as exc:
            logger.exception("Ошибка поиска %s", source, exc_info=exc)
            return source, []

    async def iter_track_batches(
        self, title: str, value: int | None = None
    ) -> AsyncIterator[tuple[str, list[Track]]]:
        """Отдаёт результаты по мере готовности каждого источника."""
        limit = value if value is not None else self._DEFAULT_PER_SOURCE
        tasks = [
            asyncio.create_task(self._fetch_source("yandex", title, limit)),
            asyncio.create_task(self._fetch_source("youtube", title, limit)),
        ]
        try:
            for done in asyncio.as_completed(tasks):
                yield await done
        finally:
            pending = [task for task in tasks if not task.done()]
            for task in pending:
                try:
                    task.cancel()
                except RuntimeError:
                    logger.debug("Пропущена отмена задачи поиска: event loop уже закрыт")
            if pending:
                try:
                    await asyncio.gather(*pending, return_exceptions=True)
                except RuntimeError:
                    logger.debug("Пропущено завершение задач поиска: event loop уже закрыт")

    async def get_tracks(self, title: str, value: int = 5) -> list[Track]:
        """Ищет треки на Яндексе и YouTube одновременно."""
        tracks: list[Track] = []
        async for _source, batch in self.iter_track_batches(title, value):
            tracks.extend(batch)
        return tracks

    async def get_track(self, track_id: str | int) -> Track | None:
        """Ищет трек по ID: Yandex — только для числовых ID, иначе YouTube."""
        if isinstance(track_id, int) or (
            isinstance(track_id, str) and track_id.isdigit()
        ):
            yandex_track = await self._yandex_finder.get_track(track_id)
            if yandex_track is not None:
                return yandex_track
        return await self._youtube_finder.get_track(track_id)

    async def resolve_tracks(
        self,
        *,
        url: str | None = None,
        track_id: str | None = None,
        source: str | None = None,
    ) -> list[Track]:
        """Разрешает трек(и) по прямой ссылке или ID из конкретного источника.

        - Если передан url — определяет источник автоматически по домену.
        - Если передан track_id — требуется source (yandex|youtube).
        Возвращает список Track (для альбома/плейлиста может быть > 1).
        """
        from quantis.services.url_resolver import parse_track_id

        if url:
            parsed = parse_track_id(url)
            if parsed is None:
                logger.warning("Не удалось разобрать ссылку: %s", url)
                return []
            src, resolved_id = parsed
            if src == "yandex":
                track = await self._yandex_finder.get_track(resolved_id)
            else:
                track = await self._youtube_finder.get_track_from_url(url)
            return [track] if track is not None else []

        if track_id:
            normalized_source = (source or "").strip().lower()
            if normalized_source == "yandex":
                track = await self._yandex_finder.get_track(track_id)
            elif normalized_source == "youtube":
                track = await self._youtube_finder.get_track(track_id)
            else:
                logger.warning(
                    "resolve_tracks: для track_id=%r нужен source (yandex|youtube)",
                    track_id,
                )
                return []
            return [track] if track is not None else []

        return []

    def shutdown(self) -> None:
        """Пул потоков общий — не останавливаем здесь."""
        return