"""Асинхронный стриминг (получение прямых URL для воспроизведения)."""

from __future__ import annotations

import logging
from asyncio import get_running_loop
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from quantis.models import Track, TrackSource
from quantis.services.stream_cache import cached_stream_url
from quantis.services.yandex_streamer import AsyncStreamerInterface, AsyncYandexStreamer
from quantis.services.youtube_streamer import AsyncYoutubeStreamer

logger = logging.getLogger(__name__)


class AsyncStreamer(AsyncStreamerInterface):
    """Фасад над Yandex и YouTube стримерами с кэшированием URL."""

    _URL_CACHE_TTL_SEC = 50
    _URL_CACHE_MAX = 64

    def __init__(self, executor: ThreadPoolExecutor | None = None) -> None:
        from quantis.core.worker_pool import get_worker_pool
        from quantis.services.yandex_progressive_buffer import ProgressiveStreamBuffer

        self._owns_executor = False
        self._executor = executor or get_worker_pool()
        self._yandex = AsyncYandexStreamer(self._executor)
        self._youtube = AsyncYoutubeStreamer(self._executor)
        self._stream_buffer = ProgressiveStreamBuffer(self._fetch_fresh_stream_url)
        self._buffer_loop: Any = None
        self._cache: OrderedDict[str, tuple[str, float]] = OrderedDict()

    async def _fetch_fresh_stream_url(self, track: Track) -> str | None:
        """Прямой URL без кэша фасада (для progressive buffer / recovery)."""
        source_type = str(track.source).lower()
        if source_type == TrackSource.YOUTUBE:
            return await self._youtube.get_stream_url(track)
        if source_type == TrackSource.YANDEX:
            return await self._yandex.get_stream_url(track)
        return None

    @cached_stream_url
    async def get_stream_url(self, track: Track) -> str | None:
        source_type = str(track.source).lower()
        if source_type == TrackSource.YOUTUBE:
            return await self._youtube.get_stream_url(track)
        if source_type == TrackSource.YANDEX:
            return await self._yandex.get_stream_url(track)
        raise ValueError(f"Неизвестный источник платформы у трека: {track.source!r}")

    async def open_playback(self, track: Track) -> str | None:
        """Стриминг через progressive buffer — стабильнее прямого HTTP (YouTube/Yandex)."""
        self._buffer_loop = get_running_loop()
        source_type = str(track.source).lower()
        if source_type in (TrackSource.YANDEX, TrackSource.YOUTUBE):
            path = await self._stream_buffer.open(track)
            if path:
                self._stream_buffer.cleanup_old_files(keep=Path(path))
            return path
        return await self.get_stream_url(track)

    async def prefetch_stream(self, track: Track) -> None:
        try:
            await self.get_stream_url(track)
        except Exception:
            logger.debug("Prefetch stream failed for %s", track.track_id, exc_info=True)

    async def get_video_url(self, track: Track, finder: object | None = None) -> str | None:
        video_id = await self._resolve_youtube_video_id(track, finder)
        if not video_id:
            return None
        return await self._youtube.get_video_url(video_id)

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

    def invalidate(self, track: Track) -> None:
        key = f"{track.source}:{track.track_id}"
        self._cache.pop(key, None)
        self._stream_buffer.invalidate_track(track)

    def set_eco(self, enabled: bool) -> None:
        self._stream_buffer.set_eco(enabled)

    def shutdown(self) -> None:
        if self._buffer_loop is not None:
            from concurrent.futures import TimeoutError as FuturesTimeoutError

            future = __import__("asyncio").run_coroutine_threadsafe(
                self._stream_buffer.close(),
                self._buffer_loop,
            )
            try:
                future.result(timeout=3)
            except FuturesTimeoutError:
                logger.debug("Таймаут остановки Yandex buffer")
            except Exception:
                logger.debug("Ошибка остановки Yandex buffer", exc_info=True)
        if self._owns_executor:
            self._executor.shutdown(wait=False)
