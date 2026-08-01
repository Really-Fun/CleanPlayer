"""Сохранение истории прослушивания по событиям плеера."""

from __future__ import annotations

from PySide6.QtCore import QObject, QTimer

from quantis.core.async_bridge import AsyncBridge
from quantis.models import Track
from quantis.player import Player
from quantis.plugins.event_bus import EventBus
from quantis.services import TrackHistoryService


class PlaybackHistoryWatcher(QObject):
    """Пишет прогресс и недавние треки в БД при воспроизведении."""

    def __init__(
        self,
        player: Player,
        history: TrackHistoryService,
        event_bus: EventBus,
        bridge: AsyncBridge,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._player = player
        self._history = history
        self._bridge = bridge
        self._event_bus = event_bus
        self._current: Track | None = None

        self._eco = False
        self._timer = QTimer(self)
        self._timer.setInterval(5000)
        self._timer.timeout.connect(self._on_tick)

        event_bus.track_changed.connect(self._on_track_changed)
        player.on_track_finished(self._on_finished)
        player.on_playback_paused(self._on_pause)

    def set_eco(self, enabled: bool) -> None:
        self._eco = enabled
        self._timer.setInterval(20_000 if enabled else 5000)

    def _on_track_changed(self, track: Track) -> None:
        previous = self._current
        if previous is not None and previous is not track:
            self._save(previous, force=True)
        self._current = track
        self._timer.start()
        self._save(track, force=True)

    def _on_tick(self) -> None:
        if self._current is not None:
            self._save(self._current)

    def _on_pause(self) -> None:
        if self._current is not None:
            self._save(self._current, force=True)

    def _on_finished(self) -> None:
        track = self._current
        if track is None:
            return
        position_ms = self._player.time
        duration_ms = self._player.duration

        async def job() -> None:
            await self._history.mark_track_finished(track, position_ms, duration_ms)
            self._bridge.invoke_main(self._event_bus.history_updated.emit)

        self._bridge.schedule(job())

    def _save(self, track: Track, *, force: bool = False) -> None:
        position_ms = self._player.time
        duration_ms = self._player.duration

        async def job() -> None:
            await self._history.save_progress(
                track,
                position_ms,
                duration_ms,
                force=force,
            )
            if force:
                self._bridge.invoke_main(self._event_bus.history_updated.emit)

        self._bridge.schedule(job())
