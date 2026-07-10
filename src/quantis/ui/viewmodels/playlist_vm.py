from __future__ import annotations

import random

from PySide6.QtCore import QObject, Signal

from quantis.controllers.playback_controller import PlaybackController
from quantis.models import DownloadPlaylist, RecentlyPlayedPlaylist, Track, UserPlaylist
from quantis.models.playlist import Playlist, RecommendationPlaylist
from quantis.ui.models import TrackListModel
from quantis.ui.viewmodels.base_viewmodel import BaseViewModel


class PlaylistViewModel(BaseViewModel):
    """ViewModel страницы плейлиста с ленивой подгрузкой треков."""

    playlist_changed = Signal()
    PLAYLIST_BATCH_SIZE = 5

    def __init__(
        self,
        playback: PlaybackController,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._playback = playback
        self._playlist: Playlist | None = None
        self._model = TrackListModel(batch_size=self.PLAYLIST_BATCH_SIZE)

    @property
    def model(self) -> TrackListModel:
        return self._model

    @property
    def playlist(self) -> Playlist | None:
        return self._playlist

    @property
    def track_count(self) -> int:
        if self._playlist is None:
            return 0
        return len(self._playlist)

    def set_playlist(self, playlist: Playlist) -> None:
        self._playlist = playlist
        self._model.set_tracks(list(playlist.tracks.values))
        self.playlist_changed.emit()

    def set_playing_track(self, track: Track | None) -> None:
        self._model.set_playing_track(track)

    async def play_all(self, start_index: int = 0) -> None:
        playlist = self._playlist
        if playlist is None:
            return
        await self._start_playlist(playlist, start_index=start_index)

    async def play_shuffled(self) -> None:
        playlist = self._playlist
        if playlist is None:
            return
        tracks = list(playlist.tracks.values)
        if not tracks:
            return
        random.shuffle(tracks)
        working = self._clone_playlist(playlist, tracks)
        working.set_current_track(0)
        self._playback.playlist_manager.set_playlist(working)
        await self._playback.play_track(tracks[0])

    async def play_at(self, index: int) -> None:
        playlist = self._playlist
        if playlist is None:
            return
        tracks = list(playlist.tracks.values)
        if not tracks:
            return
        row = max(0, min(index, len(tracks) - 1))
        await self._start_playlist(playlist, start_index=row)

    async def _start_playlist(self, playlist: Playlist, *, start_index: int) -> None:
        tracks = list(playlist.tracks.values)
        if not tracks:
            return
        index = max(0, min(start_index, len(tracks) - 1))
        working = self._clone_playlist(playlist, tracks)
        working.set_current_track(index)
        self._playback.playlist_manager.set_playlist(working)
        await self._playback.play_track(tracks[index])

    @staticmethod
    def _clone_playlist(playlist: Playlist, tracks: list[Track]) -> Playlist:
        if isinstance(playlist, RecentlyPlayedPlaylist):
            return RecentlyPlayedPlaylist(name=playlist.name, tracks=tracks)
        if isinstance(playlist, DownloadPlaylist):
            return DownloadPlaylist(name=playlist.name, tracks=tracks)
        if isinstance(playlist, UserPlaylist):
            return UserPlaylist(playlist.name, tracks, playlist.cover_path)
        if isinstance(playlist, RecommendationPlaylist):
            return RecommendationPlaylist(playlist.name, tracks, playlist.cover_path)
        return RecommendationPlaylist(playlist.name, tracks, playlist.cover_path)
