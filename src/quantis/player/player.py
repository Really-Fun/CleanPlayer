"""Контроллер воспроизведения: play / pause / volume / seek."""

from __future__ import annotations

from typing import Callable

from PySide6.QtMultimedia import QMediaPlayer

from quantis.models import Track
from quantis.player.engine import QtMediaEngine


class Player:
    """Плеер. Работает со строками (локальные файлы / URL потока)."""

    def __init__(
        self,
        engine: QtMediaEngine | None = None,
    ) -> None:
        self._engine = engine or QtMediaEngine()

        self.current_source: str | None = None
        self.current_track: Track | None = None
        self.on_pause: bool = False
        self._playback_active: bool = False
        self._loading_source: bool = False
        self._last_playback_state: QMediaPlayer.PlaybackState | None = None

        self._source_changed_callbacks: list[Callable[[str], None]] = []
        self._playback_paused_callbacks: list[Callable[[], None]] = []
        self._playback_resumed_callbacks: list[Callable[[], None]] = []
        self._track_finished_callbacks: list[Callable[[], None]] = []
        self._next_callbacks: list[Callable[[], None]] = []
        self._previous_callbacks: list[Callable[[], None]] = []

        media_player = self._engine.media_player
        media_player.mediaStatusChanged.connect(self._on_media_status)
        media_player.playbackStateChanged.connect(self._on_playback_state_changed)

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
        return (
            self._engine.media_player.playbackState()
            == QMediaPlayer.PlaybackState.PlayingState
        )

    def _on_media_status(self, status: QMediaPlayer.MediaStatus) -> None:
        if status != QMediaPlayer.MediaStatus.EndOfMedia:
            return
        if not self._playback_active or not self.current_source:
            return

        media_player = self._engine.media_player
        duration = media_player.duration()
        position = media_player.position()
        if duration > 1000 and position < duration - 1000:
            return

        self._playback_active = False
        self._trigger_finished_callbacks()

    def _on_playback_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        previous = self._last_playback_state
        self._last_playback_state = state

        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._loading_source = False
            self.on_pause = False
            self._playback_active = True
            if previous != QMediaPlayer.PlaybackState.PlayingState:
                for callback in self._playback_resumed_callbacks:
                    callback()
            return

        if state == QMediaPlayer.PlaybackState.PausedState:
            self.on_pause = True
            if (
                self._playback_active
                and not self._loading_source
                and previous == QMediaPlayer.PlaybackState.PlayingState
            ):
                for callback in self._playback_paused_callbacks:
                    callback()
            return

        if state == QMediaPlayer.PlaybackState.StoppedState:
            self.on_pause = True
            self._loading_source = False

    def _trigger_finished_callbacks(self) -> None:
        for callback in self._track_finished_callbacks:
            callback()

    @property
    def volume(self) -> int:
        return int(self._engine.audio_output.volume() * 100)

    @volume.setter
    def volume(self, value: int) -> None:
        self._engine.audio_output.setVolume(max(0, min(100, value)) / 100.0)

    @property
    def time(self) -> int:
        return self._engine.media_player.position()

    @time.setter
    def time(self, time_in_ms: int) -> None:
        self._engine.media_player.setPosition(time_in_ms)

    @property
    def duration(self) -> int:
        return self._engine.media_player.duration()
