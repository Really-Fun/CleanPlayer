"""Контроллер воспроизведения.

Управляет play / pause / volume / track loading.
Чистый Python (Pure Python) — ноль зависимостей от других модулей проекта.
"""

from __future__ import annotations
import asyncio
from typing import Callable

from vlc import EventType
from quantis.player.engine import VLCEngine


class Player:
    """Плеер. Только воспроизведение. Работает напрямую со строками (файлы/URL)."""

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._engine = VLCEngine()

        self.current_source: str | None = None
        self.on_pause: bool = False

        self._source_changed_callbacks: list[Callable[[str], None]] = []
        self._playback_paused_callbacks: list[Callable[[], None]] = []
        self._playback_resumed_callbacks: list[Callable[[], None]] = []
        self._track_finished_callbacks: list[Callable[[], None]] = []

        self.events = self._engine.playback_player.event_manager()
        self.events.event_attach(EventType.MediaPlayerEndReached, self._on_vlc_end)

    def on_source_changed(self, callback: Callable[[str], None]) -> None:
        self._source_changed_callbacks.append(callback)

    def on_playback_paused(self, callback: Callable[[], None]) -> None:
        self._playback_paused_callbacks.append(callback)

    def on_playback_resumed(self, callback: Callable[[], None]) -> None:
        self._playback_resumed_callbacks.append(callback)

    def on_track_finished(self, callback: Callable[[], None]) -> None:
        self._track_finished_callbacks.append(callback)

    def play(self, source: str) -> None:
        """Запускает воспроизведение по прямой ссылке на файл или поток URL."""
        self.on_pause = False
        self.current_source = source

        self._engine.play_media(source)
        
        for cb in self._source_changed_callbacks:
            cb(source)

    def pause(self) -> None:
        self.on_pause = True
        self._engine.pause_media()
        for cb in self._playback_paused_callbacks:
            cb()

    def resume(self) -> None:
        self.on_pause = False
        self._engine.resume_media()
        for cb in self._playback_resumed_callbacks:
            cb()

    def is_playing(self) -> bool:
        return self._engine.playback_player.is_playing()

    def _on_vlc_end(self, _event=None) -> None:     
        self._loop.call_soon_threadsafe(self._trigger_finished_callbacks)

    def _trigger_finished_callbacks(self) -> None:
        for cb in self._track_finished_callbacks:
            cb()

    @property
    def volume(self) -> int:
        return self._engine.playback_player.audio_get_volume()

    @volume.setter
    def volume(self, value: int) -> None:
        self._engine.playback_player.audio_set_volume(value)

    @property
    def time(self) -> int:
        return self._engine.playback_player.get_time()

    @time.setter
    def time(self, time_in_ms: int) -> None:
        self._engine.playback_player.set_time(time_in_ms)
        self._engine.analysis_player.set_time(time_in_ms)

    @property
    def duration(self) -> int:
        return self._engine.playback_player.get_length()