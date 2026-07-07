"""Composition root: сборка зависимостей без AppContext."""

from __future__ import annotations

from dataclasses import dataclass

from quantis.controllers.playback_controller import PlaybackController
from quantis.core.async_bridge import AsyncBridge
from quantis.core.plugin_host import PluginHost
from quantis.player import Player, QtMediaEngine
from quantis.plugins.event_bus import EventBus
from quantis.providers import PlaylistManager
from quantis.services import TrackHistoryService
from quantis.services.music_service import MusicService


@dataclass
class ApplicationBundle:
    """Объекты, собранные при старте. Используется только в main и MainWindow."""

    async_bridge: AsyncBridge
    event_bus: EventBus
    player: Player
    music: MusicService
    playlists: PlaylistManager
    playback: PlaybackController
    history: TrackHistoryService
    plugin_host: PluginHost


def build_application(bridge: AsyncBridge) -> ApplicationBundle:
    from quantis.providers import PathProvider

    PathProvider.ensure_storage_dirs()
    event_bus = EventBus()
    engine = QtMediaEngine()
    player = Player(engine=engine)
    music = MusicService()
    playlists = PlaylistManager()
    history = TrackHistoryService()
    playback = PlaybackController(
        player=player,
        playlist_manager=playlists,
        music_service=music,
        event_bus=event_bus,
        history=history,
        async_bridge=bridge,
    )
    plugin_host = PluginHost(
        event_bus=event_bus,
        playback=playback,
        music=music,
    )

    wire_player_events(player, event_bus, playback, bridge)
    wire_event_bus_navigation(event_bus, playback, bridge)

    return ApplicationBundle(
        async_bridge=bridge,
        event_bus=event_bus,
        player=player,
        music=music,
        playlists=playlists,
        playback=playback,
        history=history,
        plugin_host=plugin_host,
    )


def wire_player_events(
    player: Player,
    event_bus: EventBus,
    playback: PlaybackController,
    bridge: AsyncBridge,
) -> None:
    player.on_playback_paused(event_bus.playback_paused.emit)
    player.on_playback_resumed(event_bus.playback_resumed.emit)
    player.on_track_finished(event_bus.track_finished.emit)

    def schedule_auto_next() -> None:
        if playback.playlist_manager.current_playlist is None:
            return
        bridge.schedule(playback.play_next())

    def schedule_next() -> None:
        bridge.schedule(playback.play_next())

    def schedule_previous() -> None:
        bridge.schedule(playback.play_previous())

    player.on_next_requested(schedule_next)
    player.on_previous_requested(schedule_previous)
    player.on_track_finished(schedule_auto_next)


def wire_event_bus_navigation(
    event_bus: EventBus,
    playback: PlaybackController,
    bridge: AsyncBridge,
) -> None:
    event_bus.next_requested.connect(lambda: bridge.schedule(playback.play_next()))
    event_bus.previous_requested.connect(
        lambda: bridge.schedule(playback.play_previous())
    )


def shutdown_application(bundle: ApplicationBundle) -> None:
    bundle.music.shutdown()
