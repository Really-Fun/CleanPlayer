from __future__ import annotations

import logging
from pathlib import Path

from quantis.core.async_bridge import AsyncBridge
from quantis.models import Track
from quantis.models.playlist import WavePlaylist
from quantis.models.repeat_mode import RepeatMode
from quantis.player import Player
from quantis.plugins.event_bus import EventBus
from quantis.providers import PlaylistManager
from quantis.services import MusicService, TrackHistoryService
from quantis.ui.preferences import UiPreferences

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
        self._wave_skip_start_feedback = False
        self._stream_retry_pending = False
        self._stall_recoveries = 0
        self._stall_track_key: str | None = None
        self._repeat_mode = UiPreferences().repeat_mode

    @property
    def repeat_mode(self) -> RepeatMode:
        return self._repeat_mode

    def cycle_repeat_mode(self) -> RepeatMode:
        self._repeat_mode = self._repeat_mode.cycle()
        UiPreferences().set_repeat_mode(self._repeat_mode)
        return self._repeat_mode

    async def handle_track_finished(self) -> None:
        if self.repeat_mode is RepeatMode.TRACK:
            track = self._current_track
            if track is not None:
                await self.play_track(track)
            return
        await self.play_next()

    def handle_stream_error(self, message: str) -> None:
        """Повтор воспроизведения при ошибке медиадвижка."""
        paused_at = getattr(self.player, "paused_at_ms", 0) or 0
        position = max(0, self.player.time, int(paused_at))
        self.request_playback_recovery(position, reason=message)

    def request_playback_recovery(self, position_ms: int, *, reason: str = "stall") -> None:
        if self._stream_retry_pending or self._bridge is None:
            return
        self._bridge.schedule(self.recover_playback(position_ms, reason=reason))

    async def recover_playback(self, position_ms: int, *, reason: str = "stall") -> None:
        """Обновляет источник и продолжает с текущей позиции (signed URL / обрыв CDN)."""
        if self._stream_retry_pending:
            return
        track = self._current_track
        if track is None:
            return

        source = self.player.current_source
        if source and not str(source).startswith(("http://", "https://")):
            path = Path(str(source))
            if track.downloaded and path.is_file():
                return

        track_key = f"{track.source}:{track.track_id}"
        if self._stall_track_key != track_key:
            self._stall_track_key = track_key
            self._stall_recoveries = 0
        if reason == "resume-after-pause":
            self._stall_recoveries = 0
        if self._stall_recoveries >= 3:
            logger.warning(
                "Лимит восстановления потока для «%s» (%s)",
                track.title,
                reason,
            )
            return

        self._stream_retry_pending = True
        self._stall_recoveries += 1
        try:
            logger.info(
                "Восстановление потока «%s» @ %dms (%s)",
                track.title,
                position_ms,
                reason,
            )
            self.music.streamer.invalidate(track)
            new_source = await self.music.streamer.open_playback(track)
            if not new_source:
                return

            resume_at = position_ms

            def replay() -> None:
                if resume_at > 0:
                    self.player.play(new_source, start_ms=resume_at)
                else:
                    self.player.play(new_source)

            self._bridge.invoke_main(replay)  # type: ignore[union-attr]
        except Exception:
            logger.exception("Не удалось восстановить поток")
        finally:
            self._stream_retry_pending = False

    async def _prefetch_next_track(self, current: Track) -> None:
        playlist = self.playlist_manager.current_playlist
        if playlist is None or len(playlist) == 0:
            return
        tracks = playlist.tracks.values
        try:
            index = tracks.index(current)
        except ValueError:
            return
        if index + 1 >= len(tracks):
            return
        nxt = tracks[index + 1]
        await self.music.streamer.prefetch_stream(nxt)

    @property
    def current_track(self) -> Track | None:
        return self._current_track

    def _local_path_if_ready(self, track: Track) -> str | None:
        extension = getattr(track, "extension", None)
        path = (
            self.music.provider.get_track_path(track, extension)
            if extension
            else self.music.provider.get_track_path(track)
        )
        file_path = Path(path)
        if not file_path.is_file():
            return None
        try:
            if file_path.stat().st_size <= 0:
                return None
        except OSError:
            return None
        return path

    async def _resolve_source(self, track: Track) -> str | None:
        if track.downloaded:
            local = self._local_path_if_ready(track)
            if local:
                return local

        return await self.music.streamer.open_playback(track)

    async def play_track(self, track: Track | None) -> None:
        if not track:
            return

        source = await self._resolve_source(track)
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

        playlist = self.playlist_manager.current_playlist
        if (
            isinstance(playlist, WavePlaylist)
            and not self._wave_skip_start_feedback
        ):
            await self.music.wave.notify_track_started(track, playlist)

        def start_playback() -> None:
            self._current_track = track
            self._stall_track_key = None
            self._stall_recoveries = 0
            self.player.current_track = track
            start_ms = resume_ms if resume_ms > 0 else 0
            if start_ms > 0:
                self.player.play(source, start_ms=start_ms)
            else:
                self.player.play(source)
            if self._event_bus is not None:
                self._event_bus.track_changed.emit(track)

        if self._bridge is not None:
            self._bridge.invoke_main(start_playback)
        else:
            start_playback()

        if self._bridge is not None:
            self._bridge.schedule(self._prefetch_next_track(track))

    async def play_next(self) -> None:
        playlist = self.playlist_manager.current_playlist
        if playlist is None or len(playlist) == 0:
            return

        if isinstance(playlist, WavePlaylist) and playlist.source == "yandex":
            await self._play_wave_next(playlist)
            return

        track = playlist.move_next_track()
        await self.play_track(track)

    async def _play_wave_next(self, playlist: WavePlaylist) -> None:
        finished = self._current_track
        if finished is None:
            try:
                finished = playlist.get_current_track()
            except Exception:
                finished = None
        if finished is None:
            return

        played_seconds = max(0.0, self.player.time / 1000.0)
        nxt = await self.music.wave.continue_after_finish(
            playlist,
            finished,
            played_seconds=played_seconds,
        )
        if nxt is None:
            logger.info("Моя волна: нет следующего трека")
            return

        self._wave_skip_start_feedback = True
        try:
            await self.play_track(nxt)
        finally:
            self._wave_skip_start_feedback = False

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

