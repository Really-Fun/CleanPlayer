from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from quantis.controllers.playback_controller import PlaybackController
from quantis.core.async_bridge import AsyncBridge
from quantis.models import (
    DownloadPlaylist,
    LikedPlaylist,
    RecentlyPlayedPlaylist,
    Track,
    UserPlaylist,
)
from quantis.models.playlist import Playlist, RecommendationPlaylist
from quantis.providers.path_provider import PathProvider
from quantis.services import MusicService, TrackHistoryService
from quantis.services.liked_tracks import LikedTracksService
from quantis.ui.cover_prefetch import schedule_cover_prefetch
from quantis.ui.models import TrackListModel
from quantis.ui.viewmodels.base_viewmodel import BaseViewModel

logger = logging.getLogger(__name__)


class _CountedShell(Playlist):
    """Карточка плейлиста без полного списка треков (треки берутся из модели при открытии)."""

    def __init__(
        self,
        name: str,
        *,
        count: int,
        cover_path: str | None,
        kind: str,
    ) -> None:
        super().__init__(name, (), cover_path)
        self._ui_count = count
        self.kind = kind

    def get_tracks(self) -> tuple[Track, ...]:
        return ()

    def __len__(self) -> int:
        return self._ui_count


@dataclass(frozen=True)
class HomeSnapshot:
    greeting: str
    quick_playlists: tuple[Playlist, ...]
    library_playlists: tuple[Playlist, ...]
    recommendation_tracks: tuple[Track, ...]
    recent_tracks: tuple[Track, ...]


