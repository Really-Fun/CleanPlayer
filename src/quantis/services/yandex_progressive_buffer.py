"""Прогрессивный буфер потока: фоновая запись в temp, воспроизведение сразу.

Для Yandex и YouTube — CDN-URL могут истекать или быть HLS/DASH; range-загрузка
в локальный файл стабильнее прямого HTTP в VLC/Qt.
"""

from __future__ import annotations

import asyncio
import logging
import re
import tempfile
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientConnectionError, ClientPayloadError

from quantis.models import Track, TrackSource

logger = logging.getLogger(__name__)

StreamUrlFetcher = Callable[[Track], Awaitable[str | None]]

_UPSTREAM_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Encoding": "identity",
}
_URL_TTL_SEC = 45.0
_SEGMENT_BYTES = 1024 * 1024
_MAX_SEGMENT_RETRIES = 5
_MIN_START_BYTES = 192 * 1024
_AHEAD_BYTES = 2 * 1024 * 1024
_ECO_AHEAD_BYTES = 4 * 1024 * 1024
_START_TIMEOUT_SEC = 45.0
_BYTES_PER_SEC_EST = 40_000
_FLUSH_EVERY_BYTES = 2 * 1024 * 1024


def _total_from_content_range(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"/(\d+)\s*$", value)
    return int(match.group(1)) if match else None


def _buffer_path(track: Track, root: Path) -> Path:
    source = str(track.source).lower()
    ext = "m4a" if source == TrackSource.YOUTUBE else "mp3"
    return root / f"{source}_{track.track_id}.{ext}"


