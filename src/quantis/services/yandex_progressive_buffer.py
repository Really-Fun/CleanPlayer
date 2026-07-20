"""Прогрессивный буфер Яндекс.Музыки: фоновая запись в temp, play сразу.

HTTP-склейка сегментов ломает MP3 на границах кадров (invalid new backstep).
Файл растёт последовательно — Qt читает локальный путь как поток.
Не пишет в music/, удаляется при смене трека / выходе.
"""

from __future__ import annotations

import asyncio
import logging
import re
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING

from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientConnectionError, ClientPayloadError

from quantis.models import Track

if TYPE_CHECKING:
    from quantis.services.async_streamer import AsyncYandexStreamer

logger = logging.getLogger(__name__)

_UPSTREAM_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Encoding": "identity",
}
_URL_TTL_SEC = 40.0
_SEGMENT_BYTES = 512 * 1024
_MAX_SEGMENT_RETRIES = 5
_MIN_START_BYTES = 128 * 1024
_START_TIMEOUT_SEC = 45.0


def _total_from_content_range(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"/(\d+)\s*$", value)
    return int(match.group(1)) if match else None


class YandexProgressiveBuffer:
    """Один активный temp-файл; сегментная загрузка с CDN с обновлением signed URL."""

    def __init__(self, yandex: AsyncYandexStreamer) -> None:
        self._yandex = yandex
        self._dir = Path(tempfile.gettempdir()) / "quantis_stream"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._client: ClientSession | None = None
        self._upstream: dict[str, tuple[str, float]] = {}
        self._task: asyncio.Task[None] | None = None
        self._path: Path | None = None
        self._ready = asyncio.Event()
        self._lock = asyncio.Lock()

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
        """Старт фоновой загрузки; возвращает путь, когда буфер >= 128 KiB."""
        async with self._lock:
            await self.cancel()
            path = self._dir / f"yandex_{track.track_id}.mp3"
            self._path = path
            self._upstream.pop(str(track.track_id), None)
            self._ready = asyncio.Event()
            self._task = asyncio.create_task(self._download(track, path))

        try:
            await asyncio.wait_for(self._ready.wait(), timeout=_START_TIMEOUT_SEC)
        except asyncio.TimeoutError:
            logger.warning("Yandex buffer: таймаут старта «%s»", track.title)
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

        url = await self._yandex.get_stream_url(track)
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
                    "Yandex buffer segment retry %s@%s: %s",
                    track_id,
                    offset,
                    exc,
                )
                self._invalidate(track_id)
                continue
        raise RuntimeError("upstream segment failed")

    async def _download(self, track: Track, path: Path) -> None:
        track_id = str(track.track_id)
        client = await self._ensure_client()
        offset = 0
        total_size: int | None = None

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
                    handle.flush()
                    offset += len(body)

                    if path.stat().st_size >= _MIN_START_BYTES:
                        self._ready.set()

                    if total_size is not None and offset >= total_size:
                        break

                    self._invalidate(track_id)

            if offset > 0:
                self._ready.set()
            logger.debug(
                "Yandex buffer готов «%s»: %s bytes → %s",
                track.title,
                offset,
                path.name,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Yandex buffer: ошибка «%s»", track.title)
            self._ready.set()
            raise

    def cleanup_old_files(self, keep: Path | None = None) -> None:
        keep_resolved = keep.resolve() if keep is not None and keep.exists() else None
        for path in self._dir.glob("yandex_*.mp3"):
            try:
                if keep_resolved is not None and path.resolve() == keep_resolved:
                    continue
                path.unlink(missing_ok=True)
            except OSError:
                logger.debug("Не удалось удалить temp %s", path, exc_info=True)
