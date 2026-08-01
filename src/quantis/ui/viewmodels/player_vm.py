from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal

from quantis.controllers.playback_controller import PlaybackController
from quantis.models import Track
from quantis.player import Player
from quantis.plugins.event_bus import EventBus
from quantis.ui.viewmodels.base_viewmodel import BaseViewModel


class PlayerViewModel(BaseViewModel):
    track_changed = Signal(object)
    is_playing_changed = Signal(bool)
    position_changed = Signal(int)
    duration_changed = Signal(int)
    volume_changed = Signal(int)

    def __init__(
        self,
        playback: PlaybackController,
        player: Player,
        event_bus: EventBus,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._playback = playback
        self._player = player
        self._event_bus = event_bus
        self._eco = False
        self._last_duration = -1
        self._tick = QTimer(self)
        self._tick.setInterval(250)
        self._tick.timeout.connect(self._update_timeline)

        event_bus.track_changed.connect(self._on_track_changed)
        event_bus.playback_paused.connect(self._on_paused)
        event_bus.playback_resumed.connect(self._on_resumed)
        event_bus.track_finished.connect(self._on_track_finished)

    def set_eco(self, enabled: bool) -> None:
        self._eco = enabled
        self._tick.setInterval(2000 if enabled else 250)

    def start_updates(self) -> None:
        if not self._tick.isActive():
            self._tick.start()

    def stop_updates(self) -> None:
        self._tick.stop()

    @property
    def current_track(self) -> Track | None:
        return self._playback.current_track

    def toggle_pause(self) -> None:
        self._playback.toggle_pause()

    def play_next(self) -> None:
        self._event_bus.next_requested.emit()

    def play_previous(self) -> None:
        self._event_bus.previous_requested.emit()

    def set_volume(self, value: int) -> None:
        self._player.volume = value
        self.volume_changed.emit(value)

    def seek(self, position_ms: int) -> None:
        self._player.time = position_ms
        self.position_changed.emit(position_ms)

    def sync_from_player(self) -> None:
        """Синхронизирует UI с текущим состоянием Qt-плеера."""
        if self._playback.current_track is not None:
            self.track_changed.emit(self._playback.current_track)
        self.is_playing_changed.emit(self._player.is_playing())
        duration = max(0, self._player.duration)
        if duration > 0:
            self.duration_changed.emit(duration)
        self.position_changed.emit(max(0, self._player.time))
        if self._player.current_source:
            self.start_updates()

    def _update_timeline(self) -> None:
        if not self._player.current_source:
            return
        position = max(0, self._player.time)
        duration = max(0, self._player.duration)
        self.position_changed.emit(position)
        if duration > 0 and duration != self._last_duration:
            self._last_duration = duration
            self.duration_changed.emit(duration)

    def _on_track_changed(self, track: Track) -> None:
        self.track_changed.emit(track)
        self.start_updates()

    def _on_paused(self) -> None:
        self.is_playing_changed.emit(False)

    def _on_resumed(self) -> None:
        self.is_playing_changed.emit(True)
        self.start_updates()

    def _on_track_finished(self) -> None:
        self.is_playing_changed.emit(False)
        self.stop_updates()
