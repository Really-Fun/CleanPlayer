"""Контроллер воспроизведения: play / pause / volume / seek."""

from __future__ import annotations

import logging
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
        self._playback_active: bool = False
        self._loading_source: bool = False
        self._was_playing: bool = False

        self._source_changed_callbacks: list[Callable[[str], None]] = []
        self._playback_paused_callbacks: list[Callable[[], None]] = []
        self._playback_resumed_callbacks: list[Callable[[], None]] = []
        self._track_finished_callbacks: list[Callable[[], None]] = []
        self._next_callbacks: list[Callable[[], None]] = []
        self._previous_callbacks: list[Callable[[], None]] = []

        self._engine.on_playing(self._on_engine_playing)
        self._engine.on_paused(self._on_engine_paused)
        self._engine.on_stopped(self._on_engine_stopped)
        self._engine.on_ended(self._on_engine_ended)
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

    def play(self, source: str) -> None:
        self._loading_source = True
        self._playback_active = False
        self._was_playing = False
        self.on_pause = False
        self.current_source = source
        self._engine.play_media(source)
        for callback in self._source_changed_callbacks:
            callback(source)

    def pause(self) -> None:
        if not self.current_source:
            return
        self.on_pause = True
        self._engine.pause_media()
        for callback in self._playback_paused_callbacks:
            callback()

    def resume(self) -> None:
        if not self.current_source:
            return
        self.on_pause = False
        self._engine.resume_media()
        for callback in self._playback_resumed_callbacks:
            callback()

    def stop(self) -> None:
        self.on_pause = True
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
        truncated = duration > 60_000 and 15_000 <= position <= 45_000
        if duration > 1000 and position < duration - 1000 and not truncated:
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
        return self._engine.get_duration_ms()
