"""Асинхронное скачивание (треков, обложек)
Наследуется абстрактный класс
Yandex
Youtube"""

import logging
from abc import ABC, abstractmethod
from asyncio import Semaphore, get_running_loop
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

import aiofiles
import aiohttp
from yt_dlp import YoutubeDL

from quantis.config import Clients
from quantis.models.track import Track, TrackSource, YandexTrack, YoutubeTrack
from quantis.providers import PathProvider

logger = logging.getLogger(__name__)


class AsyncDownloaderInterface(ABC):
    """Абстрактный класс для Downloader'ов"""

    @abstractmethod
    async def download_track(self, track: Track | YandexTrack | YoutubeTrack) -> None: 
        ...

    @abstractmethod
    async def download_cover(self, track: Track | YandexTrack | YoutubeTrack) -> None:
        ...


class AsyncYandexDownloader(AsyncDownloaderInterface):
    """Класс для асинхронного скачивания треков и обложек с яндекса"""

    def __init__(self) -> None:
        self.path_provider = PathProvider()
        self.client = Clients().get_yandex_client()

    async def download_track(self, track: Track | YandexTrack | YoutubeTrack) -> None:
        """Скачивает трек с яндекса. Асинхронное скачивание

        Args:
            track (YandexTrack): Трек с Яндекса
        """
        if self.client is None:
            logger.warning("Клиент ЯндексМузыки не инициализирован." \
            "Невозможно скачать трек: %s", track)
            return
        try:
            PathProvider.ensure_storage_dirs()
            track_info = await self.client.tracks(int(track.track_id))
            current_track = track_info[0]
            file_path = self.path_provider.get_track_path(track)

            is_authorized = bool(getattr(self.client, "token", None))

            if is_authorized:
                await current_track.download_async(file_path)
            else:
                await current_track.download_async(file_path, bitrate_in_kbps=192)
        except Exception:
            logger.exception("Не удалось скачать трек с Яндекс.Музыки: %s", track)

    async def download_cover(self, track: Track | YandexTrack | YoutubeTrack) -> None:
        """Скачивает обложку трека с платформы Яндекс. Асинхронное скачивание

        Args:
            track (YandexTrack): Трек с Яндекса
        """
        if self.client is None:
            logger.warning("Клиент ЯндексМузыки не инициализирован." \
            "Невозможно скачать трек: %s", track)
            return
        try:
            PathProvider.ensure_storage_dirs()
            track_info = await self.client.tracks(int(track.track_id))
            await track_info[0].downloadCoverAsync(
                self.path_provider.get_cover_path(track), "200x200"
            )
        except Exception:
            logger.exception("Не удалось скачать обложку с Яндекс.Музыки: %s", track)


class AsyncYoutubeDownloader(AsyncDownloaderInterface):
    """Класс для асинхронного скачивания треков и обложек с ютуба"""

    def __init__(self) -> None:
        self.opts = {
            "quiet": True,
            "noplaylist": True,
            "extract_flat": False,
            "no_warnings": True,
            "nocheckcertificate": True,
            "format": "bestaudio",
            "postprocessors": [],
        }
        self.path_provider = PathProvider()
        self._executor = ThreadPoolExecutor(max_workers=10)
        self._session: Optional[aiohttp.ClientSession] = None
        self._semaphore = Semaphore(value=8)

    async def get_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def download_track(self, track: Track | YandexTrack | YoutubeTrack) -> None:
        """Асинхронная функция для скачивания трека с ютуба.
        Основана на ThreadPoolExecutor и синхронном скачивании с ytdlp

        Args:
            track (YoutubeTrack): трек с Ютуба
        """
        self.opts["outtmpl"] = self.path_provider.get_track_path(
            track, extension="%(ext)s"
        )
        await get_running_loop().run_in_executor(
            self._executor, self.sync_download, self.opts, track.track_id
        )

    async def download_cover(self, track:  Track | YandexTrack | YoutubeTrack) -> None:
        """Асинхронное получение обложки с ютуб.

        Args:
            track (YoutubeTrack): Трек с Ютуба
        """
        cover_url = f"https://img.youtube.com/vi/{track.track_id}/hqdefault.jpg"
        cover_path = self.path_provider.get_cover_path(track)

        session = await self.get_session()

        async with self._semaphore:
            try:
                async with session.get(cover_url) as response:
                    if response.status != 200:
                        return
                    data = await response.read()

                    Path(cover_path).parent.mkdir(parents=True, exist_ok=True)
                    async with aiofiles.open(cover_path, "wb") as file:
                        await file.write(data)
            except aiohttp.ClientError:
                logger.exception("Ошибка при скачивании обложки для %s", track.track_id)

    @staticmethod
    def sync_download(opts: dict, track_id: int | str) -> None:
        try:
            with YoutubeDL(opts) as ydl:
                ydl.extract_info(
                    f"https://youtube.com/watch?v={track_id}", download=True
                )
        except Exception:
            logger.exception("Не удалось скачать трек с YouTube: %s", track_id)

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()
            self._session = None

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False)


class AsyncDownloader(AsyncDownloaderInterface):
    def __init__(self) -> None:
        self._yandex_downloader = AsyncYandexDownloader()
        self._youtube_downloader = AsyncYoutubeDownloader()

    async def download_track(self, track: Track) -> None:
        match track.source:
            case TrackSource.YANDEX:
                await self._yandex_downloader.download_track(track)
            case TrackSource.YOUTUBE:
                await self._youtube_downloader.download_track(track)

    async def download_cover(self, track: Track) -> None:
        match track.source:
            case TrackSource.YANDEX:
                await self._yandex_downloader.download_cover(track)
            case TrackSource.YOUTUBE:
                await self._youtube_downloader.download_cover(track)

    def shutdown(self) -> None:
        self._youtube_downloader.shutdown()

    async def close(self) -> None:
        await self._youtube_downloader.close()
