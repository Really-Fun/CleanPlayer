from __future__ import annotations

from quantis.core.async_bridge import AsyncBridge
from quantis.models import Track
from quantis.player import Player
from quantis.plugins.event_bus import EventBus
from quantis.providers import PlaylistManager
from quantis.services import MusicService, TrackHistoryService

import logging

logger = logging.getLogger(__name__)
class PlaybackController:
    """Медиатор логики воспроизведения."""

    def __init__(
        self,
        player: Player,
        playlist_manager: PlaylistManager,
        music_service: MusicService,
        event_bus: EventBus | None = None,
        history: TrackHistoryService | None = None,
        async_bridge: AsyncBridge | None = None,
    ) -> None:
        self.player = player
        self.playlist_manager = playlist_manager
        self.music = music_service
        self._event_bus = event_bus
        self._history = history
        self._bridge = async_bridge
        self._current_track: Track | None = None

    @property
    def current_track(self) -> Track | None:
        return self._current_track

    async def play_track(self, track: Track | None) -> None:
        if not track:
            return

        if track.downloaded:
            extension = getattr(track, "extension", None)
            source = (
                self.music.provider.get_track_path(track, extension)
                if extension
                else self.music.provider.get_track_path(track)
            )
        else:
            source = await self.music.streamer.get_stream_url(track)

        if not source:
            message = f"Не удалось получить источник для воспроизведения: {track.title}"
            logger.warning(message)
            if self._event_bus is not None:

                def notify() -> None:
                    self._event_bus.error_occurred.emit(message)

                if self._bridge is not None:
                    self._bridge.invoke_main(notify)
                else:
                    notify()
            return

        resume_ms = 0
        if self._history is not None:
            resume_ms = await self._history.get_resume_position(track)

        def start_playback() -> None:
            self._current_track = track
            self.player.current_track = track
            self.player.play(source)
            if resume_ms > 0:
                self.player.time = resume_ms
            if self._event_bus is not None:
                self._event_bus.track_changed.emit(track)

        if self._bridge is not None:
            self._bridge.invoke_main(start_playback)
        else:
            start_playback()

    async def play_next(self) -> None:
        playlist = self.playlist_manager.current_playlist
        if playlist is None or len(playlist) == 0:
            return
        track = playlist.move_next_track()
        await self.play_track(track)

    async def play_previous(self) -> None:
        playlist = self.playlist_manager.current_playlist
        if playlist is None or len(playlist) == 0:
            return
        track = playlist.move_previous_track()
        await self.play_track(track)

    def toggle_pause(self) -> None:
        self.player.toggle_pause()

    async def generate_radio(self, track: Track | None):
        if track:
            return await self.music.recommendation.generate_radio_from_track(track)
