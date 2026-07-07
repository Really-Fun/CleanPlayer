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
from pathlib import Path
from time import time

from yt_dlp import YoutubeDL

from quantis.config import Clients
from quantis.models import Track, TrackSource
from quantis.providers import PathProvider

logger = logging.getLogger(__name__)


def cached_stream_url(func):
    """Декоратор для кэширования прямых URL треков внутри методов класса Streamer."""

    @functools.wraps(func)
    async def wrapper(self, track: Track, *args, **kwargs):
        track_key = f"{track.source}:{track.track_id}"

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
    def __init__(self, executor: ThreadPoolExecutor) -> None:
        self._executor = executor

    async def get_stream_url(self, track: Track) -> str | None:
        return await get_running_loop().run_in_executor(
            self._executor, self._sync_get_stream_url, track
        )

    def _yandex_token(self) -> str | None:
        from keyring import get_password

        from quantis.config.constants import SERVICE_NAME_YANDEX, USER

        return get_password(SERVICE_NAME_YANDEX, USER)

    def _sync_get_stream_url(self, track: Track) -> str | None:
        token = self._yandex_token()
        if not token:
            return None
        try:
            from yandex_music import Client

            track_id = int(track.track_id)
            track_info = Client(token).tracks(track_id)
            if not track_info:
                return None
            download_info = track_info[0].get_download_info()
            if not download_info:
                return None
            return download_info[0].get_direct_link()
        except Exception:
            logger.exception("Не удалось получить URL потока Яндекс.Музыки: %s", track)
            return None


class AsyncYoutubeStreamer(AsyncStreamerInterface):
    def __init__(self, executor: ThreadPoolExecutor) -> None:
        self.opts = {
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
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
        self._video_opts = {
            **self.opts,
            "format": (
                "18/22/b[ext=mp4][vcodec!=none][height<=720]/"
                "best[vcodec!=none][height<=720][ext=mp4]"
            ),
        }
        self._video_yt = YoutubeDL(self._video_opts)
        self._executor = executor

    async def get_stream_url(self, track: Track) -> str | None:
        return await get_running_loop().run_in_executor(
            self._executor, self.sync_stream, self.yt, track.track_id
        )

    async def get_video_url(self, video_id: str) -> str | None:
        return await get_running_loop().run_in_executor(
            self._executor, self.sync_video_stream, self._video_yt, video_id
        )

    async def download_wallpaper_clip(self, video_id: str) -> str | None:
        return await get_running_loop().run_in_executor(
            self._executor, self.sync_download_wallpaper_clip, video_id
        )

    @staticmethod
    def sync_download_wallpaper_clip(video_id: str) -> str | None:
        cache_dir = Path(PathProvider.WALLPAPER_CLIPS_FOLDER)
        cache_dir.mkdir(parents=True, exist_ok=True)
        for existing in cache_dir.glob(f"{video_id}.*"):
            if existing.is_file() and existing.stat().st_size > 0:
                return str(existing.resolve())

        out_base = cache_dir / video_id
        url = f"https://www.youtube.com/watch?v={video_id}"
        opts = {
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "nocheckcertificate": True,
            "format": (
                "18/22/b[ext=mp4][vcodec!=none][height<=720]/"
                "best[vcodec!=none][height<=720][ext=mp4]"
            ),
            "outtmpl": str(out_base) + ".%(ext)s",
        }
        try:
            with YoutubeDL(opts) as yt:
                yt.download([url])
        except Exception:
            logger.exception("Не удалось скачать видео-клип для обоев: %s", video_id)
            return None

        for candidate in cache_dir.glob(f"{video_id}.*"):
            if candidate.is_file() and candidate.stat().st_size > 0:
                return str(candidate.resolve())
        return None

    @staticmethod
    def sync_stream(yt: YoutubeDL, track_id: str) -> str | None:
        try:
            info = yt.extract_info(
                f"https://www.youtube.com/watch?v={track_id}", download=False
            )
            if info is None:
                return None
            return info.get("url")
        except Exception:
            logger.exception("Не удалось получить URL потока YouTube: %s", track_id)
            return None

    @staticmethod
    def sync_video_stream(yt: YoutubeDL, track_id: str) -> str | None:
        try:
            info = yt.extract_info(
                f"https://www.youtube.com/watch?v={track_id}", download=False
            )
            if info is None:
                return None

            url = info.get("url")
            vcodec = info.get("vcodec")
            if url and vcodec not in (None, "none"):
                return url

            progressive: str | None = None
            fallback: str | None = None
            for fmt in info.get("formats") or []:
                fmt_url = fmt.get("url")
                if not fmt_url:
                    continue
                if fmt.get("vcodec") in (None, "none"):
                    continue
                if fmt.get("acodec") not in (None, "none"):
                    progressive = fmt_url
                    break
                if fallback is None:
                    fallback = fmt_url

            return progressive or fallback
        except Exception:
            logger.exception("Не удалось получить URL видео YouTube: %s", track_id)
            return None


class AsyncStreamer(AsyncStreamerInterface):
    """Фасад над Yandex и YouTube стримерами с кэшированием URL через декоратор."""

    _URL_CACHE_TTL_SEC = 30 * 60  # 30 минут

    def __init__(self, executor: ThreadPoolExecutor | None = None) -> None:
        self._owns_executor = executor is None
        self._executor = executor or ThreadPoolExecutor(
            max_workers=4, thread_name_prefix="StreamerPool"
        )
        self._yandex = AsyncYandexStreamer(self._executor)
        self._youtube = AsyncYoutubeStreamer(self._executor)
        self._cache: dict[str, tuple[str, float]] = {}

    @cached_stream_url
    async def get_stream_url(self, track: Track) -> str | None:
        """Получает прямой URL. Декоратор @cached_stream_url сам проверит и заполнит кэш."""
        source_type = str(track.source).lower()

        if source_type == TrackSource.YOUTUBE:
            return await self._youtube.get_stream_url(track)
        if source_type == TrackSource.YANDEX:
            return await self._yandex.get_stream_url(track)

        raise ValueError(f"Неизвестный источник платформы у трека: {track.source!r}")

    async def get_video_url(self, track: Track, finder: object | None = None) -> str | None:
        """Локальный mp4-клип для динамических обоев (кэш в wallpaper_clips/)."""
        video_id = await self._resolve_youtube_video_id(track, finder)
        if not video_id:
            return None
        return await self._youtube.download_wallpaper_clip(video_id)

    async def _resolve_youtube_video_id(
        self, track: Track, finder: object | None
    ) -> str | None:
        source_type = str(track.source).lower()
        if source_type == TrackSource.YOUTUBE:
            return str(track.track_id)

        if finder is None:
            return None
        query = f"{track.title} {track.author}"
        try:
            results = await finder.get_tracks(query, value=3)  # type: ignore[attr-defined]
        except Exception:
            logger.exception("Поиск YouTube-видео для обоев: %s", query)
            return None
        youtube_hit = next(
            (t for t in results if str(t.source).lower() == TrackSource.YOUTUBE),
            None,
        )
        return str(youtube_hit.track_id) if youtube_hit else None

    def shutdown(self) -> None:
        if self._owns_executor:
            self._executor.shutdown(wait=False)
