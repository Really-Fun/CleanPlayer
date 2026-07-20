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
from typing import Any

from yt_dlp import YoutubeDL

from quantis.config import Clients
from quantis.models import Track, TrackSource

logger = logging.getLogger(__name__)


def cached_stream_url(func: callable) -> callable:
    """Декоратор для кэширования прямых URL треков внутри методов класса Streamer."""

    @functools.wraps(func)
    async def wrapper(
        self: AsyncStreamerInterface, track: Track, *args: tuple, **kwargs: dict
    ) -> str | None:
        from collections import OrderedDict

        track_key = f"{track.source}:{track.track_id}"
        now = time()
        ttl = getattr(self, "_URL_CACHE_TTL_SEC", 30 * 60)
        max_size = getattr(self, "_URL_CACHE_MAX", 64)

        if not isinstance(self._cache, OrderedDict):
            self._cache = OrderedDict(self._cache)

        cached = self._cache.get(track_key)
        if cached is not None and (now - cached[1] < ttl):
            self._cache.move_to_end(track_key)
            return cached[0]

        expired = [k for k, (_, ts) in self._cache.items() if now - ts >= ttl]
        for key in expired:
            self._cache.pop(key, None)

        url = await func(self, track, *args, **kwargs)

        if url is not None:
            self._cache[track_key] = (url, now)
            self._cache.move_to_end(track_key)
            while len(self._cache) > max_size:
                self._cache.popitem(last=False)

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

    @staticmethod
    def _pick_best_download_info(infos: list[Any]) -> Any | None:
        """Полный трек (не preview), предпочтительно mp3 с макс. bitrate.

        ``download_info[0]`` часто preview (~30с) — из‑за этого обрыв на 27–30 сек.
        """
        if not infos:
            return None
        full = [item for item in infos if not bool(getattr(item, "preview", False))]
        candidates = full or list(infos)

        def score(item: Any) -> tuple[int, int, int]:
            preview = 1 if bool(getattr(item, "preview", False)) else 0
            codec = str(getattr(item, "codec", "") or "").lower()
            # mp3 надёжнее для Qt/FFmpeg, чем aac/he-aac по http
            codec_rank = 2 if codec == "mp3" else (1 if codec in ("aac", "mp4") else 0)
            bitrate = int(getattr(item, "bitrate_in_kbps", 0) or 0)
            return (-preview, codec_rank, bitrate)

        return max(candidates, key=score)

    def _sync_get_stream_url(self, track: Track) -> str | None:
        token = self._yandex_token()
        if not token:
            return None
        try:
            from yandex_music import Client

            track_id = int(track.track_id)
            client = Client(token)
            track_info = client.tracks(track_id)
            if not track_info:
                return None
            download_info = track_info[0].get_download_info()
            chosen = self._pick_best_download_info(list(download_info or []))
            if chosen is None:
                return None
            if bool(getattr(chosen, "preview", False)):
                logger.warning(
                    "Yandex отдал только preview (~30с) для «%s» — "
                    "нужен Plus / валидный токен. codec=%s bitrate=%s",
                    track.title,
                    getattr(chosen, "codec", "?"),
                    getattr(chosen, "bitrate_in_kbps", "?"),
                )
            else:
                logger.debug(
                    "Yandex stream «%s»: codec=%s bitrate=%s",
                    track.title,
                    getattr(chosen, "codec", "?"),
                    getattr(chosen, "bitrate_in_kbps", "?"),
                )
            return chosen.get_direct_link()
        except Exception:
            logger.exception("Не удалось получить URL потока Яндекс.Музыки: %s", track)
            return None


