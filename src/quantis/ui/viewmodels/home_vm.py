from __future__ import annotations

import asyncio
import logging

from PySide6.QtCore import QObject, Signal

from quantis.controllers.playback_controller import PlaybackController
from quantis.core.async_bridge import AsyncBridge
from quantis.models import DownloadPlaylist, Track
from quantis.services import TrackHistoryService
from quantis.ui.models import TrackListModel
from quantis.ui.viewmodels.base_viewmodel import BaseViewModel

logger = logging.getLogger(__name__)


class HomeViewModel(BaseViewModel):
    recent_changed = Signal()
    downloaded_changed = Signal()

    def __init__(
        self,
        history: TrackHistoryService,
        playback: PlaybackController,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._history = history
        self._playback = playback
        self._recent_model = TrackListModel()
        self._downloaded_model = TrackListModel()
        self._load_started = False
        self._bridge: AsyncBridge | None = None

    @property
    def recent_model(self) -> TrackListModel:
        return self._recent_model

    @property
    def downloaded_model(self) -> TrackListModel:
        return self._downloaded_model

    def request_load(self, bridge: AsyncBridge) -> None:
        if self._load_started:
            return
        self._load_started = True
        self._bridge = bridge
        from quantis.ui.async_ui import schedule

        schedule(self._load_async(), bridge)

    async def _load_async(self) -> None:
        bridge = self._bridge
        if bridge is None:
            return
        bridge.invoke_main(lambda: self.set_loading(True))
        try:
            recent = await self._history.get_recent_playlist(limit=24)
            recent_tracks = list(recent.tracks.values) if recent else []
            downloaded = await asyncio.to_thread(DownloadPlaylist.get_tracks_from_music_dir)

            def apply() -> None:
                self._recent_model.set_tracks(recent_tracks)
                self.recent_changed.emit()
                self._downloaded_model.set_tracks(list(downloaded))
                self.downloaded_changed.emit()

            bridge.invoke_main(apply)
        except Exception as exc:
            logger.exception("Не удалось загрузить главную страницу")
            bridge.invoke_main(lambda: self.emit_error(str(exc)))
        finally:
            bridge.invoke_main(lambda: self.set_loading(False))

    async def play_track(self, track: Track) -> None:
        await self._playback.play_track(track)

    async def play_recent_at(self, index: int) -> None:
        track = self._recent_model.get_track(index)
        if track is not None:
            await self.play_track(track)

    async def play_downloaded_at(self, index: int) -> None:
        track = self._downloaded_model.get_track(index)
        if track is not None:
            await self.play_track(track)

    def refresh_downloaded(self, bridge: AsyncBridge) -> None:
        from quantis.ui.async_ui import schedule

        self._bridge = bridge
        schedule(self._refresh_downloaded_async(), bridge)

    async def _refresh_downloaded_async(self) -> None:
        bridge = self._bridge
        if bridge is None:
            return
        downloaded = await asyncio.to_thread(DownloadPlaylist.get_tracks_from_music_dir)

        def apply() -> None:
            self._downloaded_model.set_tracks(list(downloaded))
            self.downloaded_changed.emit()

        bridge.invoke_main(apply)

    async def download_recent_at(self, index: int) -> None:
        track = self._recent_model.get_track(index)
        if track is None or track.downloaded:
            return
        bridge = self._bridge
        if bridge is None:
            return
        downloader = self._playback.music.downloader
        bridge.invoke_main(lambda: self.set_loading(True))
        try:
            await downloader.download_track(track)
            await downloader.download_cover(track)
            track.downloaded = True

            def refresh() -> None:
                model_index = self._recent_model.index(index)
                self._recent_model.dataChanged.emit(model_index, model_index, [])
                self.downloaded_changed.emit()

            bridge.invoke_main(refresh)
            self.refresh_downloaded(bridge)
        except Exception as exc:
            logger.exception("Ошибка скачивания")
            bridge.invoke_main(lambda: self.emit_error(str(exc)))
        finally:
            bridge.invoke_main(lambda: self.set_loading(False))
