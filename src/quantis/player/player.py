"""Контроллер воспроизведения: play / pause / volume / seek."""

from __future__ import annotations

import logging
from time import monotonic
from typing import Callable

from quantis.models import Track
from quantis.player.base import MediaEngine
from quantis.player.factory import create_media_engine

logger = logging.getLogger(__name__)


class Player:
    """Плеер. Работает со строками (локальные файлы / URL потока)."""

    def __init__(self, engine: MediaEngine | None = None) -> None:
        self._engine: MediaEngine = engine or create_media_engine()

        self.current_source: str | None = None
        self.current_track: Track | None = None
        self.on_pause: bool = False
        self._paused_at_ms: int = 0
        self._paused_at_mono: float = 0.0
        self._playback_active: bool = False
        self._loading_source: bool = False
        self._was_playing: bool = False

        self._source_changed_callbacks: list[Callable[[str], None]] = []
        self._playback_paused_callbacks: list[Callable[[], None]] = []
        self._playback_resumed_callbacks: list[Callable[[], None]] = []
        self._track_finished_callbacks: list[Callable[[], None]] = []
        self._next_callbacks: list[Callable[[], None]] = []
        self._previous_callbacks: list[Callable[[], None]] = []
        self._stream_error_callbacks: list[Callable[[str], None]] = []

        self._engine.on_playing(self._on_engine_playing)
        self._engine.on_paused(self._on_engine_paused)
        self._engine.on_stopped(self._on_engine_stopped)
        self._engine.on_ended(self._on_engine_ended)
        self._stream_retry_used = False
        self._engine.on_error(self._on_engine_error)

    def on_source_changed(self, callback: Callable[[str], None]) -> None:
        self._source_changed_callbacks.append(callback)

    def on_playback_paused(self, callback: Callable[[], None]) -> None:
        self._playback_paused_callbacks.append(callback)

    def on_playback_resumed(self, callback: Callable[[], None]) -> None:
        self._playback_resumed_callbacks.append(callback)

    def on_track_finished(self, callback: Callable[[], None]) -> None:
        self._track_finished_callbacks.append(callback)

    def on_next_requested(self, callback: Callable[[], None]) -> None:
        self._next_callbacks.append(callback)

    def on_previous_requested(self, callback: Callable[[], None]) -> None:
        self._previous_callbacks.append(callback)

    def on_stream_error(self, callback: Callable[[str], None]) -> None:
        self._stream_error_callbacks.append(callback)

    def play(self, source: str, *, start_ms: int = 0) -> None:
        self._stream_retry_used = False
        self._loading_source = True
        self._playback_active = False
        self._was_playing = False
        self.on_pause = False
        self._paused_at_ms = 0
        self._paused_at_mono = 0.0
        self.current_source = source
        self._engine.play_media(source)
        if start_ms > 0:
            self._request_seek(start_ms)
        for callback in self._source_changed_callbacks:
            callback(source)

    def pause(self) -> None:
        if not self.current_source:
            return
        position = max(0, self.time)
        if position > 0:
            self._paused_at_ms = position
        self._paused_at_mono = monotonic()
        self.on_pause = True
        self._engine.pause_media()
        for callback in self._playback_paused_callbacks:
            callback()

    def resume(self) -> None:
        if not self.current_source:
            return
        resume_at = max(0, self._paused_at_ms, self.time)
        if self._http_source_likely_stale(resume_at):
            logger.info(
                "HTTP-поток после паузы — обновление источника @ %dms",
                resume_at,
            )
            for callback in self._stream_error_callbacks:
                callback("resume-after-pause")
            return
        self.on_pause = False
        self._engine.resume_media()
        if resume_at > 1000:
            self._request_seek(resume_at)
        self._paused_at_ms = 0
        self._paused_at_mono = 0.0
        for callback in self._playback_resumed_callbacks:
            callback()

    def stop(self) -> None:
        self.on_pause = True
        self._paused_at_ms = 0
        self._paused_at_mono = 0.0
        self._playback_active = False
        self._was_playing = False
        self._engine.stop_media()
        for callback in self._playback_paused_callbacks:
            callback()

    def toggle_pause(self) -> None:
        if not self.current_source:
            return
        if self.is_playing():
            self.pause()
        else:
            self.resume()

    def next(self) -> None:
        for callback in self._next_callbacks:
            callback()

    def previous(self) -> None:
        for callback in self._previous_callbacks:
            callback()

    def is_playing(self) -> bool:
        return self._engine.is_playing()

    def _on_engine_playing(self) -> None:
        previous = self._was_playing
        self._loading_source = False
        self.on_pause = False
        self._playback_active = True
        self._was_playing = True
        if not previous:
            for callback in self._playback_resumed_callbacks:
                callback()

    def _on_engine_paused(self) -> None:
        was_playing = self._was_playing
        self.on_pause = True
        self._was_playing = False
        if self._playback_active and not self._loading_source and was_playing:
            for callback in self._playback_paused_callbacks:
                callback()

    def _on_engine_stopped(self) -> None:
        self.on_pause = True
        self._loading_source = False
        self._was_playing = False

    def _on_engine_ended(self) -> None:
        if not self._playback_active or not self.current_source:
            return
        duration = self.duration
        position = self.time
        is_http = str(self.current_source).startswith(("http://", "https://"))
        # ~30с preview на прямом HTTP. Локальный growing MP3 на этом окне
        # восстанавливаем, а не считаем трек законченным.
        truncated = (
            is_http
            and duration > 60_000
            and 15_000 <= position <= 45_000
        )
        if duration > 1000 and position < duration - 1000 and not truncated:
            logger.warning(
                "Поток оборвался рано (%sms из %sms) — восстановление",
                position,
                duration,
            )
            for callback in self._stream_error_callbacks:
                callback("ended-early")
            return
        if truncated:
            logger.warning(
                "Поток оборвался рано (%sms из %sms) — preview или обрыв CDN",
                position,
                duration,
            )
        self._playback_active = False
        self._was_playing = False
        for callback in self._track_finished_callbacks:
            callback()

    def _on_engine_error(self, message: str) -> None:
        logger.warning(
            "MediaEngine error=%s source=%s",
            message,
            self.current_source,
        )
        for callback in self._stream_error_callbacks:
            callback(message)

    def _request_seek(self, ms: int) -> None:
        engine = self._engine
        request = getattr(engine, "request_seek", None)
        if callable(request):
            request(ms)
        else:
            engine.set_position_ms(ms)

    @property
    def paused_at_ms(self) -> int:
        return max(0, self._paused_at_ms)

    def paused_for_sec(self) -> float:
        if self._paused_at_mono <= 0:
            return 0.0
        return max(0.0, monotonic() - self._paused_at_mono)

    def _http_source_likely_stale(self, resume_at: int) -> bool:
        source = self.current_source or ""
        if not str(source).startswith(("http://", "https://")):
            return False
        if resume_at <= 1000:
            return False
        if self.paused_for_sec() >= 15.0:
            return True
        return self.time < 1000

    @property
    def volume(self) -> int:
        return self._engine.get_volume()

    @volume.setter
    def volume(self, value: int) -> None:
        self._engine.set_volume(value)

    @property
    def time(self) -> int:
        return self._engine.get_position_ms()

    @time.setter
    def time(self, time_in_ms: int) -> None:
        self._engine.set_position_ms(time_in_ms)

    @property
    def duration(self) -> int:
        engine_ms = max(0, int(self._engine.get_duration_ms()))
        catalog_ms = 0
        track = self.current_track
        if track is not None:
            catalog_ms = max(0, int(getattr(track, "duration_ms", 0) or 0))
        return max(engine_ms, catalog_ms)