class AsyncYoutubeStreamer(AsyncStreamerInterface):
    def __init__(self, executor: ThreadPoolExecutor) -> None:
        self._common = {
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
            "quiet": True,
            "noplaylist": True,
            "extract_flat": False,
            "no_warnings": True,
            "nocheckcertificate": True,
            "postprocessors": [],
            "skip_download": True,
            "ignore_no_formats_error": True,
        }
        self._executor = executor

    def _attempt_opts(self, *, video: bool = False) -> list[dict]:
        """Несколько стратегий: cookies сейчас часто ломают android-клиент,
        а web без JS-runtime не отдаёт аудио (только storyboard).
        """
        from quantis.config.credentials import youtube_yt_dlp_cookiefile

        cookiefile = youtube_yt_dlp_cookiefile()
        fmt = (
            (
                "best[vcodec!=none][acodec!=none][height<=720]/"
                "best[height<=720]/best"
            )
            if video
            else "bestaudio/best/bestvideo+bestaudio/best"
        )

        attempts: list[dict] = []

        # 1) android без cookies — часто даёт progressive URL без JS-solver
        attempts.append(
            {
                **self._common,
                "format": fmt if not video else "18/best[height<=720]/best",
                "extractor_args": {"youtube": {"player_client": ["android"]}},
            }
        )
        # 2) дефолтный клиент без cookies — обычно есть m4a/opus
        attempts.append({**self._common, "format": fmt})

        # 3) с cookies (возраст/приват), без android/ios (они cookies не поддерживают)
        if cookiefile:
            attempts.append(
                {
                    **self._common,
                    "format": fmt,
                    "cookiefile": cookiefile,
                    "extractor_args": {"youtube": {"player_client": ["web", "mweb"]}},
                }
            )
            attempts.append(
                {
                    **self._common,
                    "format": "best/worst",
                    "cookiefile": cookiefile,
                }
            )

        return attempts

    @staticmethod
    def _is_playable_format(fmt: dict) -> bool:
        if not fmt.get("url"):
            return False
        protocol = str(fmt.get("protocol") or "")
        if protocol.startswith("mhtml") or protocol == "mhtml":
            return False
        ext = str(fmt.get("ext") or "").lower()
        if ext in ("mhtml", "jpg", "png", "webp"):
            return False
        # storyboard format ids
        fid = str(fmt.get("format_id") or "")
        if fid.startswith("sb"):
            return False
        return True

    @classmethod
    def _pick_stream_url(
        cls, info: dict[str, Any] | None, *, prefer_video: bool = False
    ) -> str | None:
        if not info:
            return None

        formats = [f for f in (info.get("formats") or []) if cls._is_playable_format(f)]
        top_url = info.get("url")
        if top_url and cls._is_playable_format(
            {
                "url": top_url,
                "protocol": info.get("protocol"),
                "ext": info.get("ext"),
                "format_id": info.get("format_id"),
                "vcodec": info.get("vcodec"),
                "acodec": info.get("acodec"),
            }
        ):
            # Если это уже выбранный bestaudio/best — ок
            if not prefer_video:
                vcodec = str(info.get("vcodec") or "none")
                acodec = str(info.get("acodec") or "none")
                if acodec not in ("", "none") or vcodec not in ("", "none"):
                    return str(top_url)

        if not formats:
            # иногда url есть только на верхнем уровне
            return str(top_url) if top_url else None

        def score(fmt: dict) -> tuple:
            vcodec = str(fmt.get("vcodec") or "none")
            acodec = str(fmt.get("acodec") or "none")
            has_audio = acodec not in ("", "none")
            has_video = vcodec not in ("", "none")
            audio_only = has_audio and not has_video
            progressive = has_audio and has_video
            ext = str(fmt.get("ext") or "").lower()
            abr = int(fmt.get("abr") or fmt.get("tbr") or 0)
            height = int(fmt.get("height") or 0)
            if prefer_video:
                return (
                    1 if progressive else 0,
                    1 if has_video else 0,
                    -abs(height - 720) if height else -9999,
                    abr,
                )
            return (
                1 if audio_only else (1 if progressive else 0),
                2 if ext in ("m4a", "mp4") else (1 if ext in ("webm", "opus") else 0),
                abr,
            )

        best = max(formats, key=score)
        return str(best.get("url") or "") or None

    async def get_stream_url(self, track: Track) -> str | None:
        return await get_running_loop().run_in_executor(
            self._executor, self.sync_stream, track.track_id
        )

    async def get_video_url(self, video_id: str) -> str | None:
        return await get_running_loop().run_in_executor(
            self._executor, self.sync_video_stream, video_id
        )

    def sync_stream(self, track_id: str) -> str | None:
        url = f"https://www.youtube.com/watch?v={track_id}"
        last_exc: BaseException | None = None
        for opts in self._attempt_opts(video=False):
            try:
                with YoutubeDL(opts) as yt:
                    info = yt.extract_info(url, download=False)
                picked = self._pick_stream_url(info, prefer_video=False)
                if picked:
                    logger.info(
                        "YouTube stream %s via format=%s clients=%s",
                        track_id,
                        opts.get("format"),
                        (opts.get("extractor_args") or {})
                        .get("youtube", {})
                        .get("player_client"),
                    )
                    return picked
            except Exception as exc:
                last_exc = exc
                logger.debug(
                    "YouTube stream attempt failed (%s): %s",
                    opts.get("format"),
                    track_id,
                    exc_info=True,
                )
        if last_exc is not None:
            logger.error(
                "Не удалось получить URL потока YouTube: %s",
                track_id,
                exc_info=last_exc,
            )
        else:
            logger.warning("YouTube: нет playable formats для %s", track_id)
        return None

    def sync_video_stream(self, track_id: str) -> str | None:
        url = f"https://www.youtube.com/watch?v={track_id}"
        for opts in self._attempt_opts(video=True):
            try:
                with YoutubeDL(opts) as yt:
                    info = yt.extract_info(url, download=False)
                picked = self._pick_stream_url(info, prefer_video=True)
                if picked:
                    return picked
            except Exception:
                logger.debug(
                    "YouTube video attempt failed: %s", track_id, exc_info=True
                )
        logger.error("Не удалось получить URL видео YouTube: %s", track_id)
        return None


