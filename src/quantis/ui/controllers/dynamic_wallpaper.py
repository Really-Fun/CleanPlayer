"""Динамические обои: видео-клип текущего трека на фоне."""

from __future__ import annotations

import logging
from pathlib import Path

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

        preferences.changed.connect(self._on_preferences_changed)
        event_bus.track_changed.connect(self._on_track_changed)
        self._apply_enabled()

    def _on_preferences_changed(self) -> None:
        self._apply_enabled()

    def refresh_for_track(self, track: Track | None) -> None:
        if track is not None and self._prefs.dynamic_wallpaper_enabled:
            self._on_track_changed(track)

    def _apply_enabled(self) -> None:
        enabled = self._prefs.dynamic_wallpaper_enabled
        self._backdrop.set_dynamic_wallpaper_enabled(enabled)
        if not enabled:
            self._pending_track_key = None

    def _on_track_changed(self, track: Track) -> None:
        if not self._prefs.dynamic_wallpaper_enabled:
            return
        self._pending_track_key = _track_key(track)
        self._bridge.schedule(self._load_video(track))

    async def _load_video(self, track: Track) -> None:
        track_key = _track_key(track)
        try:
            clip_path = await self._music.streamer.get_video_url(
                track,
                finder=self._music.finder,
            )
        except Exception:
            logger.exception("Не удалось получить видео для обоев: %s", track)
            return

        if self._pending_track_key != track_key:
            return
        if not clip_path or not Path(clip_path).is_file():
            logger.warning("Видео-клип для обоев не найден: %s", track)
            self._bridge.invoke_main(self._backdrop.stop_video)
            return

        logger.info("Динамические обои: %s → %s", track, clip_path)
        path = clip_path

        def _play() -> None:
            self._backdrop.play_video_file(path)

        self._bridge.invoke_main(_play)
