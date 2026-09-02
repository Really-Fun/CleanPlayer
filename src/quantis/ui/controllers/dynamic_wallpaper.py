"""Динамические обои: видео-клип текущего трека на фоне."""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject

from quantis.core.async_bridge import AsyncBridge
from quantis.models import Track
from quantis.plugins.event_bus import EventBus
from quantis.services.music_service import MusicService
from quantis.ui.preferences import UiPreferences
from quantis.ui.views.widgets.wallpaper_backdrop import WallpaperBackdrop

logger = logging.getLogger(__name__)


def _track_key(track: Track) -> str:
    return f"{track.source}:{track.track_id}"


class DynamicWallpaperController(QObject):
    def __init__(
        self,
        backdrop: WallpaperBackdrop,
        music: MusicService,
        bridge: AsyncBridge,
        preferences: UiPreferences,
        event_bus: EventBus,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._backdrop = backdrop
        self._music = music
        self._bridge = bridge
        self._prefs = preferences
        self._pending_track_key: str | None = None
        self._eco = False
        self._paused_for_eco = False

        preferences.changed.connect(self._on_preferences_changed)
        event_bus.track_changed.connect(self._on_track_changed)
        self._apply_enabled()

    def set_eco(self, enabled: bool) -> None:
        """В фоне останавливаем декод видео-обоев (дорого для GPU)."""
        if self._eco == enabled:
            return
        self._eco = enabled
        if enabled:
            if self._backdrop.is_video_playing():
                self._backdrop.pause_video()
                self._paused_for_eco = True
        elif self._paused_for_eco:
            self._paused_for_eco = False
            self._backdrop.resume_video()

    def _on_preferences_changed(self) -> None:
        self._apply_enabled()

    def refresh_for_track(self, track: Track | None) -> None:
        if track is not None and self._prefs.dynamic_wallpaper_enabled and not self._eco:
            self._on_track_changed(track)

    def _apply_enabled(self) -> None:
        enabled = self._prefs.dynamic_wallpaper_enabled
        self._backdrop.set_dynamic_wallpaper_enabled(enabled)
        if not enabled:
            self._pending_track_key = None
            self._paused_for_eco = False

    def _on_track_changed(self, track: Track) -> None:
        if not self._prefs.dynamic_wallpaper_enabled or self._eco:
            return
        self._pending_track_key = _track_key(track)
        self._bridge.schedule(self._load_video(track))

    async def _load_video(self, track: Track) -> None:
        track_key = _track_key(track)
        try:
            local_path = self._local_video_path(track)
            if local_path is not None:
                logger.info("Динамические обои: локальный файл %s", local_path)
                self._bridge.invoke_main(
                    lambda path=local_path: self._backdrop.play_video_url(path)
                )
                return

            url = await self._music.streamer.get_video_url(
                track,
                finder=self._music.finder,
            )
        except Exception:
            logger.exception("Не удалось получить видео для обоев: %s", track)
            return

        if self._pending_track_key != track_key:
            return
        if not url:
            logger.warning("Видео для обоев не найдено: %s", track)
            self._bridge.invoke_main(self._backdrop.stop_video)
            return

        logger.info("Динамические обои: стрим для %s", track)
        stream_url = url

        def _play() -> None:
            self._backdrop.play_video_url(stream_url)

        self._bridge.invoke_main(_play)

    def _local_video_path(self, track: Track) -> str | None:
        from pathlib import Path

        from quantis.providers import PathProvider

        for ext in ("mp4", "webm", "mkv"):
            path = Path(PathProvider().get_video_cache_path(track, extension=ext))
            if path.is_file() and path.stat().st_size > 0:
                return str(path.resolve())
        return None