class AsyncStreamer(AsyncStreamerInterface):
    """Фасад над Yandex и YouTube стримерами с кэшированием URL через декоратор."""

    _URL_CACHE_TTL_SEC = 50  # Yandex direct link живёт ~1 мин
    _URL_CACHE_MAX = 64

    def __init__(self, executor: ThreadPoolExecutor | None = None) -> None:
        from collections import OrderedDict

        from quantis.services.yandex_progressive_buffer import YandexProgressiveBuffer

        self._owns_executor = executor is None
        self._executor = executor or ThreadPoolExecutor(
            max_workers=4, thread_name_prefix="StreamerPool"
        )
        self._yandex = AsyncYandexStreamer(self._executor)
        self._youtube = AsyncYoutubeStreamer(self._executor)
        self._yandex_buffer = YandexProgressiveBuffer(self._yandex)
        self._buffer_loop: Any = None
        self._cache: OrderedDict[str, tuple[str, float]] = OrderedDict()

    @cached_stream_url
    async def get_stream_url(self, track: Track) -> str | None:
        """Получает прямой URL. Декоратор @cached_stream_url сам проверит и заполнит кэш."""
        source_type = str(track.source).lower()

        if source_type == TrackSource.YOUTUBE:
            return await self._youtube.get_stream_url(track)
        if source_type == TrackSource.YANDEX:
            return await self._yandex.get_stream_url(track)

        raise ValueError(f"Неизвестный источник платформы у трека: {track.source!r}")

    async def open_playback(self, track: Track) -> str | None:
        """Источник для плеера: Yandex — прогрессивный temp, остальное — URL."""
        self._buffer_loop = get_running_loop()
        source_type = str(track.source).lower()
        if source_type == TrackSource.YANDEX:
            path = await self._yandex_buffer.open(track)
            if path:
                self._yandex_buffer.cleanup_old_files(keep=Path(path))
            return path
        return await self.get_stream_url(track)

    async def get_video_url(self, track: Track, finder: object | None = None) -> str | None:
        """Прямой URL видео для динамических обоев (стрим, без сохранения на диск)."""
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

    def shutdown(self) -> None:
        if self._buffer_loop is not None:
            from concurrent.futures import TimeoutError as FuturesTimeoutError

            future = __import__("asyncio").run_coroutine_threadsafe(
                self._yandex_buffer.close(),
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
