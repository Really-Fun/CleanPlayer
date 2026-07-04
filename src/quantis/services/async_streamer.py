"""Асинхронный стриминг (получение прямых URL для воспроизведения).

Поддерживаемые платформы:
- Яндекс Музыка
- YouTube
"""

from __future__ import annotations

import functools
import logging
from abc import ABC, abstractmethod
from asyncio import get_running_loop
from concurrent.futures import ThreadPoolExecutor
from time import time

from yt_dlp import YoutubeDL

from quantis.config import Clients
from quantis.models import Track

logger = logging.getLogger(__name__)

def cached_stream_url(func):
    """Декоратор для кэширования прямых URL треков внутри методов класса Streamer."""
    @functools.wraps(func)
    async def wrapper(self, track: Track, *args, **kwargs):
        track_key = str(track.track_id)
        
        cached = self._cache.get(track_key)
        if cached is not None and (time() - cached[1] < self._URL_CACHE_TTL_SEC):
            return cached[0]
            
        url = await func(self, track, *args, **kwargs)
        
        if url is not None:
            self._cache[track_key] = (url, time())
            
        return url
    return wrapper


class AsyncStreamerInterface(ABC):
    @abstractmethod
    async def get_stream_url(self, track: Track) -> str | None: ...


class AsyncYandexStreamer(AsyncStreamerInterface):
    def __init__(self):
        self.client = Clients().get_yandex_client()

    async def get_stream_url(self, track: Track) -> str | None:
        if self.client is None:
            return None
        try:
            track_info = await self.client.tracks(track.track_id)
            download_info = await track_info[0].get_download_info_async()
            url = await download_info[0].get_direct_link_async()
            return url
        except Exception:
            logger.exception("Не удалось получить URL потока Яндекс.Музыки: %s", track)
            return None


class AsyncYoutubeStreamer(AsyncStreamerInterface):
    _URL_CACHE_TTL_SEC = 30 * 60

    def __init__(self) -> None:
        self.opts = {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "quiet": False,
            "noplaylist": True,
            "extract_flat": False,
            "no_warnings": True,
            "nocheckcertificate": True,
            "postprocessors": [],
            "format": "m4a/bestaudio[ext=m4a]",
            "skip_download": True,
        }
        self.yt = YoutubeDL(self.opts)
        self._executor = ThreadPoolExecutor(max_workers=2)

    async def get_stream_url(self, track: Track) -> str | None:
        url = await get_running_loop().run_in_executor(
            self._executor, self.sync_stream, self.yt, track.track_id
        )
        return url

    @staticmethod
    def sync_stream(yt, track_id: str) -> str | None:
        try:
            info = yt.extract_info(
                f"https://www.youtube.com/watch?v={track_id}", download=False
            )
            return info.get("url")
        except Exception:
            logger.exception("Не удалось получить URL потока YouTube: %s", track_id)
            return None


class AsyncStreamer(AsyncStreamerInterface):
    """Фасад над Yandex и YouTube стримерами с кэшированием URL через декоратор."""

    _URL_CACHE_TTL_SEC = 30 * 60  # 30 минут

    def __init__(self, executor: ThreadPoolExecutor | None = None) -> None:
        self._executor = executor or ThreadPoolExecutor(max_workers=4, thread_name_prefix="StreamerPool")
        self._yandex = AsyncYandexStreamer()
        self._youtube = AsyncYoutubeStreamer(self._executor)

        self._cache: dict[str, tuple[str, float]] = {}

    @cached_stream_url
    async def get_stream_url(self, track: Track) -> str | None:
        """Получает прямой URL. Декоратор @cached_stream_url сам проверит и заполнит кэш."""
        source_type = str(track.source).lower()
        
        if source_type == "youtube":
            return await self._youtube.get_stream_url(track)
        elif source_type == "yandex":
            return await self._yandex.get_stream_url(track)
            
        raise NameError(f"Неизвестный источник платформы у трека: {track.source!r}")

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False)