class HomeViewModel(BaseViewModel):
    home_changed = Signal()
    recent_changed = Signal()
    downloaded_changed = Signal()

    def __init__(
        self,
        history: TrackHistoryService,
        playback: PlaybackController,
        music: MusicService | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._history = history
        self._playback = playback
        self._music = music or playback.music
        self._recent_model = TrackListModel()
        self._downloaded_model = TrackListModel()
        self._recommendation_model = TrackListModel()
        self._liked_model = TrackListModel()
        self._liked = LikedTracksService()
        self._snapshot = HomeSnapshot(
            greeting=_greeting_text(),
            quick_playlists=(),
            library_playlists=(),
            recommendation_tracks=(),
            recent_tracks=(),
        )
        self._recommendation_playlist: RecommendationPlaylist | None = None
        self._load_started = False
        self._bridge: AsyncBridge | None = None

    @property
    def recent_model(self) -> TrackListModel:
        return self._recent_model

    @property
    def downloaded_model(self) -> TrackListModel:
        return self._downloaded_model

    @property
    def recommendation_model(self) -> TrackListModel:
        return self._recommendation_model

    @property
    def liked_model(self) -> TrackListModel:
        return self._liked_model

    @property
    def snapshot(self) -> HomeSnapshot:
        return self._snapshot

    def request_load(self, bridge: AsyncBridge) -> None:
        if self._load_started:
            return
        self._load_started = True
        self._bridge = bridge
        from quantis.ui.async_ui import schedule

        schedule(self._load_async(), bridge)

    def refresh(self, bridge: AsyncBridge) -> None:
        self._bridge = bridge
        from quantis.ui.async_ui import schedule

        schedule(self._load_async(), bridge)

    async def _load_async(self) -> None:
        bridge = self._bridge
        if bridge is None:
            return
        bridge.invoke_main(lambda: self.set_loading(True))
        try:
            recent_task = self._history.get_recent_playlist(limit=24)
            liked_task = self._liked.get_playlist()
            downloaded_task = asyncio.to_thread(DownloadPlaylist.get_tracks_from_music_dir)
            playlists_task = asyncio.to_thread(_load_user_playlists)
            recent, liked, downloaded, user_playlists = await asyncio.gather(
                recent_task,
                liked_task,
                downloaded_task,
                playlists_task,
            )

            recent_tracks = list(recent.tracks.values) if recent else []
            liked_tracks = list(liked.tracks.values)
            snapshot = self._build_snapshot(
                recent_tracks=recent_tracks,
                liked_tracks=liked_tracks,
                downloaded=downloaded,
                user_playlists=user_playlists,
                recommendation_tracks=(),
            )

            def apply_fast() -> None:
                self._snapshot = snapshot
                self._recent_model.set_tracks(recent_tracks)
                self._liked_model.set_tracks(liked_tracks)
                self._downloaded_model.set_tracks(list(downloaded))
                self.home_changed.emit()
                self.recent_changed.emit()
                self.downloaded_changed.emit()

            bridge.invoke_main(apply_fast)
            bridge.invoke_main(lambda: self.set_loading(False))
            schedule_cover_prefetch(
                recent_tracks + liked_tracks,
                self._music.downloader,
                bridge,
                on_done=lambda: self.recent_changed.emit(),
                limit=32,
            )

            recommendation_tracks, recommendation_playlist = await self._load_recommendations(
                recent_tracks
            )
            full_snapshot = self._build_snapshot(
                recent_tracks=recent_tracks,
                liked_tracks=liked_tracks,
                downloaded=downloaded,
                user_playlists=user_playlists,
                recommendation_tracks=tuple(recommendation_tracks),
            )

            def apply_recommendations() -> None:
                self._snapshot = full_snapshot
                self._recommendation_playlist = recommendation_playlist
                self._recommendation_model.set_tracks(list(recommendation_tracks))
                self.home_changed.emit()

            bridge.invoke_main(apply_recommendations)
            schedule_cover_prefetch(
                recommendation_tracks,
                self._music.downloader,
                bridge,
                on_done=lambda: self.home_changed.emit(),
                limit=16,
            )
        except Exception as exc:
            logger.exception("Не удалось загрузить главную страницу")
            bridge.invoke_main(lambda: self.emit_error(str(exc)))
        finally:
            bridge.invoke_main(lambda: self.set_loading(False))

    def _build_snapshot(
        self,
        *,
        recent_tracks: list[Track],
        liked_tracks: list[Track],
        downloaded: list[Track] | tuple[Track, ...],
        user_playlists: list[UserPlaylist],
        recommendation_tracks: tuple[Track, ...],
    ) -> HomeSnapshot:
        library_playlists: list[Playlist] = []
        if recent_tracks:
            library_playlists.append(
                _CountedShell(
                    "Недавно прослушанные",
                    count=len(recent_tracks),
                    cover_path=RecentlyPlayedPlaylist().cover_path,
                    kind="recent",
                )
            )
        library_playlists.append(
            _CountedShell(
                "Любимые",
                count=len(liked_tracks),
                cover_path=LikedPlaylist().cover_path,
                kind="liked",
            )
        )
        downloaded_count = len(downloaded)
        if downloaded_count:
            library_playlists.append(
                _CountedShell(
                    "Скачанные",
                    count=downloaded_count,
                    cover_path=DownloadPlaylist().cover_path,
                    kind="downloaded",
                )
            )
        library_playlists.extend(user_playlists)
        quick = list(library_playlists[:6])
        return HomeSnapshot(
            greeting=_greeting_text(),
            quick_playlists=tuple(quick),
            library_playlists=tuple(library_playlists),
            recommendation_tracks=recommendation_tracks,
            recent_tracks=tuple(recent_tracks),
        )

    async def refresh_recent(self, bridge: AsyncBridge) -> None:
        """Быстрое обновление недавних треков из БД (без сетевых запросов)."""
        self._bridge = bridge
        try:
            recent = await self._history.get_recent_playlist(limit=24)
            recent_tracks = list(recent.tracks.values) if recent else []
            snap = self._snapshot
            library_playlists: list[Playlist] = []
            if recent_tracks:
                library_playlists.append(
                    _CountedShell(
                        "Недавно прослушанные",
                        count=len(recent_tracks),
                        cover_path=RecentlyPlayedPlaylist().cover_path,
                        kind="recent",
                    )
                )
            for pl in snap.library_playlists:
                if isinstance(pl, _CountedShell) and pl.kind == "recent":
                    continue
                if isinstance(pl, RecentlyPlayedPlaylist):
                    continue
                library_playlists.append(pl)
            # Гарантируем shell «Любимые», если его ещё нет в снимке.
            if not any(
                isinstance(pl, _CountedShell) and pl.kind == "liked"
                for pl in library_playlists
            ):
                library_playlists.insert(
                    1 if recent_tracks else 0,
                    _CountedShell(
                        "Любимые",
                        count=len(self._liked_model.all_tracks()),
                        cover_path=LikedPlaylist().cover_path,
                        kind="liked",
                    ),
                )
            quick = list(library_playlists[:6])
            new_snap = HomeSnapshot(
                greeting=_greeting_text(),
                quick_playlists=tuple(quick),
                library_playlists=tuple(library_playlists),
                recommendation_tracks=snap.recommendation_tracks,
                recent_tracks=tuple(recent_tracks),
            )

            def apply() -> None:
                self._snapshot = new_snap
                self._recent_model.set_tracks(recent_tracks)
                # Только recent_changed — без полной пересборки карточек главной.
                self.recent_changed.emit()

            bridge.invoke_main(apply)
        except Exception:
            logger.exception("Не удалось обновить недавние треки")

    async def _load_recommendations(
        self, recent_tracks: list[Track]
    ) -> tuple[list[Track], RecommendationPlaylist | None]:
        if not recent_tracks:
            try:
                fallback = await self._music.finder.get_tracks("chill mix", value=10)
            except Exception:
                logger.exception("Не удалось загрузить рекомендации")
                return [], None
            if not fallback:
                return [], None
            playlist = RecommendationPlaylist(name="Для вас", tracks=fallback)
            return fallback, playlist

        seed = recent_tracks[0]
        try:
            playlist = await self._music.recommendation.generate_radio_from_track(seed)
        except Exception:
            logger.exception("Не удалось сгенерировать радио для главной")
            return recent_tracks[1:9], None
        tracks = list(playlist.tracks.values)
        return tracks[:12], playlist

    async def play_track(self, track: Track) -> None:
        await self._playback.play_track(track)

    async def play_recent_at(self, index: int) -> None:
        await self._play_from_model(self._recent_model, index)

    async def play_recommendation_at(self, index: int) -> None:
        await self._play_from_model(self._recommendation_model, index)

    async def play_playlist(self, playlist: Playlist, start_index: int = 0) -> None:
        playlist = self.resolve_playlist(playlist)
        tracks = list(playlist.tracks.values)
        if not tracks:
            return
        index = max(0, min(start_index, len(tracks) - 1))
        if isinstance(playlist, RecentlyPlayedPlaylist):
            working = RecentlyPlayedPlaylist(name=playlist.name, tracks=tracks)
        elif isinstance(playlist, LikedPlaylist):
            working = LikedPlaylist(name=playlist.name, tracks=tracks)
        elif isinstance(playlist, DownloadPlaylist):
            working = DownloadPlaylist(name=playlist.name, tracks=tracks)
        elif isinstance(playlist, UserPlaylist):
            working = UserPlaylist(playlist.name, tracks, playlist.cover_path)
        elif isinstance(playlist, RecommendationPlaylist):
            working = RecommendationPlaylist(playlist.name, tracks, playlist.cover_path)
        else:
            working = RecommendationPlaylist(playlist.name, tracks, playlist.cover_path)
        working.set_current_track(index)
        self._playback.playlist_manager.set_playlist(working)
        await self._playback.play_track(tracks[index])

    def resolve_playlist(self, playlist: Playlist) -> Playlist:
        """Подставляет треки из моделей для shell-карточек главной."""
        if isinstance(playlist, _CountedShell):
            if playlist.kind == "recent":
                return RecentlyPlayedPlaylist(tracks=self._recent_model.all_tracks())
            if playlist.kind == "liked":
                return LikedPlaylist(tracks=self._liked_model.all_tracks())
            if playlist.kind == "downloaded":
                return DownloadPlaylist(tracks=self._downloaded_model.all_tracks())
        return playlist

    async def refresh_liked(self, bridge: AsyncBridge | None = None) -> None:
        bridge = bridge or self._bridge
        if bridge is None:
            return
        liked = await self._liked.get_playlist()
        liked_tracks = list(liked.tracks.values)

        def apply() -> None:
            self._liked_model.set_tracks(liked_tracks)
            snap = self._snapshot
            library: list[Playlist] = []
            for pl in snap.library_playlists:
                if isinstance(pl, _CountedShell) and pl.kind == "liked":
                    library.append(
                        _CountedShell(
                            "Любимые",
                            count=len(liked_tracks),
                            cover_path=LikedPlaylist().cover_path,
                            kind="liked",
                        )
                    )
                else:
                    library.append(pl)
            if not any(
                isinstance(pl, _CountedShell) and pl.kind == "liked" for pl in library
            ):
                library.insert(
                    1,
                    _CountedShell(
                        "Любимые",
                        count=len(liked_tracks),
                        cover_path=LikedPlaylist().cover_path,
                        kind="liked",
                    ),
                )
            self._snapshot = HomeSnapshot(
                greeting=snap.greeting,
                quick_playlists=tuple(library[:6]),
                library_playlists=tuple(library),
                recommendation_tracks=snap.recommendation_tracks,
                recent_tracks=snap.recent_tracks,
            )
            self.home_changed.emit()

        bridge.invoke_main(apply)

    async def _play_from_model(self, model: TrackListModel, index: int) -> None:
        track = model.get_track(index)
        if track is None:
            return
        tracks = model.all_tracks()
        playlist = RecommendationPlaylist(name="Главная", tracks=tracks)
        playlist.set_current_track(index)
        self._playback.playlist_manager.set_playlist(playlist)
        await self._playback.play_track(track)

    def refresh_downloaded(self, bridge: AsyncBridge) -> None:
        self._bridge = bridge
        from quantis.ui.async_ui import schedule

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
        self.refresh(bridge)

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


def _greeting_text() -> str:
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Доброе утро"
    if 12 <= hour < 18:
        return "Добрый день"
    if 18 <= hour < 23:
        return "Добрый вечер"
    return "Доброй ночи"


def _load_user_playlists() -> list[UserPlaylist]:
    playlists_dir = Path("playlists")
    if not playlists_dir.is_dir():
        playlists_dir.mkdir(parents=True, exist_ok=True)
        return []

    result: list[UserPlaylist] = []
    json_files = sorted(
        playlists_dir.glob("*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for path in json_files:
        try:
            playlist = UserPlaylist.get_playlist_from_path(str(path))
        except Exception:
            logger.exception("Не удалось загрузить плейлист %s", path)
            continue
        if playlist is not None and playlist.tracks.values:
            if not playlist.cover_path:
                first = playlist.tracks.values[0]
                playlist.cover_path = PathProvider().get_cover_path(first)
            result.append(playlist)
    return result
