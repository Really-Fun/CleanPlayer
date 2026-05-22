"""Контроллер воспроизведения.

Управляет play / pause / volume / track loading.
Чистый Python (Pure Python) — никаких зависимостей от PySide6 или GUI.
"""

from __future__ import annotations

import asyncio
from vlc import EventType

from quantis.models import Track
from quantis.player.engine import VLCEngine

class Player:
    """Плеер. Только воспроизведение. Работает поверх asyncio."""

    def __init__(
        self,
        event_bus,
        path_provider,
        streamer,
        history_service,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self._event_bus = event_bus
        self._path_provider = path_provider
        self._streamer = streamer
        self._history_service = history_service
        self._loop = loop
        
        self._engine = VLCEngine()

        self.current_track: Track | None = None
        self.on_pause: bool = False

        self.events = self._engine.playback_player.event_manager()
        self.events.event_attach(EventType.MediaPlayerEndReached, self._on_end)
        self._persist_task = self._loop.create_task(self._persist_loop())

    async def _persist_loop(self) -> None:
        """Фоновый цикл, который каждые 5 секунд сохраняет прогресс."""
        try:
            while True:
                await asyncio.sleep(5)
                self._persist_current_progress()
        except asyncio.CancelledError:
            pass # Задача корректно отменена при выключении приложения

    async def play_track(self, track: Track) -> None:
        if self.current_track is not None and self.current_track != track:
            self._save_progress_background(self.current_track, force=True)

        self.on_pause = False
        self.current_track = track

        source = await self._resolve_source(track)
        if source is None:
            return

        self._engine.play_both(source)
        self._save_progress_background(track, force=True)
        self._start_resume_restore(track)
        
        self._event_bus.track_changed.emit(track)

    def pause(self) -> None:
        self.on_pause = True
        self._engine.pause_both()
        if self.current_track is not None:
            self._save_progress_background(self.current_track, force=True)
            
        self._event_bus.playback_paused.emit()

    def resume(self) -> None:
        self.on_pause = False
        self._engine.resume_both()
        self._event_bus.playback_resumed.emit()

    def next(self) -> None:
        self._event_bus.next_requested.emit()

    def previous(self) -> None:
        self._event_bus.previous_requested.emit()

    def is_playing(self) -> bool:
        return self._engine.playback_player.is_playing()

    def _on_end(self, _event=None) -> None:
        """VLC вызывает это из отдельного C-потока.
        Qt-сигналы в EventBus потокобезопасны, поэтому emit сработает корректно.
        Но асинхронные задачи нужно кидать в loop безопасно."""
        
        if self.current_track is not None:
            duration = max(0, self.duration)
            
            # Поскольку этот метод вызывается из потока VLC, 
            # мы используем call_soon_threadsafe для работы с asyncio
            self._loop.call_soon_threadsafe(
                self._run_background_sync, 
                self._history_service.mark_track_finished(
                    self.current_track, position_ms=duration, duration_ms=duration
                )
            )
            
        self._event_bus.track_finished.emit()

    def _run_background_sync(self, coro):
        """Вспомогательный метод для запуска корутин из не-asyncio потоков (VLC)"""
        self._loop.create_task(coro)

    @property
    def volume(self) -> int:
        return self._engine.playback_player.audio_get_volume()

    @volume.setter
    def volume(self, value: int) -> None:
        self._engine.playback_player.audio_set_volume(value)

    @property
    def time(self) -> int:
        """Текущая позиция воспроизведения в мс."""
        return self._engine.playback_player.get_time()

    @time.setter
    def time(self, time_in_ms: int) -> None:
        self._engine.playback_player.set_time(time_in_ms)
        self._engine.analysis_player.set_time(time_in_ms)

    @property
    def duration(self) -> int:
        """Длительность текущего трека в мс."""
        return self._engine.playback_player.get_length()

    # --- Internal ---

    async def _resolve_source(self, track: Track) -> str | None:
        """Возвращает путь к файлу или URL стрима."""
        if track.downloaded:
            try:
                if hasattr(track, "extension"):
                    return self._path_provider.get_track_path(track, track.extension)
                return self._path_provider.get_track_path(track)
            except FileNotFoundError:
                return None
        return await self._streamer.get_stream_url(track)

    def _persist_current_progress(self) -> None:
        """Периодически сохраняет прогресс текущего трека."""
        if self.current_track is None:
            return
        if self.is_playing():
            self._save_progress_background(self.current_track, force=False)

    def _save_progress_background(self, track: Track, *, force: bool) -> None:
        """Сохраняет прогресс в фоне без блокировки UI."""
        position = max(0, self.time)
        duration = max(0, self.duration)
        self._run_background(
            self._history_service.save_progress(
                track,
                position_ms=position,
                duration_ms=duration,
                force=force,
            )
        )

    def _start_resume_restore(self, track: Track) -> None:
        """Запускает восстановление позиции воспроизведения в фоне."""
        self._run_background(self._restore_track_position(track))

    async def _restore_track_position(self, track: Track) -> None:
        """Восстанавливает позицию для трека после запуска playback."""
        await asyncio.sleep(0.35)
        if self.current_track != track:
            return
        resume_pos = await self._history_service.get_resume_position(track)
        if resume_pos > 0:
            self.time = resume_pos

    @staticmethod
    def _run_background(coro) -> None:
        """Безопасно создает фоновую asyncio-задачу."""
        try:
            asyncio.get_running_loop().create_task(coro)
        except RuntimeError:
            pass