class ProgressiveStreamBuffer:
    """Один активный temp-файл; сегментная загрузка с CDN."""

    def __init__(self, url_fetcher: StreamUrlFetcher) -> None:
        self._url_fetcher = url_fetcher
        self._dir = Path(tempfile.gettempdir()) / "quantis_stream"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._client: ClientSession | None = None
        self._upstream: dict[str, tuple[str, float]] = {}
        self._task: asyncio.Task[None] | None = None
        self._path: Path | None = None
        self._ready = asyncio.Event()
        self._lock = asyncio.Lock()
        self._eco = False

    def set_eco(self, enabled: bool) -> None:
        self._eco = enabled

    def invalidate_track(self, track: Track) -> None:
        self._upstream.pop(str(track.track_id), None)

    async def _ensure_client(self) -> ClientSession:
        if self._client is None:
            self._client = ClientSession(headers=_UPSTREAM_HEADERS)
        return self._client

    async def close(self) -> None:
        await self.cancel()
        if self._client is not None:
            await self._client.close()
            self._client = None
        self._upstream.clear()

    async def cancel(self) -> None:
        task = self._task
        self._task = None
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        path = self._path
        self._path = None
        self._ready = asyncio.Event()
        if path is not None:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                logger.debug("Не удалось удалить temp %s", path, exc_info=True)

    async def open(self, track: Track) -> str | None:
        """Старт фоновой загрузки; возвращает путь, когда буфер готов к play."""
        async with self._lock:
            await self.cancel()
            path = _buffer_path(track, self._dir)
            self._path = path
            self._upstream.pop(str(track.track_id), None)
            self._ready = asyncio.Event()
            self._task = asyncio.create_task(self._download(track, path))

        try:
            await asyncio.wait_for(self._ready.wait(), timeout=_START_TIMEOUT_SEC)
        except TimeoutError:
            logger.warning("Stream buffer: таймаут старта «%s»", track.title)
            await self.cancel()
            return None

        if self._task is not None and self._task.done():
            if self._task.exception() is not None:
                await self.cancel()
                return None

        return str(path)

    async def _upstream_url(self, track: Track, *, force: bool = False) -> str | None:
        key = str(track.track_id)
        now = time.monotonic()
        if not force:
            cached = self._upstream.get(key)
            if cached is not None and now - cached[1] < _URL_TTL_SEC:
                return cached[0]
        else:
            self._upstream.pop(key, None)

        url = await self._url_fetcher(track)
        if not url:
            return None
        self._upstream[key] = (url, now)
        return url

    def _invalidate(self, track_id: str) -> None:
        self._upstream.pop(track_id, None)

    async def _fetch_segment(
        self,
        client: ClientSession,
        track: Track,
        track_id: str,
        offset: int,
        seg_end: int,
    ) -> tuple[bytes, int | None]:
        for attempt in range(_MAX_SEGMENT_RETRIES):
            try:
                if attempt > 0:
                    self._invalidate(track_id)
                url = await self._upstream_url(track, force=attempt > 0)
                if not url:
                    raise RuntimeError("no upstream url")

                headers = {"Range": f"bytes={offset}-{seg_end}"}
                async with client.get(
                    url, headers=headers, allow_redirects=True
                ) as upstream:
                    if upstream.status in (403, 410):
                        self._invalidate(track_id)
                        continue
                    if upstream.status == 416:
                        return b"", None
                    if upstream.status >= 400:
                        text = await upstream.text()
                        raise RuntimeError(
                            f"upstream {upstream.status}: {text[:200]}"
                        )
                    total = _total_from_content_range(
                        upstream.headers.get("Content-Range")
                    )
                    if total is None and upstream.headers.get("Content-Length"):
                        cl = int(upstream.headers["Content-Length"])
                        total = offset + cl if upstream.status == 206 else cl
                    body = await upstream.read()
                    return body, total
            except (ClientPayloadError, ClientConnectionError) as exc:
                logger.debug(
                    "Stream buffer segment retry %s@%s: %s",
                    track_id,
                    offset,
                    exc,
                )
                self._invalidate(track_id)
                continue
        raise RuntimeError("upstream segment failed")

    async def _pace_after_segment(self, offset: int, segment_len: int) -> None:
        ahead_target = _ECO_AHEAD_BYTES if self._eco else _AHEAD_BYTES
        if offset < ahead_target:
            return
        factor = 1.8 if self._eco else 2.2
        delay = segment_len / (_BYTES_PER_SEC_EST * factor)
        if self._eco:
            delay = min(delay, 8.0)
        await asyncio.sleep(delay)

    async def _download(self, track: Track, path: Path) -> None:
        track_id = str(track.track_id)
        client = await self._ensure_client()
        offset = 0
        total_size: int | None = None
        since_flush = 0

        try:
            with path.open("wb") as handle:
                while total_size is None or offset < total_size:
                    seg_end = offset + _SEGMENT_BYTES - 1
                    body, segment_total = await self._fetch_segment(
                        client, track, track_id, offset, seg_end
                    )
                    if segment_total is not None:
                        total_size = segment_total
                    if not body:
                        break

                    if handle.tell() != offset:
                        raise RuntimeError(
                            f"temp write mismatch: file={handle.tell()} offset={offset}"
                        )
                    handle.write(body)
                    since_flush += len(body)
                    done = total_size is not None and offset + len(body) >= total_size
                    if since_flush >= _FLUSH_EVERY_BYTES or done:
                        handle.flush()
                        since_flush = 0
                    offset += len(body)

                    if path.stat().st_size >= _MIN_START_BYTES:
                        self._ready.set()

                    if total_size is not None and offset >= total_size:
                        break

                    await self._pace_after_segment(offset, len(body))

                handle.flush()

            if offset > 0:
                self._ready.set()
            logger.debug(
                "Stream buffer готов «%s»: %s bytes → %s",
                track.title,
                offset,
                path.name,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Stream buffer: ошибка «%s»", track.title)
            self._ready.set()
            raise

    def cleanup_old_files(self, keep: Path | None = None) -> None:
        keep_resolved = keep.resolve() if keep is not None and keep.exists() else None
        for path in self._dir.glob("*_*.*"):
            try:
                if keep_resolved is not None and path.resolve() == keep_resolved:
                    continue
                path.unlink(missing_ok=True)
            except OSError:
                logger.debug("Не удалось удалить temp %s", path, exc_info=True)


# Обратная совместимость
YandexProgressiveBuffer = ProgressiveStreamBuffer
